import json
import pandas as pd
import asyncio
import numpy as np
import re
import argparse
from difflib import SequenceMatcher
from typing import List, Dict
from time import time
from pathlib import Path

import sys
import random
sys.path.append(str(Path(__file__).parent))

from word_embedding.gensim import build_search_query, extract_best_match
from schemas.publication import Publication, Author
from lingua import Language, LanguageDetectorBuilder

# ─── ISOLAMENTO OFFLINE: Garante zero acesso à rede durante o experimento ───
# O venue score é substituído por um mock local (retorna 0).
# Isso assegura que todas as métricas reflitam exclusivamente a semântica
# dos títulos, sem qualquer influência de dados externos como ranking de venue.
import word_embedding.gensim as _gensim_module
async def _offline_venue_score(publication):
    return 0
_gensim_module.get_venue_score = _offline_venue_score

# ─── RANQUEAMENTO SEMÂNTICO PURO: Score baseado exclusivamente em Word2Vec ──
# O sistema avalia candidatos usando apenas similaridade semântica de títulos.
# Utiliza Sentence Embedding via Mean Pooling: calcula o vetor médio das
# palavras de cada título e compara com cosine similarity.
from word_embedding.gensim import cosine_similarity as _cosine_sim, load_model as _load_model
from nlp.nltk import NTLKService as _NTLKService

async def _semantic_extract_best_match(publications, subject):
    """
    Sentence Embedding via Mean Pooling.

    Para cada título, calcula o vetor médio (Mean Pool) das palavras
    presentes no vocabulário Word2Vec e compara com cosine similarity.
    Retorna a publicação com maior semelhança semântica ao subject.
    """
    ntlk_service = _NTLKService()
    model = _load_model()

    # Vetor médio do título de treino (subject)
    subject_words = ntlk_service.clean_publication_title(subject)
    subject_vecs  = [model[w] for w in subject_words if w in model]

    if not subject_vecs:
        return publications[0]  # sem vocabulário, retorna primeiro

    subject_vec = np.mean(subject_vecs, axis=0)

    for pub in publications:
        pub_words = ntlk_service.clean_publication_title(pub.title)
        pub_vecs  = [model[w] for w in pub_words if w in model]
        if not pub_vecs:
            pub.score = 0.0
            continue
        pub_vec    = np.mean(pub_vecs, axis=0)
        pub.score  = float(_cosine_sim(subject_vec, pub_vec))

    return max(publications, key=lambda x: x.score)

# Sobrescreve o extract_best_match no escopo local E no módulo
extract_best_match = _semantic_extract_best_match
_gensim_module.extract_best_match = _semantic_extract_best_match

# ─── Configurações do Experimento ─────────────────────────────
DATA_JSON            = r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados\data.json"
DBLP_CSV             = r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados\dblp-v10.csv"
MIN_PUBLICATIONS     = 20        # Mínimo de publicações por autor
YEAR_CUTOFF          = 2017      # Simulação temporal (ano de referência)
YEAR_WINDOW          = 5         # Janela: artigos entre 2012 e 2017
TOP_K                = 10        # Recomendações geradas por avaliação (suporte a K@3, K@5, K@10)
CANDIDATES_PER_TOPIC = 100       # Candidatos por busca de tópico (Aumentado para melhorar a abrangência)

# ─── Configurações do Protocolo Hold-Out ─────────────────────
N_AUTHORS                = 82    # Tamanho do grupo de teste (Mudar para 82 para o teste completo)
TRAIN_SIZE               = 15    # Títulos usados para treino (perfil)
TEST_SIZE                = 5     # Títulos injetados no corpus como gabarito
TITLE_SIMILARITY_THRESHOLD = 0.60  # Similaridade mínima de título para considerar ACERTO


# ==============================================================
#  ETAPA 1 - DEFINIÇÃO DO CONJUNTO DE DADOS
# ==============================================================
print("[Etapa 1] Inicializando conjunto de dados...")

# Detector de idioma (filtra apenas EN e PT)
LANGUAGES     = [Language.PORTUGUESE, Language.ENGLISH]
lang_detector = LanguageDetectorBuilder.from_all_languages().build()

