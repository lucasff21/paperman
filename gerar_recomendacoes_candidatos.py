#!/usr/bin/env python3
"""
gerar_recomendacoes_candidatos.py — Geração de Recomendações para Avaliação Humana
====================================================================================
Utiliza EXATAMENTE o mesmo pipeline de busca e scoring do evaluate_online_replica.py:
  - "Tiro no Escuro" (amostragem aleatória no DBLP-v10.csv)
  - Filtro temporal (YEAR_WINDOW) e de idioma (PT/EN)
  - Scoring V5.3: Sem + Rec + Cit + (Qua × Sem)

O que foi REMOVIDO em relação ao evaluate_online_replica.py:
  - Fase de Injeção do Gabarito (gold papers) — não há hold-out
  - Avaliação automática (coautoria, author_cited, cited_author)
  - Cálculo de métricas (Precision, MRR, nDCG)
  - Wilcoxon test e experiment_log.json

Quem avalia as recomendações são os próprios usuários do experimento.

ENTRADA:
  candidatos_reais.json — lista de candidatos, cada um com 1 título de publicação.
  Estrutura idêntica ao data_apt.json (formato ORCID + _enriched), mas com n=1 título.

SAÍDA:
  recomendacoes_candidatos.json — para cada candidato, 10 recomendações com scores.

USO:
  python gerar_recomendacoes_candidatos.py
  python gerar_recomendacoes_candidatos.py --qualis-mode all_modulated
  python gerar_recomendacoes_candidatos.py --random   (baseline aleatório)
"""

import sys
import os
import re
import json
import random
import argparse
from typing import List, Dict

import pandas as pd

# ─── Reusa toda a infraestrutura do evaluate_online_replica ──────────────────
# Importamos funções e constantes diretamente para garantir paridade total.
from evaluate_online_replica import (
    load_model,
    load_csv,
    clean_publication_title,
    is_valid_language,
    extract_best_match_online,
    YEAR_CUTOFF,
    YEAR_WINDOW,
    YEAR_MIN,
    TOP_K_EVAL,
    LOG_DIR,
    DATA_JSON as DEFAULT_DATA_JSON,
)
from multi_rake import Rake

CANDIDATES_PER_TOPIC = 100

def build_search_query(subject: str) -> List[str]:
    subject = re.sub(r'[^\x00-\x7f]', r'', subject)
    rake = Rake()
    keywords = rake.apply(subject)
    return [item[0] for item in keywords]

def search_by_topic(query: str, df: pd.DataFrame) -> List[Dict]:
    q = query.lower().strip()
    hits = df[df['title_norm'].str.contains(q, na=False, regex=False)].head(CANDIDATES_PER_TOPIC)
    result = []
    for _, row in hits.iterrows():
        raw = str(row.get('authors', '[]'))
        names = [a.strip().strip("'\"") for a in re.sub(r"[\[\]]", "", raw).split(",") if a.strip()]
        abstract_raw = str(row.get('abstract', '') or '')
        result.append({
            "title":          str(row['title']),
            "year":           int(row['year']),
            "venue":          str(row['venue']),
            "authors":        names,
            "id":             str(row['id']),
            "n_citation":     int(row.get('n_citation', 0) or 0),
            "references_raw": str(row.get('references', '[]') or '[]'),
            "abstract":       abstract_raw[:500] if abstract_raw != 'nan' else "",
        })
    return result

# ─── ARQUIVO DE ENTRADA/SAÍDA ────────────────────────────────────────────────
DATA_JSON   = r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados\candidatos_reais.json"
BASE_DIR    = r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados"


# ─── EXTRAÇÃO DO PERFIL DO CANDIDATO ─────────────────────────────────────────
def extract_author_data(a: dict) -> dict:
    """
    Idêntica ao extract_author_data() interno do evaluate_online_replica.run().
    Normaliza o formato ORCID para o formato interno: {author, titles_with_meta}.
    """
    person = a.get("person", {})
    name_obj = person.get("name", {})
    given  = (name_obj.get("given-names")  or {}).get("value", "")
    family = (name_obj.get("family-name") or {}).get("value", "")
    full_name = f"{given} {family}".strip() or a.get("path", "unknown")

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
                    "enriched": ws.get("_enriched"),
                })
    return {"author": full_name, "titles_with_meta": titles_with_meta}


