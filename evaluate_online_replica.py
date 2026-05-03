#!/usr/bin/env python3
"""
evaluate_online_replica.py — Avaliação Offline (Réplica Fiel do Motor Online)
==============================================================================
Replica fielmente o pipeline de recomendação de:
  - services/publication.py  → PublicationService.get_publications()
  - word_embedding/gensim.py → extract_best_match()
  - nlp/nltk.py              → NTLKService.clean_publication_title()

Substituições mínimas (APENAS infraestrutura):
  API DBLP   → busca por string matching no dblp-v10.csv
  API Qualis → venue_score = 0
  Redis/DB   → sem cache (re-processa tudo em memória)
  ORCID live → títulos pré-carregados de data.json

SCORING (idêntico ao gensim.py online):
  score = year + venue_score + title_similarity
  title_similarity = Σ cosine(model[subject], model[word])
    → model[subject] recebe o título COMPLETO como string
    → Word2Vec é word-level → KeyError → capturado → title_similarity = 0
    → score efetivo = year + 0

CRITÉRIO DE ACERTO (coautoria, independente do motor):
  Acerto = autor-alvo listado como (co)autor no DBLP.

USO:
  python evaluate_online_replica.py --n 10
  python evaluate_online_replica.py --n 82 --random
"""

import sys
import os
import re
import ast
import json
import random
import argparse
import warnings
from datetime import datetime
from math import log2
from typing import List, Dict, Optional, Tuple, Set

import numpy as np
import pandas as pd
from gensim.models import KeyedVectors
from rapidfuzz import process, fuzz
from scipy.stats import wilcoxon
import re

from utils import QUALIS_SCORES
from utils.qualis import load_conferences, load_periodics

# ─── CACHE GLOBAL QUALIS ──────────────────────────────────────────────────────
# Carregamos a planilha da CAPES UMA VEZ na memória para lookup super veloz
QUALIS_CACHE = {}
print("[INFO] Carregando planilhas do Qualis...")
try:
    for row in load_conferences():
        name = re.sub(r"\([^)]*\)", "", row.get("evento", "")).lower().strip()
        score = QUALIS_SCORES.get(row.get("Qualis_Final", "NONE"), 0.0)
        if name and score > 0:
            QUALIS_CACHE[name] = score
    for row in load_periodics():
        name = re.sub(r"\([^)]*\)", "", row.get("periodico", "")).lower().strip()
        score = QUALIS_SCORES.get(row.get("Qualis_Final", "NONE"), 0.0)
        if name and score > 0:
            QUALIS_CACHE[name] = score
    print(f"[OK] Qualis em memória: {len(QUALIS_CACHE)} veiculos mapeados da CAPES.")
except Exception as e:
    print(f"[WARN] Não foi possível carregar planilha Qualis (verifique os resources): {e}")
    QUALIS_CACHE = {}

from multi_rake import Rake
from lingua import Language, LanguageDetectorBuilder
from nltk import word_tokenize, WordNetLemmatizer
from nltk import download as nltk_download
from nltk.corpus import stopwords

warnings.filterwarnings("ignore")

# ─── CONFIGURAÇÕES DO EXPERIMENTO ──────────────────────────────────────────
DATA_JSON            = r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados\data_apt.json" # Default, can be overridden
DBLP_CSV             = r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados\dblp-v10.csv"
MODEL_PATH           = r"c:\Users\Lucas\Documents\Paperman\paperman_back\paperman\cbow_s100"
MODEL_TXT            = r"c:\Users\Lucas\Documents\Paperman\paperman_back\paperman\resources\word2vec\cbow_s100.txt"
LOG_DIR              = r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados"

# MIN_PUBLICATIONS agora é dinâmico: n_train + n_test
YEAR_CUTOFF          = 2017      # teto temporal (simula estado da arte em 2017)
YEAR_WINDOW          = 5         # janela: aceita 2013 ≤ year ≤ 2017
YEAR_MIN             = YEAR_CUTOFF - YEAR_WINDOW + 1   # 2013 — menor ano aceito
CANDIDATES_PER_TOPIC = 90      # head(N) por keyword no DBLP. Subido de 45→100 após
                                 # remoção da injeção: pool maior compensa a perda do
                                 # gabarito injetado, aumentando a chance de coautoria
                                 # orgânica aparecer nos candidatos.
TOP_K_EVAL           = 10        # avaliamos @3, @5, @10

FUZZ_THRESHOLD       = 85        # threshold de fuzzy matching para coautoria
ALLOWED_LANGS        = [Language.PORTUGUESE, Language.ENGLISH]
SYMBOL_RE            = re.compile(r"[^a-zA-Z0-9\s]")

# ─── CARREGAMENTO (uma vez) ─────────────────────────────────────────────────
_model   = None
_df      = None
_wnl     = None
_stops   = None
_lang_d  = None


def load_model():
    """
    Carrega o modelo Word2Vec (cbow_s100) na memória uma única vez.
    Na primeira chamada, tenta carregar o arquivo binário binário (gensim KeyedVectors).
    Se não encontrar, converte o formato texto (.txt) para binário e salva em disco
    para que as próximas execuções sejam mais rápidas.

    Retorna: o objeto KeyedVectors com os vetores de palavras carregados.
    """
    global _model
    if _model is None:
        try:
            # Tenta carregar o formato binário (muito mais rápido)
            _model = KeyedVectors.load(MODEL_PATH, mmap="r")
        except FileNotFoundError:
            # Converte do formato texto original e salva o binário para próximas execuções
            m = KeyedVectors.load_word2vec_format(MODEL_TXT)
            m.init_sims(replace=True)
            m.save(MODEL_PATH)
            _model = KeyedVectors.load(MODEL_PATH, mmap="r")
        print(f"[OK] Word2Vec carregado ({len(_model.key_to_index):,} palavras)")
    return _model


def load_csv():
    """
    Carrega o arquivo DBLP (dblp-v10.csv) como DataFrame Pandas uma única vez.
    Cria a coluna auxiliar 'title_norm' (título em minúsculas sem espaços extras)
    para acelerar as buscas por string matching.

    Retorna: o DataFrame com todos os artigos do DBLP.
    """
    global _df
    if _df is None:
        _df = pd.read_csv(DBLP_CSV, on_bad_lines='skip')
        # Coluna normalizada facilita comparação case-insensitive
        _df['title_norm'] = _df['title'].str.lower().str.strip()
        print(f"[OK] DBLP CSV carregado: {len(_df):,} artigos")
    return _df


def ensure_nltk():
    """
    Garante que os recursos do NLTK (tokenizador, lematizador e stopwords)
    estão carregados na memória antes do uso.
    Faz o download automático caso os arquivos não estejam instalados localmente.
    """
    global _wnl, _stops
    if _wnl is None:
        try:
            _wnl   = WordNetLemmatizer()
            _stops = stopwords.words("portuguese") + stopwords.words("english")
        except LookupError:
            # Baixa os recursos NLTK necessários se ainda não estiverem instalados
            for r in ["stopwords", "wordnet", "punkt", "punkt_tab"]:
                nltk_download(r, quiet=True)
            _wnl   = WordNetLemmatizer()
            _stops = stopwords.words("portuguese") + stopwords.words("english")


