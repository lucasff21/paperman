#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

"""
gerar_recomendacoes_online.py — Pipeline Online para Avaliação A/B
===================================================================
Substitui a busca local no DBLP-v10.csv por chamadas à API do OpenAlex.
Para cada candidato:
  1. Busca o perfil ORCID (títulos reais de publicações)
  2. Extrai keywords/bigramas dos títulos
  3. Pesquisa na OpenAlex API por papers da área
  4. Filtra por ano e idioma
  5. Pontua com Word2Vec + Qualis (extract_best_match_online)
  6. Salva Top-10 no formato recomendacoes_ab.json

USO:
  python gerar_recomendacoes_online.py --qualis-mode sem_only
  python gerar_recomendacoes_online.py --qualis-mode multiplicative
"""

import sys
import re
import os
import json
import time
import argparse
import urllib.request
import urllib.parse
from typing import List, Dict, Optional

# ─── Reusa o motor de scoring do sistema existente ────────────────────────────
from evaluate_online_replica import (
    load_model,
    is_valid_language,
    extract_best_match_online,
    YEAR_CUTOFF,
    YEAR_WINDOW,
    YEAR_MIN,
    TOP_K_EVAL,
)

# ─── Configuração ─────────────────────────────────────────────────────────────
CANDIDATES = [
    {
        "name": "Frederico Araújo Durão",
        "orcid": "0000-0002-7766-6666",
    },
    {
        "name": "Lucas França Freitas",
        "orcid": "0009-0006-1512-2803",
        "fallback_titles": [
            "Paperman: A Scientific Paper Recommendation System"
        ],
    },
]

OUTPUT_BASE = r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados"
PAPERS_PER_QUERY = 50      # papers buscados por keyword na OpenAlex
MAX_QUERIES = 10           # máximo de queries (só bigramas — mais específicos)
MIN_SEM_THRESHOLD = 0.15   # filtra papers semanticamente distantes antes do scoring
SLEEP_BETWEEN_QUERIES = 1.0  # segundos entre chamadas (respeita rate limit)

# Stopwords para construção de bigramas
STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "in", "on", "at", "to", "for",
    "with", "by", "from", "into", "using", "based", "via", "is", "are",
    "be", "as", "it", "its", "this", "that", "these", "those", "can",
    "has", "have", "not", "no", "new", "um", "uma", "de", "do", "da",
    "para", "com", "em", "e", "o", "os", "as", "na", "no", "se"
}


# ─── 1. ORCID: Busca perfil completo ─────────────────────────────────────────
def fetch_orcid_titles(orcid_id: str) -> List[str]:
    """Retorna todos os títulos de publicação do perfil ORCID."""
    url = f"https://pub.orcid.org/v3.0/{orcid_id}/record"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
    except Exception as e:
        print(f"  [WARN] ORCID fetch falhou ({orcid_id}): {e}")
        return []

    works = data.get("activities-summary", {}).get("works", {}).get("group", [])
    titles = []
    for group in works:
        for ws in group.get("work-summary", []):
            t = (ws.get("title") or {}).get("title") or {}
            v = t.get("value", "") if isinstance(t, dict) else ""
            if v:
                titles.append(v)
    return titles


# ─── 2. Extração de keywords (SOMENTE bigramas) ──────────────────────────────
def extract_keywords(titles: List[str]) -> List[str]:
    """
    Extrai APENAS bigramas dos títulos do candidato.

    Motivo: unigramas genéricos como 'system', 'data', 'scientific' contaminam
    o pool com papers de medicina/biologia com 10.000+ citações que dominam o
    modelo multiplicativo, apesar de serem semanticamente irrelevantes.
    Bigramas são específicos o suficiente para retornar apenas papers da área.

    Ex (Fred): 'recommender system', 'linked data', 'online social'
    Ex (Lucas): 'scientific paper', 'paper recommendation', 'recommendation system'
    """
    bigram_freq: Dict[str, int] = {}

    for title in titles:
        clean = re.sub(r"[^a-zA-Z0-9 ]", " ", title).lower()
        words = [w for w in clean.split() if len(w) > 2 and w not in STOPWORDS]

        for i in range(len(words) - 1):
            bg = f"{words[i]} {words[i+1]}"
            bigram_freq[bg] = bigram_freq.get(bg, 0) + 1

    sorted_bigrams = sorted(bigram_freq.items(), key=lambda x: -x[1])

    keywords = []
    seen = set()
    for bg, freq in sorted_bigrams:
        if bg not in seen:
            keywords.append(bg)
            seen.add(bg)
        if len(keywords) >= MAX_QUERIES:
            break

    return keywords[:MAX_QUERIES]