# ─── PIPELINE PRINCIPAL ───────────────────────────────────────────────────────
def run(qualis_mode: str = "modulated", random_mode: bool = False) -> None:
    label = "ALEATÓRIO (baseline)" if random_mode else f"SCORING V5.3 [{qualis_mode}]"

    print()
    print("=" * 70)
    print("  GERADOR DE RECOMENDAÇÕES — AVALIAÇÃO HUMANA")
    print("=" * 70)
    print(f"  Pipeline      : Idêntico ao evaluate_online_replica.py")
    print(f"  Scoring       : {label}")
    print(f"  DBLP sampling : RAKE + String Matching ({CANDIDATES_PER_TOPIC} papers por keyword)")
    print(f"  Janela anos   : {YEAR_MIN}–{YEAR_CUTOFF}")
    print(f"  Recomendações : Top-{TOP_K_EVAL} por candidato")
    print(f"  Avaliação     : HUMANA (sem métrica automática)")
    output_filename = f"recomendacoes_{'random' if random_mode else qualis_mode}.json"
    output_json = os.path.join(BASE_DIR, output_filename)

    print(f"  Entrada       : {DATA_JSON}")
    print(f"  Saída         : {output_json}")
    print("=" * 70)
    print()

    # ── Carregamento ────────────────────────────────────────────────────────
    model = load_model()
    df    = load_csv()
    print()

    with open(DATA_JSON, encoding="utf-8") as f:
        raw_authors = json.load(f)

    all_authors = [extract_author_data(a) for a in raw_authors]
    # Candidatos com ao menos 1 título
    eligible = [a for a in all_authors if len(a["titles_with_meta"]) >= 1]
    print(f"[OK] {len(eligible)} candidatos carregados\n")

    results = []

    for idx, author_data in enumerate(eligible):
        author_name = author_data["author"]
        # Usa o PRIMEIRO título como "perfil" do candidato (subject)
        subject = author_data["titles_with_meta"][0]["title"]

        print(f"  [{idx+1:02d}] {author_name}")
        print(f"       Título base: {subject[:80]}")

        # ══════════════════════════════════════════════════════════════════════
        # FASE 1 — RETRIEVAL: RAKE + String Matching no DBLP
        # ══════════════════════════════════════════════════════════════════════
        recommendations = []
        seen_titles     = {subject.lower().strip()}

        keywords = build_search_query(subject)
        if not keywords:
            keywords = [subject]

        candidates_pool: Dict[str, Dict] = {}
        for kw in keywords:
            hits = search_by_topic(kw, df)
            for pub in hits:
                candidates_pool[pub["title"]] = pub

        # ══════════════════════════════════════════════════════════════════════
        # FASE 2 — FILTRAGEM: Temporal + Idioma
        # ══════════════════════════════════════════════════════════════════════
        filtered = [
            c for c in candidates_pool.values()
            if c["title"].lower().strip() not in seen_titles
            and (YEAR_CUTOFF - YEAR_WINDOW < c["year"] <= YEAR_CUTOFF)
            and is_valid_language(c["title"])
        ]

        # ══════════════════════════════════════════════════════════════════════
        # FASE 3 — SCORING: Ranqueia o pool todo de uma vez e pega o Top-10
        # ══════════════════════════════════════════════════════════════════════
        if filtered:
            if random_mode:
                random.shuffle(filtered)
                for best_candidate in filtered:
                    title_norm = best_candidate["title"].lower().strip()
                    if title_norm not in seen_titles:
                        recommendations.append(best_candidate)
                        seen_titles.add(title_norm)
                        if len(recommendations) >= TOP_K_EVAL:
                            break
            else:
                ranked = extract_best_match_online(
                    candidates=filtered,
                    subject=subject,
                    model=model,
                    qualis_mode=qualis_mode
                )
                for best_scored in ranked:
                    best_candidate = best_scored[6]
                    title_norm = best_candidate["title"].lower().strip()
                    if title_norm not in seen_titles:
                        best_candidate["_scores"] = {
                            "score_total": round(best_scored[0], 4),
                            "score_sem":   round(best_scored[1], 4),
                            "score_rec":   round(best_scored[2], 4),
                            "score_cit":   round(best_scored[3], 4),
                            "qua_term":    round(best_scored[4], 4),
                            "qua_raw":     round(best_scored[5], 4),
                        }
                        recommendations.append(best_candidate)
                        seen_titles.add(title_norm)
                        if len(recommendations) >= TOP_K_EVAL:
                            break

        # Fallback: Se o RAKE + String Matching não rendeu 10 recomendações, preenche o resto com Tiro no Escuro
        attempts = 0
        while len(recommendations) < TOP_K_EVAL and attempts < TOP_K_EVAL * 3:
            attempts += 1

            random_sample = df.sample(n=CANDIDATES_PER_TOPIC)
            fallback_candidates: Dict[str, Dict] = {}

            for _, row in random_sample.iterrows():
                raw = str(row.get('authors', '[]'))
                names = [a.strip().strip("'\"") for a in re.sub(r"[\[\]]", "", raw).split(",") if a.strip()]
                abstract_raw = str(row.get('abstract', '') or '')
                pub = {
                    "title":          str(row['title']),
                    "year":           int(row['year']),
                    "venue":          str(row['venue']),
                    "authors":        names,
                    "id":             str(row['id']),
                    "n_citation":     int(row.get('n_citation', 0) or 0),
                    "references_raw": str(row.get('references', '[]') or '[]'),
                    "abstract":       abstract_raw[:500] if abstract_raw != 'nan' else "",
                }
                fallback_candidates[pub["title"]] = pub

            fallback_filtered = [
                c for c in fallback_candidates.values()
                if c["title"].lower().strip() not in seen_titles
                and (YEAR_CUTOFF - YEAR_WINDOW < c["year"] <= YEAR_CUTOFF)
                and is_valid_language(c["title"])
            ]

            if not fallback_filtered:
                continue

            if random_mode:
                best_candidate = random.choice(fallback_filtered)
                best_scored    = None
            else:
                ranked = extract_best_match_online(
                    candidates=fallback_filtered,
                    subject=subject,
                    model=model,
                    qualis_mode=qualis_mode
                )
                if not ranked:
                    continue
                best_scored    = ranked[0]
                best_candidate = best_scored[6]

            title_norm = best_candidate["title"].lower().strip()
            if title_norm not in seen_titles:
                if best_scored:
                    best_candidate["_scores"] = {
                        "score_total": round(best_scored[0], 4),
                        "score_sem":   round(best_scored[1], 4),
                        "score_rec":   round(best_scored[2], 4),
                        "score_cit":   round(best_scored[3], 4),
                        "qua_term":    round(best_scored[4], 4),
                        "qua_raw":     round(best_scored[5], 4),
                    }
                recommendations.append(best_candidate)
                seen_titles.add(title_norm)

        print(f"       Recomendações geradas: {len(recommendations)}/10")

        # Ordena por score_total decrescente antes de atribuir ranks finais
        recommendations.sort(
            key=lambda r: r.get("_scores", {}).get("score_total", 0.0),
            reverse=True
        )

        results.append({
            "author":          author_name,
            "base_title":      subject,
            "qualis_mode":     qualis_mode if not random_mode else "random_baseline",
            "recommendations": [
                {
                    "rank":        i + 1,
                    "title":       r["title"],
                    "year":        r["year"],
                    "venue":       r.get("venue", ""),
                    "authors":     r.get("authors", []),
                    "n_citation":  r.get("n_citation", 0),
                    "abstract":    r.get("abstract", ""),
                    "scores":      r.get("_scores", {}),
                    # Campo para preenchimento pelo usuário na avaliação:
                    "avaliacao_usuario": None,
                    "comentario":        None,
                }
                for i, r in enumerate(recommendations)
            ]
        })

    # ── Salva saída ──────────────────────────────────────────────────────────
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 70)
    print(f"  CONCLUÍDO | {len(results)} candidatos processados")
    print(f"  Arquivo salvo: {output_json}")
    print("=" * 70)


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gera recomendações para avaliação humana (pipeline idêntico ao evaluate_online_replica.py)"
    )
    parser.add_argument(
        "--qualis-mode",
        choices=["sem_only", "off", "additive", "modulated", "cit_modulated", "all_modulated", "multiplicative"],
        default="modulated",
        help="Modo de scoring (padrão: modulated)"
    )
    parser.add_argument(
        "--random",
        action="store_true",
        help="Baseline: recomendação aleatória (sem scoring)"
    )
    args = parser.parse_args()

    run(
        qualis_mode = args.qualis_mode,
        random_mode = args.random,
    )