# Carrega o Research Papers Dataset localmente (Original dblp-v10.csv - 1.7GB)
print(f"[Etapa 1] Carregando Research Papers Dataset (dblp-v10.csv)...")
df = pd.read_csv(DBLP_CSV, on_bad_lines='skip', low_memory=False)
df['title_norm'] = df['title'].str.lower().str.strip()
print(f"[Etapa 1] {len(df):,} artigos carregados com sucesso (linhas corrompidas puladas).\n")


# ==============================================================
#  FUNÇÕES AUXILIARES
# ==============================================================

def name_norm(text: str) -> str:
    """Normaliza nomes para comparação de coautoria."""
    if not text:
        return ""
    return re.sub(r'[^a-z]', '', str(text).lower())


def search_by_topic(query: str) -> List[Dict]:
    """Busca artigos candidatos no dataset local por correspondência de tópico."""
    q = query.lower().strip()
    hits = df[df['title_norm'].str.contains(q, na=False, regex=False)].head(CANDIDATES_PER_TOPIC)
    results = []
    for _, row in hits.iterrows():
        raw = str(row['authors'])
        names = [a.strip().strip("'\"") for a in re.sub(r"[\[\]]", "", raw).split(",") if a.strip()]
        results.append({
            "title":   str(row['title']),
            "year":    int(row['year']),
            "venue":   str(row['venue']),
            "authors": names,
            "id":      str(row['id']),
        })
    return results


_author_papers_cache: Dict[str, List[Dict]] = {}

def search_by_author(author_name: str) -> List[Dict]:
    """Busca artigos do autor-alvo no dataset local (simula base DBLP completa)."""
    if author_name in _author_papers_cache:
        return _author_papers_cache[author_name]

    surname = author_name.split()[-1].lower() if author_name.split() else ""
    if len(surname) < 3:
        _author_papers_cache[author_name] = []
        return []

    matches = df[df['authors'].str.lower().str.contains(surname, na=False, regex=False)]
    full_lower = author_name.lower()
    precise = matches[matches['authors'].str.lower().str.contains(full_lower, na=False, regex=False)]

    results = []
    for _, row in precise.iterrows():
        raw = str(row['authors'])
        names = [a.strip().strip("'\"") for a in re.sub(r"[\[\]]", "", raw).split(",") if a.strip()]
        results.append({
            "title":   str(row['title']),
            "year":    int(row['year']),
            "venue":   str(row['venue']),
            "authors": names,
            "id":      str(row['id']),
        })

    _author_papers_cache[author_name] = results
    return results


def is_valid_language(title: str) -> bool:
    """Filtra artigos por idioma (apenas Inglês e Português)."""
    detected = lang_detector.detect_language_of(title)
    return detected in LANGUAGES


# Threshold de similaridade para Fuzzy Match (0.0 a 1.0)
# 0.82 = tolera typos e iniciais, evita falsos positivos em nomes comuns
FUZZY_THRESHOLD = 0.82

def fuzzy_name_match(name_a: str, name_b: str) -> bool:
    """
    Verifica similaridade entre dois nomes normalizados.
    Cobre casos como:
      - Iniciais: 'jsmith' vs 'johnsmith' -> MATCH
      - Typos: 'bernhard' vs 'bernard'   -> MATCH
      - Abreviações: 'jmurphy' vs 'johnmurphy' -> MATCH
    """
    if not name_a or not name_b:
        return False
    # Match exato
    if name_a in name_b or name_b in name_a:
        return True
    # Match por similaridade (Levenshtein aproximado via SequenceMatcher)
    ratio = SequenceMatcher(None, name_a, name_b).ratio()
    return ratio >= FUZZY_THRESHOLD


def check_coauthorship(target_name: str, rec_authors: List[str]) -> bool:
    """
    HEURíSTICA FUNDAMENTAL (com Fuzzy Matching v2):
    Uma recomendação só é considerada relevante se o autor-alvo estiver
    listado como autor principal ou coautor do artigo recomendado.
    Usa correspondência fuzzy para tolerar variações de nome (iniciais, typos).
    """
    target_norm = name_norm(target_name)
    for author in rec_authors:
        a_norm = name_norm(author)
        if len(a_norm) > 3 and fuzzy_name_match(target_norm, a_norm):
            return True
    return False


def compute_match_score(
    rec_title:   str,
    test_titles: List[str],
) -> float:
    """Similaridade máxima entre o título recomendado e os títulos de teste."""
    if not test_titles:
        return 0.0
    return round(
        max(
            SequenceMatcher(None, rec_title.lower(), t.lower()).ratio()
            for t in test_titles
        ),
        4
    )