# ─── 3. OpenAlex: Busca por keywords ─────────────────────────────────────────
def search_openalex(query: str, year_min: int, year_max: int) -> List[Dict]:
    """Busca papers na OpenAlex API e normaliza para o formato do pipeline."""
    params = urllib.parse.urlencode({
        "search": query,
        "filter": f"publication_year:{year_min}-{year_max},language:en",
        "select": "title,publication_year,primary_location,cited_by_count,authorships,abstract_inverted_index",
        "per_page": PAPERS_PER_QUERY,
        "mailto": "paperman@experiment.com",
    })
    url = f"https://api.openalex.org/works?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "Paperman/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = json.loads(r.read())
    except Exception as e:
        print(f"  [WARN] OpenAlex query '{query}' falhou: {e}")
        return []

    papers = []
    for p in raw.get("results", []):
        title = p.get("title") or ""
        if not title:
            continue

        year = p.get("publication_year") or 0

        # Venue
        loc = p.get("primary_location") or {}
        source = loc.get("source") or {}
        venue = source.get("display_name", "") if isinstance(source, dict) else ""

        # Authors
        authors = []
        for auth_obj in (p.get("authorships") or [])[:5]:
            name = (auth_obj.get("author") or {}).get("display_name", "")
            if name:
                authors.append(name)

        # Citations
        n_citation = p.get("cited_by_count", 0) or 0

        # Abstract (formato índice invertido → texto)
        inv = p.get("abstract_inverted_index") or {}
        abstract = ""
        if inv:
            pos_word = {}
            for word, positions in inv.items():
                for pos in positions:
                    pos_word[pos] = word
            abstract = " ".join(pos_word[i] for i in sorted(pos_word))[:500]

        papers.append({
            "title": title,
            "year": int(year),
            "venue": venue,
            "authors": authors,
            "id": title[:50],  # OpenAlex não tem id compatível com DBLP
            "n_citation": int(n_citation),
            "references_raw": "[]",
            "abstract": abstract,
        })

    return papers