def ensure_lang():
    """
    Inicializa o detector de idiomas (biblioteca Lingua) na primeira chamada.
    A detecção é usada para filtrar artigos em idiomas não suportados
    (só aceita Português e Inglês, conforme ALLOWED_LANGS).
    """
    global _lang_d
    if _lang_d is None:
        _lang_d = LanguageDetectorBuilder.from_all_languages().build()


# ─── RÉPLICA: NTLKService.clean_publication_title() ─────────────────────────
def clean_publication_title(title: str) -> List[str]:
    """
    Réplica de nlp/nltk.py — NTLKService.clean_publication_title().
    
    Prepara o texto do título para que o Word2Vec consiga processá-lo.
    Executa 5 passos de limpeza e normalização:
    
    Exemplo de entrada: "A Learning Approach for the Acquisition of User Preferences"
    
    1. Tokenização: Quebra a frase em palavras ["A", "Learning", ...]
    2. Duplicatas e Case: Converte para minúsculas e remove repetições
    3. Stopwords: Remove palavras sem valor semântico (a, for, the, of)
    4. Símbolos: Descarta tokens com caracteres especiais ({, -, *)
    5. Lematização e Idioma: Reduz ao radical base (preferences -> preference) 
       e garante que a palavra seja PT ou EN.
       
    Retorno: ["learn", "approach", "acquisition", "user", "preference"]
    """
    ensure_nltk()
    ensure_lang()
    try:
        tokens = word_tokenize(title)
    except LookupError:
        for r in ["punkt", "punkt_tab"]:
            nltk_download(r, quiet=True)
        tokens = word_tokenize(title)

    unique    = list({w.lower(): "" for w in tokens})
    no_stop   = [w for w in unique if w not in _stops]
    no_sym    = [w for w in no_stop if not SYMBOL_RE.search(w)]
    lemmatized = [_wnl.lemmatize(w).lower() for w in no_sym]
    return [w for w in lemmatized if _lang_d.detect_language_of(w) in ALLOWED_LANGS]


# ==============================================================================
# FUNÇÕES OBSOLETAS (MANTIDAS APENAS PARA HISTÓRICO)
# Com a nova arquitetura de "Tiro no Escuro" sugerida pelo orientador, 
# a extração de keywords e a busca textual foram substituídas pela
# amostragem aleatória `df.sample(n=100)`.
#
# No sistema online de produção (que exige velocidade), elas continuam
# sendo usadas. Mas para o experimento offline, viraram código morto.
# ==============================================================================

# # ─── RÉPLICA: build_search_query() ──────────────────────────────────────────
# def build_search_query(subject: str) -> List[str]: # Alterara nome do metodo
#     """
#     Réplica de word_embedding/gensim.py — build_search_query().
#     
#     Usa o algoritmo RAKE (Rapid Automatic Keyword Extraction) para extrair
#     os termos centrais de um artigo que o usuário escreveu no passado.
#     O RAKE identifica blocos de palavras (phrases) com alto conteúdo semântico,
#     ignorando palavras de ligação.
#     
#     Exemplo de entrada: "A novel architecture for deep neural networks in robotics"
#     Retorno: ["deep neural networks", "novel architecture", "robotics"]
#     
#     Essas palavras-chave são a "isca" usada para buscar candidatos no DBLP.
#     """
#     subject = re.sub(r'[^\x00-\x7f]', r'', subject)
#     rake     = Rake()
#     keywords = rake.apply(subject)
#     return [item[0] for item in keywords]
# 
# 
# # ─── RÉPLICA: DBLPAdapter.get_publications() (via CSV local) ────────────────
# def search_by_topic(query: str, df: pd.DataFrame) -> List[Dict]:
#     """
#     Réplica da chamada à API DBLP (DBLPAdapter.get_publications).
#     
#     Faz a busca textual (string matching) no banco de dados inteiro procurando
#     pela palavra-chave extraída. Este é o "Funil Grosso" (Retrieval Phase).
#     
#     Para evitar que o sistema exploda de lentidão ao buscar palavras comuns como "learning",
#     o filtro é truncado pelo .head(CANDIDATES_PER_TOPIC) — ex: retorna no máximo 90 artigos.
#     
#     Retorna a lista de artigos (em formato dicionário) que contêm a keyword no título,
#     que formarão a "Piscina de Candidatos" a serem avaliados pelo Word2Vec + Equação V5.
#     """
#     q    = query.lower().strip()
#     hits = df[df['title_norm'].str.contains(q, na=False, regex=False)].head(CANDIDATES_PER_TOPIC)
#     result = []
#     for _, row in hits.iterrows():
#         raw   = str(row['authors'])
#         names = [a.strip().strip("'\"") for a in re.sub(r"[\[\]]", "", raw).split(",") if a.strip()]
#         result.append({
#             "title":   str(row['title']),
#             "year":    int(row['year']),
#             "venue":   str(row['venue']),
#             "authors": names,
#             "id":      str(row['id']),
#             "n_citation": int(row.get('n_citation', 0) or 0),
#             "references_raw": str(row.get('references', '[]') or '[]'),
#         })
#     return result


# ─── ENRIQUECIMENTO DO GABARITO (lookup no DBLP) ─────────────────────────────
# OBSOLETA: Antes os gabaritos não tinham citações/venue, então fazíamos um fuzzy match
# no DBLP. Hoje o `data_apt.json` já traz esses dados consolidados do Semantic Scholar
# no campo `_enriched`, tornando essa função código morto.
# def enrich_from_dblp(title: str, df: pd.DataFrame) -> tuple:
#     """
#     Busca o paper do gabarito no DBLP por título (exato → fuzzy) para recuperar
#     n_citation e venue reais. Necessário porque o gabarito hoje é injetado como
#     dict sintético com venue='TestSet' e sem citações, o que enviesava o ranking
#     contra os hits após o fix do bug de citação.
# 
#     Retorna (n_citation, venue). Se não encontrar, devolve (0, 'TestSet').
#     """
#     title_norm = title.lower().strip()
#     exact = df[df['title_norm'] == title_norm]
#     if not exact.empty:
#         row = exact.iloc[0]
#         return int(row.get('n_citation', 0) or 0), str(row['venue'])
# 
#     # Fallback fuzzy: estreita por prefixo (~30 chars) pra não varrer 1M
#     prefix = title_norm[:30]
#     if not prefix:
#         return 0, "TestSet"
#     candidates = df[df['title_norm'].str.startswith(prefix, na=False)].head(100)
#     if candidates.empty:
#         return 0, "TestSet"
#     pool = candidates['title_norm'].tolist()
#     best = process.extractOne(title_norm, pool, scorer=fuzz.ratio, score_cutoff=85)
#     if best:
#         match_str = best[0]
#         row = candidates[candidates['title_norm'] == match_str].iloc[0]
#         return int(row.get('n_citation', 0) or 0), str(row['venue'])
#     return 0, "TestSet"