def evaluate_relevance(
    rec_title:   str,
    rec_authors: List[str],
    test_titles: List[str],
    author_name: str,
) -> tuple:
    """
    Validação com Relevância Graduada (Graded Relevance):

      Grau 3 — GOLDEN MATCH : Título ≥ 60% + Coautoria  (acerto perfeito)
      Grau 2 — TOPIC MATCH  : Apenas Título ≥ 60%        (acerto de tópico)
      Grau 0 — MISS         : Nenhum critério            (erro)

    Apenas similaridade de título ≥ 60% qualifica um acerto. Coautoria
    isolada (sem título similar) é tratada como Miss, pois seria alcançável
    trivialmente por qualquer baseline aleatório num pool filtrado por tópico.

    Retorna: (grade: int, title_sim: float, match_reason: str)
    """
    title_sim  = compute_match_score(rec_title, test_titles)
    title_hit  = title_sim >= TITLE_SIMILARITY_THRESHOLD
    author_hit = check_coauthorship(author_name, rec_authors)

    if title_hit and author_hit:
        return 3, title_sim, "golden_match"  # 🥇 Acerto Perfeito
    if title_hit:
        return 2, title_sim, "title_match"   # 🥈 Acerto de Tópico
    return 0, title_sim, "no_match"          # ❌ Miss (coautoria isolada não conta)



# ==============================================================
#  ETAPA 3 - MÉTRICAS DE AVALIAÇÃO
# ==============================================================

def precision_at_k(rel: List[int], k: int) -> float:
    """Precision@K: porcentagem de artigos relevantes nos K recomendados."""
    return sum(rel[:k]) / k


def mrr_at_k(rel: List[int], k: int) -> float:
    """MRR@K: pontuação maior quando o primeiro acerto está no topo."""
    for i, r in enumerate(rel[:k]):
        if r > 0:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(rel: List[int], k: int) -> float:
    """nDCG@K: avalia se os itens mais relevantes estão nas primeiras posições."""
    dcg  = sum((2**r - 1) / np.log2(i + 2) for i, r in enumerate(rel[:k]))
    idcg = sum((2**r - 1) / np.log2(i + 2) for i, r in enumerate(sorted(rel, reverse=True)[:k]))
    return dcg / idcg if idcg > 0 else 0.0


# ==============================================================
#  ETAPA 2 - GERAÇÃO DE RECOMENDAÇÕES
# ==============================================================