# ─── 4. Pipeline principal ────────────────────────────────────────────────────
def run(qualis_mode: str = "sem_only") -> None:
    print()
    print("=" * 70)
    print("  GERADOR DE RECOMENDAÇÕES ONLINE — AVALIAÇÃO A/B")
    print("=" * 70)
    print(f"  Motor de busca   : OpenAlex API (online, sem CSV local)")
    print(f"  Perfil candidato : ORCID API")
    print(f"  Scoring          : {qualis_mode}")
    print(f"  Janela temporal  : {YEAR_MIN}–{YEAR_CUTOFF}")
    print(f"  Top-K            : {TOP_K_EVAL}")
    print("=" * 70)
    print()

    model = load_model()
    results = []

    for cand in CANDIDATES:
        name = cand["name"]
        orcid = cand["orcid"]
        print(f"\n{'─'*60}")
        print(f"  Candidato: {name}")
        print(f"  ORCID:     {orcid}")

        # 1. Busca títulos no ORCID
        titles = fetch_orcid_titles(orcid)
        print(f"  Títulos ORCID encontrados: {len(titles)}")

        # Fallback para candidatos sem publicações no ORCID
        if not titles:
            fallback = cand.get("fallback_titles", [])
            if fallback:
                titles = fallback
                print(f"  [FALLBACK] Usando títulos manuais: {titles}")
            else:
                print(f"  [SKIP] Sem títulos disponíveis.")
                continue

        for t in titles[:5]:
            print(f"    - {t[:75]}")
        if len(titles) > 5:
            print(f"    ... e mais {len(titles)-5}")

        # 2. Extrai keywords
        keywords = extract_keywords(titles)
        print(f"\n  Keywords extraídas ({len(keywords)}):")
        for kw in keywords:
            print(f"    \"{kw}\"")

        # 3. Busca na OpenAlex
        candidates_pool: Dict[str, Dict] = {}
        for i, kw in enumerate(keywords):
            print(f"  [{i+1}/{len(keywords)}] OpenAlex: '{kw}'...", end=" ", flush=True)
            hits = search_openalex(kw, YEAR_MIN, YEAR_CUTOFF)
            new = 0
            for pub in hits:
                key = pub["title"].lower().strip()
                if key not in candidates_pool:
                    candidates_pool[key] = pub
                    new += 1
            print(f"+{new} novos (total: {len(candidates_pool)})")
            time.sleep(SLEEP_BETWEEN_QUERIES)

        # 4. Filtra por idioma e por semântica mínima
        # O pré-filtro semântico (MIN_SEM_THRESHOLD) descarta papers claramente
        # off-topic antes do scoring, evitando que papers de medicina/biologia
        # com muitas citações dominem o modelo multiplicativo.
        from evaluate_online_replica import load_model as _lm, clean_publication_title, cosine_similarity
        subject_words = clean_publication_title(titles[0])

        seen_titles = {t.lower().strip() for t in titles}
        pre_filtered = [
            c for c in candidates_pool.values()
            if c["title"].lower().strip() not in seen_titles
            and is_valid_language(c["title"])
        ]

        # Calcula semântica mínima para pré-filtro
        filtered = []
        for c in pre_filtered:
            cand_words = clean_publication_title(c["title"])
            sim_total, n_pairs = 0.0, 0
            for sw in subject_words:
                for cw in cand_words:
                    try:
                        sim_total += cosine_similarity(model[sw], model[cw])
                        n_pairs += 1
                    except KeyError:
                        pass
            mean_sim = sim_total / n_pairs if n_pairs > 0 else 0.0
            if mean_sim >= MIN_SEM_THRESHOLD:
                filtered.append(c)

        print(f"\n  Pool bruto: {len(pre_filtered)} | Após pré-filtro semântico (>={MIN_SEM_THRESHOLD}): {len(filtered)} papers")

        # 5. Scoring
        ranked = extract_best_match_online(
            candidates=filtered,
            subject=titles[0],  # Usa o 1º título como âncora semântica
            model=model,
            qualis_mode=qualis_mode,
        )

        # 6. Monta Top-10
        recommendations = []
        seen_final = set(seen_titles)
        for scored in ranked:
            candidate = scored[6]
            title_norm = candidate["title"].lower().strip()
            if title_norm not in seen_final:
                candidate["_scores"] = {
                    "score_total": round(scored[0], 4),
                    "score_sem":   round(scored[1], 4),
                    "score_rec":   round(scored[2], 4),
                    "score_cit":   round(scored[3], 4),
                    "qua_term":    round(scored[4], 4),
                    "qua_raw":     round(scored[5], 4),
                }
                recommendations.append(candidate)
                seen_final.add(title_norm)
                if len(recommendations) >= TOP_K_EVAL:
                    break

        print(f"  Top-{len(recommendations)} gerado:")
        for i, rec in enumerate(recommendations, 1):
            sc = rec.get("_scores", {})
            print(f"    {i:2}. [{rec['year']}] {rec['title'][:65]}")
            print(f"        total={sc.get('score_total',0):.3f} sem={sc.get('score_sem',0):.3f} cit={sc.get('score_cit',0):.3f}")

        results.append({
            "author": name,
            "orcid": orcid,
            "base_title": titles[0],
            "n_orcid_titles": len(titles),
            "keywords_used": keywords,
            "recommendations": [
                {
                    "rank": i + 1,
                    "title": rec["title"],
                    "year": rec["year"],
                    "venue": rec["venue"],
                    "authors": rec["authors"],
                    "n_citation": rec["n_citation"],
                    "abstract": rec.get("abstract", ""),
                    "scores": rec.get("_scores", {}),
                    "avaliacao_usuario": None,
                    "comentario": None,
                }
                for i, rec in enumerate(recommendations)
            ],
        })

    # 7. Salva
    output_path = os.path.join(OUTPUT_BASE, f"recomendacoes_online_{qualis_mode}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*70}")
    print(f"  Salvo em: {output_path}")
    print(f"  {len(results)} candidatos processados")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualis-mode", default="sem_only",
                        choices=["sem_only", "multiplicative", "modulated"])
    args = parser.parse_args()
    run(qualis_mode=args.qualis_mode)
