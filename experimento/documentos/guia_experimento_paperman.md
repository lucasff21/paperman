# 🧠 Guia Completo — Experimento Offline Paperman

> **Versão:** Motor Corrigido (Word2Vec + Normalização de Ano)
> **Script:** `evaluate_online_replica.py`
> **Critério de Acerto:** Coautoria pura (Gold Standard)

---

## PARTE 1 — O Paper Original

### 1.1 Objetivo

Validar quantitativamente o sistema de recomendação Paperman usando dados históricos,
sem interação com usuários reais.

### 1.2 Dados

| Dataset | Descrição |
|---|---|
| DBLP (~5M artigos) | Base de artigos científicos |
| 100 autores ORCID | Pesquisadores com ≥ 20 publicações |

### 1.3 Resultados Originais do Paper

| Métrica | Valor |
|---|---|
| Precision@5 | 0.77 |
| MRR@3 | 0.86 |
| nDCG@3 | 0.92 |

> Critério de acerto original: o autor-alvo é (co)autor do artigo recomendado.

---

## PARTE 2 — Nossa Implementação

### 2.1 Substituições de Infraestrutura

```
API DBLP    →  dblp-v10.csv (1M artigos, local)
API ORCID   →  data.json    (82 autores, pré-coletado)
API Qualis  →  venue_score = 0 (indisponível offline)
Redis/Cache →  sem cache    (re-processa em memória)
Votos user  →  coautoria    (gold standard automático)
```

### 2.2 Dataset

- **`dblp-v10.csv`** — 1 milhão de artigos com campos:
  `title`, `authors`, `year`, `venue`, `n_citation`, `abstract`, `references`
- **`data.json`** — 82 autores com ≥ 20 publicações coletados via ORCID

---

## PARTE 3 — O Ciclo Completo de uma Recomendação

```
1. ORCID → 15 títulos do pesquisador (treino)

2. RAKE → extrai keywords de cada título
   "Machine Learning for Health" → ["machine learning", "health"]

3. Word2Vec (Retrieve) → expande cada keyword
   "learning" → "reasoning"   ← busca também palavras relacionadas

4. Busca no CSV → até 30 artigos por keyword

5. Filtros hard:
   ├── ano: 2012 < year ≤ 2017
   ├── idioma: EN ou PT
   └── sem duplicatas

6. NLTK → limpa título de cada candidato
   tokeniza + remove stopwords + lematiza

7. Word2Vec (Rank) → transforma palavras em vetores de 100 números

8. Cosseno → mede ângulo entre vetores
   resultado em [0, 1]: 1.0 = idêntico | 0.0 = diferente

9. Score composto (normalizado) → decide o vencedor
   (ver Seção 4)

10. Top-10 recomendações → avaliação por coautoria
```

---

## PARTE 4 — O Score Composto (Corrigido)

### 4.1 O Problema Original (Bug)

O sistema online tentava calcular:
```
score = year + venue_score + title_similarity
```

Mas havia dois problemas:

**Bug 1 — Word2Vec recebia uma frase inteira:**
```python
# ERRADO (online — bug):
cosine(model["machine learning for health"], model["neural"])
#             ↑ frase completa → KeyError → title_similarity = 0

# CORRETO (nossa versão):
cosine(model["machine"], model["neural"])   ← palavra a palavra
cosine(model["learning"], model["neural"])
cosine(model["health"], model["neural"])
mean_cosine = média de todas as comparações
```

**Bug 2 — Escalas incompatíveis:**
```
year = 2017         (escala: 2013–2017)
similarity = 0.9    (escala: 0.0–1.0)

score = 2017 + 0.9 = 2017.9   ← paper de 2017 com sim=0.1 (score=2017.1) PERDE
para paper mais relevante de 2016 com sim=0.9 (score=2016.9)!
```

### 4.2 O Score Corrigido

**Passo 1 — Normalizar o ano para [0, 1]:**
```
YEAR_MIN = 2013   YEAR_MAX = 2017   range = 4

ano 2013 → (2013-2013)/4 = 0.00
ano 2014 → (2014-2013)/4 = 0.25
ano 2015 → (2015-2013)/4 = 0.50
ano 2016 → (2016-2013)/4 = 0.75
ano 2017 → (2017-2013)/4 = 1.00
```