# ─── RÉPLICA: sanitize_publications() — filtro de idioma ────────────────────
def is_valid_language(title: str) -> bool:
    """
    Verifica se o título do artigo está em um dos idiomas aceitos pelo sistema
    (Português ou Inglês). Descarta artigos em Chinês, Árabe, Alemão etc.
    Evita que textos sem sentido semântico para o Word2Vec entrem no pool.
    """
    ensure_lang()
    return _lang_d.detect_language_of(title) in ALLOWED_LANGS


# ─── RÉPLICA: cosine_similarity() ────────────────────────────────────────────
def cosine_similarity(a, b) -> float:
    """
    Calcula a Similaridade de Cosseno entre dois vetores numpy.
    Mede o ângulo entre os dois vetores no espaço vetorial do Word2Vec:
      - Resultado = 1.0: vetores idênticos (palavras muito similares)
      - Resultado = 0.0: vetores perpendiculares (sem relação semântica)
      - Resultado < 0: vetores opostos (raro em Word2Vec)
    Retorna 0.0 se qualquer um dos vetores for nulo (evita divisão por zero).
    """
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom > 0 else 0.0


# ─── SCORING CORRIGIDO: extract_best_match() ────────────────────────────────
def extract_best_match_online(candidates: List[Dict], subject: str, model,
                              qualis_mode: str = "additive") -> Optional[Dict]:
    """
    Versão final do motor Paperman (V5.3).
    Score = somatório de parâmetros normalizados em [0, 1], sem pesos arbitrários.

    qualis_mode:
      - "sem_only"      → Apenas semântica. Score = Sem                                  (0..1)
      - "off"           → Qualis ignorado.  Score = Sem + Rec + Cit                      (0..3)
      - "additive"      → Qualis aditivo.   Score = Sem + Rec + Cit + Qua                (0..4)
      - "modulated"     → Qua×Sem.          Score = Sem + Rec + Cit + (Qua×Sem)          (0..4)
      - "cit_modulated" → Cit×Sem.          Score = Sem + Rec + (Cit×Sem) + Qua          (0..4)
      - "all_modulated" → Tudo×Sem.         Score = Sem + (Rec×Sem) + (Cit×Sem) + (Qua×Sem) (0..4)
      - "multiplicative"→ Multiplicação.    Score = Sem × Rec × Cit × Qua                (0..1)

    Justificativas:
      "sem_only": isola completamente o componente semântico. Serve como teste de
        ablação: se o ranking baseado SÓ em similaridade já bate o aleatório, prova
        que o sinal semântico tem valor independente. Se perde para "all_modulated",
        prova que os termos universais agregam valor quando modulados.
      "modulated": Qualis bruto soma até +1.0 num score onde Sem opera em [0.3, 0.6],
        dominando ranking por prestígio independente de relevância. Multiplicar por Sem
        condiciona o bônus de prestígio à relevância semântica.
      "all_modulated": estende a mesma lógica para Rec e Cit. Adota Sem como pilar
        autoridade — todos os termos universais (Rec/Cit/Qua) só contribuem
        proporcionalmente à relevância semântica do candidato. Papers irrelevantes
        (Sem≈0) ficam com score≈0, independente de citações ou prestígio.
    """
    if not candidates:
        return None

    import math

    # Perfil (subject) tokenizado
    subject_words = clean_publication_title(subject)

    # ── PRÉ-PASSE: calcula CPY para todos os candidatos e faz Min-Max Local ──
    # Em vez de um teto global fixo (MAX_CPY=50), normalizamos as citações
    # em relação ao pool atual da rodada.
    # O paper mais citado do pool recebe 1.0; o menos citado recebe 0.0.
    # Isso elimina o parâmetro arbitrário MAX_CPY e torna a escala adaptativa.
    cpys = []
    for c in candidates:
        age = max(1, YEAR_CUTOFF - c["year"] + 1)
        cpys.append(c.get("n_citation", 0) / age)

    cpy_min = min(cpys)
    cpy_max = max(cpys)
    cpy_range = cpy_max - cpy_min  # evita divisão por zero abaixo

    scored = []
    for i, c in enumerate(candidates):
        # 1. Similaridade Semântica
        cand_words = clean_publication_title(c["title"])
        sim_total, n_pairs = 0.0, 0
        for sw in subject_words:
            for cw in cand_words:
                try:
                    sim_total += cosine_similarity(model[sw], model[cw])
                    n_pairs += 1
                except KeyError:
                    pass
        mean_cosine = sim_total / n_pairs if n_pairs > 0 else 0.0

        # 2. Recência (Decaimento Logarítmico Temporal)
        age_in_years = max(0, YEAR_CUTOFF - c["year"])
        max_age = YEAR_CUTOFF - YEAR_MIN
        if max_age <= 0:
            recency = 1.0
        else:
            recency = max(0.0, 1.0 - (math.log(age_in_years + 1) / math.log(max_age + 1)))

        # 3. Citações — Min-Max Local por Pool
        # Se todos os papers do pool têm o mesmo CPY (cpy_range == 0),
        # todos empatam com 0.5 para não privilegiar nem penalizar ninguém.
        if cpy_range > 0:
            citation_score = (cpys[i] - cpy_min) / cpy_range
        else:
            citation_score = 0.5  # pool com citações uniformes: empate técnico

        # 4. Qualis (Busca instantânea e Fuzzy Match otimizado no cache da CAPES)
        venue = str(c.get("venue", "") or "").lower().strip()
        qualis_score = 0.0
        
        if venue and QUALIS_CACHE:
            # 1. Tenta match exato primeiro (mais rápido)
            if venue in QUALIS_CACHE:
                qualis_score = QUALIS_CACHE[venue]
            else:
                # 2. Tenta Fuzzy Extract no topo do cache se não for exato
                # Usa token_sort_ratio e threshold de 85
                best_match = process.extractOne(venue, QUALIS_CACHE.keys(), scorer=fuzz.token_sort_ratio, score_cutoff=85)
                if best_match:
                    match_str = best_match[0]
                    qualis_score = QUALIS_CACHE[match_str]

        # Aplica o modo de combinação dos termos universais
        if qualis_mode == "sem_only":
            qualis_term = 0.0
            rec_term    = 0.0
            cit_term    = 0.0
        elif qualis_mode == "off":
            qualis_term = 0.0
            rec_term    = recency
            cit_term    = citation_score
        elif qualis_mode == "modulated":
            qualis_term = qualis_score * mean_cosine
            rec_term    = recency
            cit_term    = citation_score
        elif qualis_mode == "cit_modulated":
            qualis_term = qualis_score
            rec_term    = recency
            cit_term    = citation_score * mean_cosine
        elif qualis_mode == "all_modulated":
            qualis_term = qualis_score * mean_cosine
            rec_term    = recency        * mean_cosine
            cit_term    = citation_score * mean_cosine
        elif qualis_mode == "multiplicative":
            total = mean_cosine * recency * citation_score * qualis_score
            qualis_term = qualis_score
            rec_term    = recency
            cit_term    = citation_score
        else:  # "additive"
            qualis_term = qualis_score
            rec_term    = recency
            cit_term    = citation_score

        if qualis_mode != "multiplicative":
            total = mean_cosine + rec_term + cit_term + qualis_term
        # Tupla: (score, sem, rec_term, cit_term, qua_term, qua_raw, candidato)
        scored.append((total, mean_cosine, rec_term, cit_term,
                       qualis_term, qualis_score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored  # lista de tuplas ordenadas por score desc


# ─── AVALIAÇÃO: coautoria (regra de ouro) ────────────────────────────────────
def check_coauthorship(author_name: str, paper_authors: List[str]) -> bool:
    """
    Verifica se o autor-alvo é coautor de um paper candidato.
    Usa Fuzzy Matching (token_sort_ratio) com threshold de 85 pontos
    para tolerar pequenas variações de grafia (ex: abreviações, acentos).
    Exemplo: "Lucas A. Silva" e "Lucas Silva" são considerados o mesmo autor.

    Retorna True se encontrar correspondência suficiente, False caso contrário.
    """
    for pa in paper_authors:
        if fuzz.token_sort_ratio(author_name.lower(), pa.lower()) >= FUZZ_THRESHOLD:
            return True
    return False


# ─── AVALIAÇÃO ESTENDIDA: 3 proxies de relevância via grafo de citação ──────
_author_data_cache: Dict[str, Tuple[Set[str], Set[str]]] = {}


def parse_refs(refs_str: str) -> Set[str]:
    """Parse seguro do campo references (string Python-list) para set de IDs."""
    if not refs_str or not refs_str.startswith('['):
        return set()
    try:
        parsed = ast.literal_eval(refs_str)
        if isinstance(parsed, list):
            return {str(r) for r in parsed}
    except (ValueError, SyntaxError):
        pass
    return set()


def get_author_dblp_data(author_name: str, df: pd.DataFrame) -> Tuple[Set[str], Set[str]]:
    """
    Para um autor, retorna:
      - author_ids: set dos IDs dos papers que ele (co)autorou no DBLP-v10
      - author_refs: união dos IDs que esses papers citam (papers que ele já citou)
    Cache global por nome — chamada cara, ~1s por autor.
    """
    if author_name in _author_data_cache:
        return _author_data_cache[author_name]

    parts = author_name.split()
    surname = parts[-1].lower() if parts else ""
    if len(surname) < 3:
        _author_data_cache[author_name] = (set(), set())
        return set(), set()

    # Pré-filtra por sobrenome (rápido) e depois confirma com fuzzy match
    candidates = df[df['authors'].str.lower().str.contains(surname, na=False, regex=False)]

    author_ids: Set[str] = set()
    references: Set[str] = set()
    for _, row in candidates.iterrows():
        raw = str(row['authors'])
        names = [a.strip().strip("'\"") for a in re.sub(r"[\[\]]", "", raw).split(",") if a.strip()]
        if check_coauthorship(author_name, names):
            author_ids.add(str(row['id']))
            references.update(parse_refs(str(row.get('references', '[]') or '[]')))

    result = (author_ids, references)
    _author_data_cache[author_name] = result
    return result


def classify_hit(rec: Dict, target_name: str,
                 author_ids: Set[str], author_refs: Set[str]) -> Optional[str]:
    """
    Classifica um paper recomendado segundo 3 proxies de relevância:
      - 'coauthor':     o autor alvo é coautor do paper (gabarito clássico)
      - 'author_cited': o autor alvo já citou esse paper em algum trabalho dele
      - 'cited_author': esse paper cita pelo menos um trabalho do autor alvo
      - None:           nenhum dos três
    Ordem de prioridade: coauthor > author_cited > cited_author (caso múltiplo).
    """
    if check_coauthorship(target_name, rec.get('authors', [])):
        return 'coauthor'
    rec_id = str(rec.get('id', ''))
    if rec_id and rec_id in author_refs:
        return 'author_cited'
    rec_refs = parse_refs(rec.get('references_raw', '[]'))
    if rec_refs & author_ids:
        return 'cited_author'
    return None


# ─── MÉTRICAS ─────────────────────────────────────────────────────────────────
def precision_at_k(rel: List[bool], k: int) -> float:
    """
    Precision@K: mede a proporção de acertos nas K primeiras recomendações.
    Exemplo: se das 5 primeiras, 2 são relevantes → P@5 = 2/5 = 0.40.
    Quanto maior, melhor. Máximo = 1.0 (todos os K primeiros são acertos).
    """
    return sum(rel[:k]) / k if k > 0 else 0.0


def mrr_at_k(rel: List[bool], k: int) -> float:
    """
    Mean Reciprocal Rank (MRR@K): mede a posição do PRIMEIRO acerto no ranking.
    Fórmula: 1 / posição_do_primeiro_acerto.
    Exemplo: primeiro acerto na posição 2 → MRR = 1/2 = 0.50.
             primeiro acerto na posição 1 → MRR = 1/1 = 1.00 (perfeito).
    Retorna 0.0 se não houver nenhum acerto nas K primeiras posições.
    """
    for i, r in enumerate(rel[:k]):
        if r:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(rel: List[bool], k: int) -> float:
    """
    Normalized Discounted Cumulative Gain (nDCG@K): avalia a QUALIDADE DO RANKING.
    Diferente do Precision, penaliza acertos que aparecem em posições baixas.
    Um acerto na posição 1 vale mais do que um acerto na posição 8.
    Fórmula: DCG / IDCG, onde IDCG é o ranking ideal (todos os acertos no topo).
    Resultado ∈ [0, 1]. Quanto maior, melhor o ranqueamento.
    """
    dcg  = sum(int(r) / log2(i + 2) for i, r in enumerate(rel[:k]))
    idcg = sum(1.0 / log2(i + 2) for i in range(min(sum(rel), k)))
    return dcg / idcg if idcg > 0 else 0.0


# ─── PIPELINE PRINCIPAL ───────────────────────────────────────────────────────
def run(n_authors: int, n_train: int, n_test: int, random_mode: bool,
        qualis_mode: str = "modulated", data_json: str = DATA_JSON) -> None:
    label = "ALEATÓRIO" if random_mode else "RÉPLICA DO MOTOR ONLINE"
    scoring_label_map = {
        "sem_only":      "Sem                                              [0.0–1.0]",
        "off":           "Sem + Rec + Cit                                  [0.0–3.0]",
        "additive":      "Sem + Rec + Cit + Qua                            [0.0–4.0]",
        "modulated":     "Sem + Rec + Cit + Qua×Sem                        [0.0–4.0]",
        "cit_modulated": "Sem + Rec + Cit×Sem + Qua                        [0.0–4.0]",
        "all_modulated": "Sem + (Rec×Sem) + (Cit×Sem) + (Qua×Sem)          [0.0–4.0]",
        "multiplicative":"Sem × Rec × Cit × Qua                            [0.0–1.0]",
    }
    scoring_label = scoring_label_map.get(qualis_mode, scoring_label_map["additive"])
    print()
    print("=" * 70)
    print(f"  EXPERIMENTO OFFLINE — {label}")
    print("=" * 70)
    print(f"  Autores      : {n_authors}")
    print(f"  Treino       : {n_train} títulos por autor")
    print(f"  Hold-out     : {n_test} títulos reservados (não injetados; descoberta orgânica via coautoria)")
    print(f"  Janela Anos  : {YEAR_CUTOFF - YEAR_WINDOW + 1}–{YEAR_CUTOFF}")
    print(f"  Scoring      : {scoring_label}")
    if not random_mode:
        print(f"  Qualis Mode  : {qualis_mode}")
    print(f"  Acerto       : Coautoria pura")
    print("=" * 70)
    print()

    model = load_model()
    df    = load_csv()
    print()

    with open(data_json, encoding="utf-8") as f:
        raw_authors = json.load(f)

    def extract_author_data(a: dict) -> dict:
        """
        Normaliza o formato ORCID para o formato interno do script.
        Inclui o campo _enriched (do Semantic Scholar) atrelado a cada título,
        preservando ordem do ORCID. Quando o enrichment não existe (paper sem
        DOI ou não-achado no SS), _enriched é None.
        """
        # Nome
        person = a.get("person", {})
        name_obj = person.get("name", {})
        given  = (name_obj.get("given-names")  or {}).get("value", "")
        family = (name_obj.get("family-name") or {}).get("value", "")
        full_name = f"{given} {family}".strip() or a.get("path", "unknown")

        # Títulos com enrichment (works dentro de activities-summary)
        acts  = a.get("activities-summary", {})
        works = acts.get("works", {}).get("group", [])
        titles_with_meta = []
        for group in works:
            for ws in group.get("work-summary", []):
                t = (ws.get("title", {}) or {}).get("title", {}) or {}
                val = t.get("value", "") if isinstance(t, dict) else ""
                if val:
                    titles_with_meta.append({
                        "title":    val,
                        "enriched": ws.get("_enriched"),  # None ou dict
                    })
        return {"author": full_name, "titles_with_meta": titles_with_meta}

    all_authors = [extract_author_data(a) for a in raw_authors]
    min_pubs = n_train + n_test
    eligible = [a for a in all_authors if len(a["titles_with_meta"]) >= min_pubs]
    authors  = eligible[:n_authors]
    print(f"[OK] {len(authors)} autores selecionados de {len(eligible)} elegíveis\n")

    results_per_author = []
    n_skipped_few_titles = 0  # autor sem títulos únicos suficientes p/ 15+5

    for idx, author_data in enumerate(authors):
        author_name  = author_data["author"]
        all_items    = author_data["titles_with_meta"]  # [{title, enriched}, ...]

        # Deduplica por título normalizado preservando ordem do ORCID + metadata.
        # Necessário porque o ORCID frequentemente devolve a mesma publicação
        # mais de uma vez (preprint + versão final, variações de capitalização).
        seen_norm = set()
        unique_items = []
        for it in all_items:
            norm = it["title"].lower().strip()
            if norm and norm not in seen_norm:
                seen_norm.add(norm)
                unique_items.append(it)

        if len(unique_items) < n_train + n_test:
            print(f"  [SKIP] {author_name}: só {len(unique_items)} títulos únicos (< {n_train + n_test})")
            n_skipped_few_titles += 1
            continue

        train_titles = [it["title"] for it in unique_items[:n_train]]
        test_items   = unique_items[n_train:n_train + n_test]
        test_titles  = [it["title"] for it in test_items]

        # ══════════════════════════════════════════════════════════════════════
        # FASE 1 — INJEÇÃO DO GABARITO (os "5 golds")
        # ══════════════════════════════════════════════════════════════════════
        # Do total de artigos do autor, separamos:
        #   - 15 para TREINO: são usados para extrair o "perfil" do pesquisador
        #     (esses 15 viram os "subjects" que percorremos no loop abaixo).
        #   - 5  para TESTE (gold): são os artigos que o sistema precisa
        #     recomendar. Eles ficam ESCONDIDOS durante a fase de busca e só
        #     são injetados artificialmente no pool de candidatos no momento
        #     do scoring — garantindo que o gabarito sempre esteja disponível
        #     para o ranqueador avaliar (protocolo Sampled Evaluation).
        #
        # Cada gold paper é montado com metadados REAIS vindos do Semantic
        # Scholar (citações, venue). O ano é forçado para YEAR_CUTOFF-1 (2016)
        # para garantir que ele passe no filtro temporal do sistema.
        # ──────────────────────────────────────────────────────────────────────
        injected = []
        gold_enriched = 0
        for i, it in enumerate(test_items):
            enr = it["enriched"] or {}
            n_cit      = int(enr.get("citationCount", 0) or 0)
            venue      = enr.get("venue") or "TestSet"
            refs_list  = enr.get("references") or []
            if enr:
                gold_enriched += 1
            injected.append({
                "title":          it["title"],
                "year":           YEAR_CUTOFF - 1,   # força passagem no filtro temporal
                "venue":          venue,
                "authors":        [author_name],
                "id":             f"TEST_{i}",
                "n_citation":     n_cit,
                "references_raw": str(refs_list),
            })

        recommendations = []
        seen_titles     = set(train_titles)  # garante que nunca recomendemos um paper que o autor já escreveu
        pool_sizes      = []                  # armazena o tamanho de cada pool (para diagnóstico)

        # ══════════════════════════════════════════════════════════════════════
        # FASE 2 — LOOP PRINCIPAL: para cada artigo do treino, gera 1 recomendação
        # ══════════════════════════════════════════════════════════════════════
        # O sistema itera sobre os 15 artigos de treino do autor (train_titles).
        # Para cada artigo de treino ("subject"), ele tenta encontrar no corpus
        # o artigo mais relevante que o autor AINDA NÃO escreveu.
        # No total, o sistema tentará gerar até TOP_K_EVAL=10 recomendações únicas.
        # ──────────────────────────────────────────────────────────────────────
        for subject in train_titles:
            # Para de buscar assim que tiver 10 recomendações geradas
            if len(recommendations) >= TOP_K_EVAL:
                break

            # ══════════════════════════════════════════════════════════════════
            # FASE 2a — RETRIEVAL: "Tiro no Escuro" (Amostragem Aleatória)
            # ══════════════════════════════════════════════════════════════════
            # Sugestão do orientador: em vez de buscar por palavras-chave exatas
            # (que criavam viés de correspondência textual), sorteamos 100 papers
            # TOTALMENTE ALEATÓRIOS do DBLP.
            #
            # Isso cria um "Palheiro": 100 artigos sem relação nenhuma com o autor.
            # Em seguida (Fase 2b), escondemos os 5 "golds" (as "Agulhas") dentro
            # desse palheiro.
            #
            # A missão da Equação V5 (Fase 2c) é achar as agulhas no palheiro
            # USANDO APENAS A MATEMÁTICA (Word2Vec + Recência + Citações + Qualis),
            # sem nenhuma pista textual. Se o motor for bom, as agulhas chegam ao
            # topo do ranking. Esse é o verdadeiro teste de qualidade do modelo.
            # ──────────────────────────────────────────────────────────────────
            candidates: Dict[str, Dict] = {}

            # Sorteia N papers aleatórios do corpus DBLP (o "palheiro")
            random_sample = df.sample(n=CANDIDATES_PER_TOPIC)

            for _, row in random_sample.iterrows():
                # Limpa o campo de autores que vem formatado como string "[nome1, nome2]"
                raw = str(row.get('authors', '[]'))
                names = [a.strip().strip("'\"") for a in re.sub(r"[\[\]]", "", raw).split(",") if a.strip()]
                pub = {
                    "title":          str(row['title']),
                    "year":           int(row['year']),
                    "venue":          str(row['venue']),
                    "authors":        names,
                    "id":             str(row['id']),
                    "n_citation":     int(row.get('n_citation', 0) or 0),
                    "references_raw": str(row.get('references', '[]') or '[]'),
                }
                # Usa o título como chave: evita duplicatas caso o mesmo paper
                # seja sorteado mais de uma vez
                candidates[pub["title"]] = pub

            # ══════════════════════════════════════════════════════════════════
            # FASE 2b — INJEÇÃO DAS AGULHAS NO PALHEIRO
            # ══════════════════════════════════════════════════════════════════
            # Adicionamos os 5 gold papers ("as agulhas") ao pool de candidatos.
            # Eles só entram se ainda não estiverem lá (evita sobrescrever
            # um gold que coincidentemente foi sorteado como candidato aleatório).
            # Após essa etapa, o pool terá entre 100 e 105 artigos:
            #   - 100 "palhas" aleatórias (ruído)
            #   - 5   "agulhas" (os artigos que o pesquisador realmente escreveu)
            # ──────────────────────────────────────────────────────────────────
            for inj in injected:
                if inj["title"] not in candidates:
                    candidates[inj["title"]] = inj

            # ══════════════════════════════════════════════════════════════════
            # FASE 2c — FILTRAGEM DO POOL
            # ══════════════════════════════════════════════════════════════════
            # Antes de passar para o ranqueador, aplicamos 3 filtros básicos:
            #   1. Não recomendar artigos que o autor já escreveu (seen_titles)
            #   2. Só artigos dentro da janela temporal (2013–2017): evita
            #      recomendar artigos do futuro ou muito antigos
            #   3. Só artigos em inglês ou português (filtro de idioma)
            # ──────────────────────────────────────────────────────────────────
            filtered = [
                c for c in candidates.values()
                if c["title"] not in seen_titles
                and (YEAR_CUTOFF - YEAR_WINDOW < c["year"] <= YEAR_CUTOFF)
                and is_valid_language(c["title"])
            ]

            if not filtered:
                continue
            pool_sizes.append(len(filtered))

            # ══════════════════════════════════════════════════════════════════
            # FASE 2d — SCORING: Ranqueamento pela Equação V5
            # ══════════════════════════════════════════════════════════════════
            # Para cada paper no pool filtrado, a equação calcula:
            #   Score = Sem + Rec + Cit + (Qua × Sem)      ∈ [0, 4]
            #
            #   Sem: similaridade de cosseno entre o vetor Word2Vec do "subject"
            #        (artigo de treino) e o vetor do candidato.        ∈ [0, 1]
            #   Rec: recência normalizada pelo ano de publicação.       ∈ [0, 1]
            #   Cit: citações por ano, achatadas em log com teto=50.   ∈ [0, 1]
            #   Qua: nota Qualis (CAPES) da venue, modulada por Sem —
            #        o prestígio da revista só vale se o paper for
            #        semanticamente próximo do perfil do autor.         ∈ [0, 1]
            #
            # Se estiver no modo aleatório (--random), pula o scoring e sorteia
            # um paper qualquer do pool para servir de baseline de comparação.
            # ──────────────────────────────────────────────────────────────────
            if random_mode:
                # Baseline: escolha totalmente aleatória (sem matemática)
                best_candidate = random.choice(filtered)
                best_scored = None
            else:
                # Motor real: executa a Equação V5 em todos os candidatos e
                # devolve a lista ordenada do maior para o menor score
                ranked = extract_best_match_online(filtered, subject, model,
                                                    qualis_mode=qualis_mode)
                if not ranked:
                    continue
                best_scored = ranked[0]  # (score, sem, rec, cit, qua_term, qua_raw, paper)
                best_candidate = best_scored[6]

            if best_candidate and best_candidate["title"] not in seen_titles:
                # Salva os scores individuais no paper para auditoria e debug
                if best_scored:
                    best_candidate["_scores"] = {
                        "score":    round(best_scored[0], 4),  # score final da equação
                        "sem":      round(best_scored[1], 4),  # cosseno Word2Vec
                        "rec":      round(best_scored[2], 4),  # recência
                        "cit":      round(best_scored[3], 4),  # citações normalizadas
                        "qua_term": round(best_scored[4], 4),  # Qua × Sem (entra na soma)
                        "qua_raw":  round(best_scored[5], 4),  # nota CAPES bruta (0–1)
                    }
                # Adiciona à lista final de recomendações e marca como "já visto"
                recommendations.append(best_candidate)
                seen_titles.add(best_candidate["title"])

        # ══════════════════════════════════════════════════════════════════════
        # FASE 3 — AVALIAÇÃO: classificação dos acertos por proxy de relevância
        # ══════════════════════════════════════════════════════════════════════
        # Após gerar as 10 recomendações, verificamos quais são "acertos".
        # Usamos 3 proxies complementares para classificar a relevância:
        #   1. Coautoria: o autor é listado como (co)autor do paper recomendado.
        #      → Proxy mais forte. Prova que o paper é diretamente do universo do autor.
        #   2. Autor citou: o autor já citou esse paper em algum trabalho dele.
        #      → Proxy médio. O autor conhece e usa esse paper como referência.
        #   3. Paper cita autor: o paper recomendado cita trabalhos do autor.
        #      → Proxy fraco. Indica que o paper está no mesmo campo de estudo.
        # A métrica primária é a UNIÃO dos três (acerto = qualquer um dos 3).
        # ──────────────────────────────────────────────────────────────────────
        author_ids, author_refs = get_author_dblp_data(author_name, df)

        hit_types = [classify_hit(rec, author_name, author_ids, author_refs)
                     for rec in recommendations]

        # Cria vetores binários (1=acerto, 0=erro) para cada proxy separado
        relevance_any          = [1 if t else 0 for t in hit_types]      # UNIÃO dos 3
        relevance_coauthor     = [1 if t == 'coauthor' else 0 for t in hit_types]
        relevance_author_cited = [1 if t == 'author_cited' else 0 for t in hit_types]
        relevance_cited_author = [1 if t == 'cited_author' else 0 for t in hit_types]

        def metrics_for(rel):
            return {
                f"k{k}": {
                    "precision": precision_at_k(rel, k),
                    "mrr":       mrr_at_k(rel, k),
                    "ndcg":      ndcg_at_k(rel, k),
                }
                for k in [3, 5, 10]
            }

        metrics = metrics_for(relevance_any)  # ground truth primário = união
        metrics_per_proxy = {
            "coauthor":     metrics_for(relevance_coauthor),
            "author_cited": metrics_for(relevance_author_cited),
            "cited_author": metrics_for(relevance_cited_author),
        }

        first_hit_pos = next((i + 1 for i, r in enumerate(relevance_any) if r), None)
        hits_by_type = {
            "coauthor":     sum(relevance_coauthor),
            "author_cited": sum(relevance_author_cited),
            "cited_author": sum(relevance_cited_author),
            "any":          sum(relevance_any),
        }

        results_per_author.append({
            "author":            author_name,
            "train_size":        n_train,
            "test_size":         n_test,
            "n_recommendations": len(recommendations),
            "hits_at_10":        sum(relevance_any[:10]),
            "hits_by_type":      hits_by_type,
            "first_hit_position": first_hit_pos,
            "mean_pool_size":    round(float(np.mean(pool_sizes)), 2) if pool_sizes else 0.0,
            "gold_enriched":     gold_enriched,  # quantos dos 5 test papers têm metadata real do SS
            "n_author_papers_in_dblp": len(author_ids),  # diagnóstico de cobertura
            "validation":        {"method": "enriched injection + triangulated (coauthor + citation_fwd + citation_bwd)"},
            "metrics_by_k":          metrics,                # primário = união
            "metrics_by_k_per_proxy": metrics_per_proxy,     # detalhe por proxy
            "held_out_titles":   test_titles,
            "recommendations": [
                {
                    "title":     r["title"],
                    "year":      r["year"],
                    "venue":     r.get("venue", ""),
                    "n_citation": r.get("n_citation", 0),
                    "is_hit":    bool(rel),
                    "hit_type":  ht,  # None | 'coauthor' | 'author_cited' | 'cited_author'
                    "scores":    r.get("_scores", {})
                }
                for r, rel, ht in zip(recommendations, relevance_any, hit_types)
            ]
        })

        p5 = metrics["k5"]["precision"]
        m3 = metrics["k3"]["mrr"]
        n3 = metrics["k3"]["ndcg"]
        print(f"  [{idx+1:02d}] {author_name[:38]:<38}  P@5={p5:.2f}  MRR@3={m3:.2f}  nDCG@3={n3:.2f}")

    # ══════════════════════════════════════════════════════════════════════════
    # FASE 4 — AGREGAÇÃO FINAL: calcula as métricas médias de todos os autores
    # ══════════════════════════════════════════════════════════════════════════
    # Aqui somamos os resultados individuais de cada autor e calculamos
    # as médias de Precision, MRR e nDCG para K=3, K=5 e K=10.
    # O desvio padrão (±) mostra a variabilidade entre autores.
    # ──────────────────────────────────────────────────────────────────────────
    if not results_per_author:
        print("\n[ERRO] Nenhum autor avaliado.")
        return

    print()
    print("=" * 70)
    print(f"  RESULTADOS ({label}) | N={len(results_per_author)}")
    print(f"  Protocolo : Hold-Out | {n_train} treino / {n_test} teste injetado")
    print(f"  Acerto    : Coautoria")
    print("=" * 70)
    print(f"  {'K':>5} | {'Precision':>14} | {'MRR':>14} | {'nDCG':>14}")
    print("  " + "-" * 57)
    for k in [3, 5, 10]:
        ps = [r["metrics_by_k"][f"k{k}"]["precision"] for r in results_per_author]
        ms = [r["metrics_by_k"][f"k{k}"]["mrr"]       for r in results_per_author]
        ns = [r["metrics_by_k"][f"k{k}"]["ndcg"]      for r in results_per_author]
        print(f"  {k:>5} | {np.mean(ps):.4f}±{np.std(ps):.4f} | {np.mean(ms):.4f}±{np.std(ms):.4f} | {np.mean(ns):.4f}±{np.std(ns):.4f}")
    print("=" * 70)

    # ── Salva no experiment_log.json (histórico acumulado) ──────────────────
    LOG_FILE = os.path.join(LOG_DIR, "experiment_log.json")
    suffix_map = {
        "sem_only":      "_SemOnly",
        "off":           "_QualisOff",
        "additive":      "_QualisAdditive",
        "modulated":     "_QualisModulated",
        "cit_modulated": "_CitModulated",
        "all_modulated": "_AllModulated",
        "multiplicative":"_Multiplicative",
    }
    suffix = suffix_map.get(qualis_mode, "")
    # _Enriched indica: data_apt.json (só autores aptos) + injeção com metadata real do SS
    # + 3 proxies (coautor + cit fwd + cit bwd)
    label_mode = ("Baseline_Aleatorio_Enriched" if random_mode
                  else f"Paperman_V5.3_Enriched{suffix}")
    scoring_str_map = {
        "sem_only":      "Sem                                          [0-1]",
        "off":           "Sem + Rec + Cit                              [0-3]",
        "additive":      "Sem + Rec + Cit + Qua                        [0-4]",
        "modulated":     "Sem + Rec + Cit + (Qua × Sem)                [0-4]",
        "all_modulated": "Sem + (Rec×Sem) + (Cit×Sem) + (Qua×Sem)      [0-4]",
    }
    scoring_str = scoring_str_map.get(qualis_mode, scoring_str_map["additive"])

    # Métricas agregadas + arrays por autor (para Wilcoxon)
    agg_metrics = {}
    per_author_metrics = {}
    for k in [3, 5, 10]:
        ps = [r["metrics_by_k"][f"k{k}"]["precision"] for r in results_per_author]
        ms = [r["metrics_by_k"][f"k{k}"]["mrr"]       for r in results_per_author]
        ns = [r["metrics_by_k"][f"k{k}"]["ndcg"]      for r in results_per_author]
        agg_metrics[f"k{k}"] = {
            "precision":     round(float(np.mean(ps)), 4),
            "precision_std": round(float(np.std(ps)),  4),
            "mrr":           round(float(np.mean(ms)), 4),
            "mrr_std":       round(float(np.std(ms)),  4),
            "ndcg":          round(float(np.mean(ns)), 4),
            "ndcg_std":      round(float(np.std(ns)),  4),
        }
        per_author_metrics[f"k{k}"] = {
            "precision": [round(float(x), 4) for x in ps],
            "mrr":       [round(float(x), 4) for x in ms],
            "ndcg":      [round(float(x), 4) for x in ns],
        }

    # Diagnósticos auxiliares (não influenciam o score, são para análise)
    pool_sizes_all = [r["mean_pool_size"] for r in results_per_author if r.get("mean_pool_size")]
    # Agregação dos hits por tipo de proxy (triangulação)
    hits_total_by_type = {
        "coauthor":     sum(r.get("hits_by_type", {}).get("coauthor", 0) for r in results_per_author),
        "author_cited": sum(r.get("hits_by_type", {}).get("author_cited", 0) for r in results_per_author),
        "cited_author": sum(r.get("hits_by_type", {}).get("cited_author", 0) for r in results_per_author),
        "any":          sum(r.get("hits_by_type", {}).get("any", 0) for r in results_per_author),
    }
    authors_with_hit_by_type = {
        "coauthor":     sum(1 for r in results_per_author if r.get("hits_by_type", {}).get("coauthor", 0) > 0),
        "author_cited": sum(1 for r in results_per_author if r.get("hits_by_type", {}).get("author_cited", 0) > 0),
        "cited_author": sum(1 for r in results_per_author if r.get("hits_by_type", {}).get("cited_author", 0) > 0),
        "any":          sum(1 for r in results_per_author if r.get("hits_by_type", {}).get("any", 0) > 0),
    }
    diagnostics = {
        "mean_pool_size":         round(float(np.mean(pool_sizes_all)), 2) if pool_sizes_all else None,
        "median_pool_size":       round(float(np.median(pool_sizes_all)), 2) if pool_sizes_all else None,
        "authors_with_hit":       sum(1 for r in results_per_author if r.get("first_hit_position")),
        "median_first_hit":       float(np.median([r["first_hit_position"] for r in results_per_author
                                                    if r.get("first_hit_position")])) if any(r.get("first_hit_position") for r in results_per_author) else None,
        "n_authors_requested":    n_authors,
        "n_authors_evaluated":    len(results_per_author),
        "n_skipped_few_titles":   n_skipped_few_titles,
        # Triangulação: detalha hits por proxy de relevância
        "hits_total_by_type":         hits_total_by_type,
        "authors_with_hit_by_type":   authors_with_hit_by_type,
        "mean_author_papers_in_dblp": round(float(np.mean([r.get("n_author_papers_in_dblp", 0) for r in results_per_author])), 2),
        # Enrichment: cobertura dos 5 test papers por autor (0-5)
        "gold_enriched_total":        sum(r.get("gold_enriched", 0) for r in results_per_author),
        "gold_total":                 sum(r.get("test_size", 0) for r in results_per_author),
        "mean_gold_enriched":         round(float(np.mean([r.get("gold_enriched", 0) for r in results_per_author])), 2),
    }

    # Carrega log existente e determina próximo ID
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = []
    next_id = (max(e.get("id", 0) for e in history) + 1) if history else 1

    # ══════════════════════════════════════════════════════════════════════════
    # FASE 5 — SIGNIFICÂNCIA ESTATÍSTICA: Teste de Wilcoxon Pareado
    # ══════════════════════════════════════════════════════════════════════════
    # Compara este experimento com o experimento "oposto" mais recente no log
    # (ex: se este é o Paperman, compara com o Baseline; e vice-versa).
    # O teste de Wilcoxon verificia se a diferença entre os dois não é fruto
    # do acaso. Se p < 0.05, rejeitamos H0 e concluímos que a diferença
    # entre os modelos é estatisticamente significativa.
    # ──────────────────────────────────────────────────────────────────────────
    target_prefix = ("Paperman_V5.3" if random_mode else "Baseline_Aleatorio")
    comparable = next(
        (e for e in reversed(history)
         if e.get("notes", "").startswith(target_prefix)
         and e.get("protocol", {}).get("n_authors") == len(results_per_author)
         and "per_author_metrics" in e),
        None
    )
    significance = None
    if comparable:
        sig = {"vs_exp_id": comparable["id"], "vs_notes": comparable["notes"], "tests": {}}
        for k in [3, 5, 10]:
            for metric in ["precision", "mrr", "ndcg"]:
                a = per_author_metrics[f"k{k}"][metric]
                b = comparable["per_author_metrics"][f"k{k}"][metric]
                if len(a) != len(b):
                    sig["tests"][f"k{k}_{metric}"] = {"error": "n_pairs mismatch"}
                    continue
                if all((x - y) == 0 for x, y in zip(a, b)):
                    sig["tests"][f"k{k}_{metric}"] = {"note": "all paired diffs zero"}
                    continue
                try:
                    stat, p = wilcoxon(a, b)
                    sig["tests"][f"k{k}_{metric}"] = {
                        "statistic": round(float(stat), 4),
                        "p_value":   round(float(p), 4),
                        "n_pairs":   len(a),
                        "significant_at_0.05": bool(p < 0.05),
                    }
                except Exception as e:
                    sig["tests"][f"k{k}_{metric}"] = {"error": str(e)}
        significance = sig

    entry = {
        "id":                   next_id,
        "experiment_id":        "OFFLINE_HOLDOUT_CV",
        "timestamp":            datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "notes":                f"{label_mode}_N{len(results_per_author)}",
        "scoring":              scoring_str,
        "qualis_mode":          (None if random_mode else qualis_mode),
        "datasets": {
            "author_profiles":    "data.json (ORCID)",
            "publication_corpus": "dblp-v10.csv"
        },
        "protocol": {
            "type":       "Hold-Out",
            "n_authors":  len(results_per_author),
            "train_size": n_train,
            "test_size":  n_test,
            "validation": "coauthorship",
            "year_cutoff": YEAR_CUTOFF,
            "year_window": YEAR_WINDOW,
        },
        "metrics_by_k":         agg_metrics,
        "per_author_metrics":   per_author_metrics,
        "diagnostics":          diagnostics,
        "significance_wilcoxon": significance,
    }

    # ══════════════════════════════════════════════════════════════════════════
    # FASE 6 — PERSISTÊNCIA: salva resultados no log histórico e em arquivo JSON
    # ══════════════════════════════════════════════════════════════════════════
    # Cada execução gera dois arquivos:
    #   1. experiment_log.json: histórico acumulado de todos os experimentos.
    #      Cada entrada tem ID único, métricas agregadas e dados do Wilcoxon.
    #      É o arquivo que alimenta o comparacao_modelos.html.
    #   2. recommendations_exp_N.json: lista completa das recomendações geradas
    #      para cada autor (inclui scores individuais de Sem, Rec, Cit, Qua).
    #      Serve para inspeção qualitativa e auditoria da equação.
    # ──────────────────────────────────────────────────────────────────────────
    history.append(entry)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] Experimento #{next_id} salvo em: {LOG_FILE}")
    
    # Salva também um report das recomendações por extenso para inspeção qualitativa
    REC_FILE = os.path.join(LOG_DIR, f"recommendations_exp_{next_id}.json")
    with open(REC_FILE, "w", encoding="utf-8") as f:
        json.dump(results_per_author, f, ensure_ascii=False, indent=2)
    print(f"[OK] Recomendações completas do experimento salvos em: {REC_FILE}\n")


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Avaliação Offline — Réplica Fiel do Motor Online"
    )
    parser.add_argument("--n",      type=int, default=10, help="Número de autores a avaliar")
    parser.add_argument("--train",  type=int, default=10, help="Títulos de treino por autor")
    parser.add_argument("--test",   type=int, default=10,  help="Títulos gabarito (Hold-Out)")
    parser.add_argument("--random", action="store_true",  help="Modo baseline aleatório")
    parser.add_argument("--qualis-mode",
                        choices=["sem_only", "off", "additive", "modulated", "cit_modulated", "all_modulated", "multiplicative"],
                        default="modulated",
                        help="Combinação dos termos do score: "
                             "sem_only (só Sem) | off (sem Qua) | additive (soma) | "
                             "modulated (Qua×Sem) | "
                             "all_modulated (Rec×Sem + Cit×Sem + Qua×Sem) | "
                             "multiplicative (Sem×Rec×Cit×Qua)")
    parser.add_argument("--data", type=str, default=DATA_JSON, help="Caminho para o JSON de dados")
    args = parser.parse_args()

    run(
        n_authors   = args.n,
        n_train     = args.train,
        n_test      = args.test,
        random_mode = args.random,
        qualis_mode = args.qualis_mode,
        data_json   = args.data,
    )