async def generate_recommendations(author: Dict, injected_titles: List[Dict] = None, random_baseline: bool = False) -> List[Dict]:
    """
    Geração de Recomendações — Arquitetura de Busca Temática + Perfil Agregado.

    O sistema opera em três etapas:

      1. PERFIL DO AUTOR (DNA Semântico):
         Calcula o vetor médio (Mean Pooling) de TODOS os títulos de treino.
         Esse vetor representa o interesse científico geral do pesquisador.

      2. BUSCA TEMÁTICA MÚLTIPLA (Pool Focado por Título):
         Para cada um dos 15 títulos de treino, extrai palavras-chave e busca
         até 100 candidatos no corpus DBLP. Os 5 papers de teste (gabarito)
         são injetados em cada pool para garantir testabilidade.

      3. RANQUEAMENTO PELO PERFIL AGREGADO:
         Dentro de cada pool focado (~100 candidatos), cada artigo é avaliado
         pela sua similaridade cosseno com o Perfil do Autor (DNA completo),
         não pelo título que originou a busca. O melhor candidato de cada pool
         ganha uma vaga nas recomendações finais.

    A separação entre busca (por tópico) e avaliação (pelo perfil completo)
    garante ao mesmo tempo diversidade temática e precisão semântica.
    """
    ntlk_service = _NTLKService()
    model        = _load_model()

    # ── 1. Perfil do Autor: média dos vetores de TODOS os títulos de treino ──
    profile_vecs = []
    for title in author['titles']:
        words = ntlk_service.clean_publication_title(title)
        vecs  = [model[w] for w in words if w in model]
        if vecs:
            profile_vecs.append(np.mean(vecs, axis=0))

    author_profile = np.mean(profile_vecs, axis=0) if profile_vecs else None

    # ── 2. Pré-carrega artigos do autor no dataset ──
    author_papers  = search_by_author(author['name'])
    recommendations = []
    seen_titles     = set()

    # ── 3. Para cada título de treino: pool focado + score contra perfil ──
    for title in author['titles']:
        if len(recommendations) >= TOP_K:
            break

        topics = build_search_query(title)
        if not topics:
            continue

        # Busca Temática: monta pool focado nos tópicos extraídos deste título
        candidates: Dict[str, Dict] = {}
        for topic in topics:
            for c in search_by_topic(topic):
                if c['title'] not in candidates:
                    candidates[c['title']] = c

        for c in author_papers:
            if c['title'] not in candidates:
                candidates[c['title']] = c

        # Injeção de Gabarito: os 5 papers de teste são sempre incluídos no pool
        # para garantir que o sistema tenha a oportunidade de encontrá-los
        if injected_titles:
            for inj in injected_titles:
                if inj['title'] not in candidates:
                    candidates[inj['title']] = inj

        # Filtragem: janela temporal + idioma + já recomendado
        filtered = [
            c for c in candidates.values()
            if c['title'] not in seen_titles
            and (YEAR_CUTOFF - YEAR_WINDOW < c['year'] <= YEAR_CUTOFF)
            and is_valid_language(c['title'])
        ]

        if not filtered:
            continue

        # Seleção do Melhor Candidato do Pool:
        # — Baseline Aleatório: escolha aleatória (usado para comparação)
        # — Paperman: ranqueia todos os candidatos pela similaridade cosseno
        #   com o Perfil Agregado do autor (DNA semântico completo)
        if random_baseline:
            best_c = random.choice(filtered)
        elif author_profile is not None:
            best_score, best_c = -1.0, filtered[0]
            for c in filtered:
                pub_words = ntlk_service.clean_publication_title(c['title'])
                pub_vecs  = [model[w] for w in pub_words if w in model]
                if pub_vecs:
                    score = float(_cosine_sim(author_profile, np.mean(pub_vecs, axis=0)))
                    if score > best_score:
                        best_score, best_c = score, c
        else:
            best_c = filtered[0]  # fallback: sem vocabulário no modelo

        if best_c['title'] not in seen_titles:
            seen_titles.add(best_c['title'])
            recommendations.append({
                "title":   best_c['title'],
                "authors": best_c['authors'],
            })

    return recommendations


# ==============================================================
#  ETAPA 4 - EXECUÇÃO E ANÁLISE DOS RESULTADOS
# ==============================================================