**Passo 2 — Calcular similaridade semântica real:**
```
subject_words = ["machine", "learning", "health"]   ← título do treino
cand_words    = ["neural", "network", "medicine"]   ← título candidato

cosine("machine", "neural")   = 0.61
cosine("machine", "network")  = 0.45
cosine("machine", "medicine") = 0.38
cosine("learning", "neural")  = 0.72
cosine("learning", "network") = 0.58
... (9 pares no total)

mean_cosine = soma / 9 = 0.55
```

**Passo 3 — Score composto ponderado:**
```
score = 0.4 × recency + 0.6 × mean_cosine

Exemplo A: ano=2017 (recency=1.0), sim=0.1
  score = 0.4 × 1.0 + 0.6 × 0.1 = 0.40 + 0.06 = 0.46

Exemplo B: ano=2016 (recency=0.75), sim=0.9
  score = 0.4 × 0.75 + 0.6 × 0.9 = 0.30 + 0.54 = 0.84 ← VENCE ✅

→ O paper mais relevante agora ganha do mais recente
```

---

## PARTE 5 — Critério de Acerto (Gold Standard)

Uma recomendação é um **acerto** se e somente se o autor-alvo constar
como (co)autor do artigo recomendado no DBLP.

Verificação via **Fuzzy Matching** (threshold ≥ 85%):
```
Autor-alvo:   "João Silva"
Paper autores: ["J. Silva", "Maria Costa"]
  → token_sort_ratio("joão silva", "j. silva") = 91% ≥ 85% → ACERTO ✅
```

**Por que coautoria?**
- Critério binário e indiscutível
- Não depende de julgamento subjetivo
- Alinhado ao protocolo do paper original
- A similaridade de título era usada antes, mas criava falsos positivos

---

## PARTE 6 — Protocolo Hold-Out

```
all_titles = ["Paper A", ..., "Paper T"]  (20 títulos do autor)
                │
                ├── train: [0..14]  → sistema VÊ (15 títulos)
                └── test:  [15..19] → sistema NÃO VÊ (5 gabarito)

Os 5 gabarito são injetados com ano=2016 e
authors=[nome do autor] no pool de candidatos.
→ Garante que o acerto é matematicamente possível.
```

---

## PARTE 7 — Métricas

| Métrica | O que mede | Sensível à posição? |
|---|---|---|
| **Precision@K** | Fração de acertos no Top-K | ❌ Não |
| **MRR@K** | Posição do 1º acerto | ✅ Sim |
| **nDCG@K** | Qualidade do ranking completo | ✅ Sim (penaliza acertos tardios) |

Avaliamos para **K = 3, 5 e 10**.

---

## PARTE 8 — Roadmap de Melhorias

```
✅ 1. Critério de acerto → coautoria pura
✅ 2. Réplica fiel do online → diagnóstico dos bugs
✅ 3. Corrigir bug Word2Vec → similaridade semântica real
✅ 4. Normalizar ano → score composto equilibrado [0,1]
⏳ 5. Re-ranking por citações/ano → impacto científico (Opção C)
⏳ 6. Definir pesos α, β via ablation study
```

**Score futuro com citações (Opção C — Two-Stage Ranking):**
```
Stage 1: score = 0.4 × recency + 0.6 × semantic    → Top-15
Stage 2: re-rank por log(n_citation / age + 1)      → Top-10 final
```

---

## PARTE 9 — Como Rodar

```bash
cd "C:\Users\Lucas\Documents\Paperman\paperman_back\paperman"

# Paperman (corrigido)
python evaluate_online_replica.py --n 10
python evaluate_online_replica.py --n 20
python evaluate_online_replica.py --n 82

# Baseline aleatório
python evaluate_online_replica.py --n 10 --random
python evaluate_online_replica.py --n 82 --random
```

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `--n` | 10 | Número de autores |
| `--train` | 15 | Títulos de treino |
| `--test` | 5 | Títulos gabarito |
| `--random` | False | Baseline aleatório |

**Saída gerada:**
```
resultados/experiment_online_replica_N{n}.json
resultados/experiment_random_N{n}.json
```