async def main(notes: str = "Sem anotações", random_baseline: bool = False):
    t_start = time()  # Marca o início para calcular o tempo total
    print("  🔬 EXPERIMENTO OFFLINE - PAPERMAN")
    print("  Validação Quantitativa do Sistema de Recomendação")
    print(f"{'='*65}")

    # ── Etapa 1: Carrega perfis ORCID ──
    with open(DATA_JSON, encoding="utf-8") as f:
        data = json.load(f)

    authors_pool = []
    for entry in data:
        try:
            name_obj  = entry["person"]["name"]
            given     = (name_obj.get("given-names") or {}).get("value", "")
            family    = (name_obj.get("family-name") or {}).get("value", "")
            full_name = f"{given} {family}".strip()
            orcid     = entry.get("orcid-identifier", {}).get("path", "")
            works     = entry.get("activities-summary", {}).get("works", {}).get("group", [])
            titles    = [
                g["work-summary"][0]["title"]["title"]["value"]
                for g in works
                if g.get("work-summary")
                and g["work-summary"][0].get("title", {}).get("title", {}).get("value")
            ]
            if len(titles) >= MIN_PUBLICATIONS and full_name and orcid:
                authors_pool.append({
                    "name": full_name,
                    "titles": titles,
                    "orcid": orcid
                })
        except Exception:
            continue

    print(f"[Etapa 1] {len(authors_pool)} autores selecionados (mínimo {MIN_PUBLICATIONS} publicações)\n")

    # ── Seleção do Grupo de Teste (N_AUTHORS aleatórios com seed fixo) ──
    import random
    random.seed(42)
    random.shuffle(authors_pool)
    test_group = [a for a in authors_pool if len(a['titles']) >= TRAIN_SIZE + TEST_SIZE][:N_AUTHORS]

    print(f"[Etapa 1] Grupo de teste: {len(test_group)} autores selecionados")
    print(f"[Etapa 1] Protocolo: Hold-Out | Treino={TRAIN_SIZE} títulos | Teste={TEST_SIZE} títulos injetados\n")

    # ── Estruturas de acumulação de métricas ──
    metrics_acc = {k: {"p": [], "mrr": [], "ndcg": []} for k in [3, 5, 10]}
    detailed_results = []

    for idx, auth in enumerate(test_group, 1):
        titles_all   = auth['titles'][:TRAIN_SIZE + TEST_SIZE]
        train_titles = titles_all[:TRAIN_SIZE]   # 15 títulos de treino
        test_titles  = titles_all[TRAIN_SIZE:]   # 5 títulos da Caixa Preta

        # Monta objetos de injeção dos 5 títulos de teste no corpus
        injected = [
            {
                "title":   t,
                "title_norm": t.lower().strip(),
                "authors": [auth['name']],
                "year":    YEAR_CUTOFF - 1,
                "venue":   "TestSet",
                "id":      f"inj_{abs(hash(t))}",
            }
            for t in test_titles
        ]

        # Monta perfil com apenas os 15 títulos de treino
        auth_train = {**auth, "titles": train_titles}

        print(f"[{idx:>2}/{len(test_group)}] {auth['name']:<35}")
        print(f"    Treino: {TRAIN_SIZE} títulos | Caixa Preta: {TEST_SIZE} títulos injetados")
        t0 = time()

        # Gera recomendações com os títulos de teste injetados no corpus
        recs = await generate_recommendations(auth_train, injected_titles=injected, random_baseline=random_baseline)

        # Relevância Graduada: 3=Golden, 2=Topic, 1=Author, 0=Miss
        eval_results    = [
            evaluate_relevance(r['title'], r['authors'], test_titles, auth['name'])
            for r in recs
        ]
        grades          = [ev[0] for ev in eval_results]   # 0, 1, 2 ou 3
        title_scores    = [ev[1] for ev in eval_results]
        match_reasons   = [ev[2] for ev in eval_results]

        # P@K e MRR usam relevância binária (apenas Grau >= 2 é acerto válido)
        # Bronze (Grau 1 = só coautoria) é excluído: seria inflado em qualquer baseline aleatório
        relevance_bin    = [1 if g >= 2 else 0 for g in grades]
        # nDCG usa graus graduados, mas Bronze vale 0 (não contribui para DCG)
        relevance_graded = [g if g >= 2 else 0 for g in grades]

        while len(relevance_bin) < TOP_K:
            relevance_bin.append(0)
            relevance_graded.append(0)

        # Calcula métricas para K = 3, 5 e 10
        for k in [3, 5, 10]:
            metrics_acc[k]["p"].append(precision_at_k(relevance_bin, k))
            metrics_acc[k]["mrr"].append(mrr_at_k(relevance_bin, k))
            metrics_acc[k]["ndcg"].append(ndcg_at_k(relevance_graded, k))

        golden_hits = sum(1 for r in match_reasons if r == "golden_match")
        title_hits  = sum(1 for r in match_reasons if r == "title_match")
        hits        = sum(relevance_bin[:10])
        elapsed     = time() - t0
        print(f"    Hits: {hits}/{len(recs)} (🥇golden={golden_hits} 🥈topic={title_hits}) | P@5={metrics_acc[5]['p'][-1]:.2f} | nDCG@10={metrics_acc[10]['ndcg'][-1]:.2f} | {elapsed:.1f}s")
        print(f"    Sim títulos: {[f'{s:.2f}' for s in title_scores[:5]]}\n")

        detailed_results.append({
            "author":     auth['name'],
            "orcid":      auth['orcid'],
            "train_size": TRAIN_SIZE,
            "test_size":  TEST_SIZE,
            "test_titles": test_titles,
            "recommendations": [
                {
                    "rank":          i + 1,
                    "title":         r['title'],
                    "authors":       r['authors'],
                    "grade":         grades[i],
                    "title_sim":     title_scores[i],
                    "match_reason":  match_reasons[i],
                    "is_relevant":   bool(relevance_bin[i]),
                }
                for i, r in enumerate(recs)
            ],
            "validation": {
                "method":    "title_similarity",
                "threshold": TITLE_SIMILARITY_THRESHOLD,
            },
            "metrics_by_k": {
                f"k{k}": {
                    "precision": metrics_acc[k]["p"][-1],
                    "mrr":       metrics_acc[k]["mrr"][-1],
                    "ndcg":      metrics_acc[k]["ndcg"][-1],
                }
                for k in [3, 5, 10]
            }
        })


    # Salva Análise Detalhada
    DETAILED_FILE = r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados\DETAILED_ANALYSIS.json"
    analysis_payload = {
        "summary": {
            "total_authors":    len(detailed_results),
            "avg_precision_5":  float(np.mean(metrics_acc[5]["p"])),
            "avg_mrr_3":        float(np.mean(metrics_acc[3]["mrr"])),
            "avg_ndcg_3":       float(np.mean(metrics_acc[3]["ndcg"])),
        },
        "results": detailed_results
    }
    with open(DETAILED_FILE, "w", encoding="utf-8") as f:
        json.dump(analysis_payload, f, indent=2, ensure_ascii=False)

    # Atualiza o Log de Experimentos (Histórico Acumulativo)
    LOG_FILE = r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados\experiment_log.json"
    from datetime import datetime

    # Carrega histórico existente ou cria nova lista
    history = []
    if Path(LOG_FILE).exists():
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
                if not isinstance(history, list): history = [history]
        except: history = []

    # Calcula próximo ID sequencial
    next_id = len(history) + 1

    new_entry = {
        "id":                    next_id,
        "experiment_id":         "OFFLINE_HOLDOUT_CV",
        "timestamp":             datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "execution_time_seconds": round(time() - t_start, 1),
        "notes":                 notes,
        "datasets": {
            "author_profiles": "data.json (ORCID)",
            "publication_corpus": Path(DBLP_CSV).name
        },
        "protocol": {
            "type":                    "Hold-Out",
            "n_authors":               N_AUTHORS,
            "train_size":              TRAIN_SIZE,
            "test_size":               TEST_SIZE,
            "validation":              "title_similarity_only (title >= 60% | Bronze excluido das metricas)",
            "title_similarity_threshold": TITLE_SIMILARITY_THRESHOLD,
        },
        "metrics_by_k": {
            f"k{k}": {
                "precision":     round(float(np.mean(metrics_acc[k]["p"])), 4),
                "precision_std": round(float(np.std(metrics_acc[k]["p"])), 4),
                "mrr":           round(float(np.mean(metrics_acc[k]["mrr"])), 4),
                "ndcg":          round(float(np.mean(metrics_acc[k]["ndcg"])), 4),
            }
            for k in [3, 5, 10]
        }
    }

    history.append(new_entry)

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*65}")
    print(f"  📊 RESULTADOS DO EXPERIMENTO OFFLINE (Hold-Out CV)")
    print(f"{'='*65}")
    print(f"  Autores avaliados : {len(detailed_results)}")
    print(f"  Protocolo         : Hold-Out | {TRAIN_SIZE} treino / {TEST_SIZE} teste injetado")
    print(f"  Critério de Acerto : similaridade de título ≥ {int(TITLE_SIMILARITY_THRESHOLD*100)}%")
    print(f"  Análise detalhada : {DETAILED_FILE}")
    print(f"  Log resumo        : {LOG_FILE}")
    print(f"{'='*65}")
    print(f"  {'K':>4} | {'Precision':>14} | {'MRR':>14} | {'nDCG':>14}")
    print(f"  {'-'*55}")
    for k in [3, 5, 10]:
        p_list    = metrics_acc[k]["p"]
        mrr_list  = metrics_acc[k]["mrr"]
        ndcg_list = metrics_acc[k]["ndcg"]
        print(f"  {k:>4} | {np.mean(p_list):>7.4f}±{np.std(p_list):.4f} | {np.mean(mrr_list):>7.4f}±{np.std(mrr_list):.4f} | {np.mean(ndcg_list):>7.4f}±{np.std(ndcg_list):.4f}")
    print(f"{'='*65}\n")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Experimento Offline - Paperman")
    parser.add_argument("--msg", type=str, default="Sem anotações",
                        help="Anotação sobre o que está sendo testado nesta rodada")
    parser.add_argument("--random", action="store_true",
                        help="Usa um baseline aleatório no lugar do Word2Vec")
    args = parser.parse_args()
    asyncio.run(main(notes=args.msg, random_baseline=args.random))
