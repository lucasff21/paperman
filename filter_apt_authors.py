#!/usr/bin/env python3
"""
filter_apt_authors.py — Filtra autores aptos pro experimento
=============================================================

Lê o data_enriched.json e gera um novo arquivo data_apt.json contendo apenas
autores que atendem os critérios de elegibilidade:

  1. Pelo menos 20 títulos únicos (após deduplicação) — necessário pra 15 treino
     + 5 teste;
  2. Pelo menos N test_titles (posições 16-20) com _enriched preenchido
     (citação do Semantic Scholar via DOI). Threshold via --min-enriched.

Preserva toda a estrutura original do ORCID (inclusive o _enriched nos
work-summaries) — só remove autores não-aptos do array externo.

USO:
  python filter_apt_authors.py                        # threshold 3 (default)
  python filter_apt_authors.py --min-enriched 4       # stricter
  python filter_apt_authors.py --min-enriched 5       # só autores perfeitos
"""

import json
import argparse
from pathlib import Path

# ─── CONFIG ───────────────────────────────────────────────────────────────────
DATA_ENRICHED = r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados\data_enriched.json"
DATA_APT      = r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados\data_apt.json"

TRAIN_SIZE = 15
TEST_SIZE  = 5

parser = argparse.ArgumentParser()
parser.add_argument("--min-enriched", type=int, default=3,
                    help="Mínimo de test_titles enriquecidos para autor ser apto (default: 3)")
args = parser.parse_args()
MIN_ENRICHED = args.min_enriched


# ─── FUNÇÕES ─────────────────────────────────────────────────────────────────
def extract_name(author: dict) -> str:
    """Extrai nome completo do autor ORCID."""
    person = author.get("person", {})
    name_obj = person.get("name", {})
    given  = (name_obj.get("given-names")  or {}).get("value", "")
    family = (name_obj.get("family-name") or {}).get("value", "")
    return f"{given} {family}".strip() or author.get("path", "unknown")


def extract_titles_with_enriched(author: dict) -> list:
    """Retorna [{title, enriched}] preservando ordem ORCID."""
    acts  = author.get("activities-summary", {})
    works = acts.get("works", {}).get("group", [])
    items = []
    for group in works:
        for ws in group.get("work-summary", []) or []:
            t = (ws.get("title", {}) or {}).get("title", {}) or {}
            val = t.get("value", "") if isinstance(t, dict) else ""
            if val:
                items.append({
                    "title":    val,
                    "enriched": ws.get("_enriched"),
                })
    return items


def is_apt(author: dict, min_enriched: int) -> tuple:
    """
    Retorna (apt: bool, reason: str, n_unique: int, n_enriched_in_test: int).
    """
    items = extract_titles_with_enriched(author)

    # Dedup
    seen = set()
    unique = []
    for item in items:
        norm = item["title"].lower().strip()
        if norm and norm not in seen:
            seen.add(norm)
            unique.append(item)

    n_unique = len(unique)
    if n_unique < TRAIN_SIZE + TEST_SIZE:
        return False, f"só {n_unique} títulos únicos (< {TRAIN_SIZE + TEST_SIZE})", n_unique, 0

    test_items = unique[TRAIN_SIZE:TRAIN_SIZE + TEST_SIZE]
    n_enriched_in_test = sum(1 for it in test_items if it["enriched"])

    if n_enriched_in_test < min_enriched:
        return False, f"só {n_enriched_in_test}/{TEST_SIZE} enriquecidos (< {min_enriched})", n_unique, n_enriched_in_test

    return True, f"{n_enriched_in_test}/{TEST_SIZE} enriquecidos", n_unique, n_enriched_in_test


# ─── PIPELINE ─────────────────────────────────────────────────────────────────
print(f"[1/3] Carregando {DATA_ENRICHED}...")
with open(DATA_ENRICHED, encoding="utf-8") as f:
    data = json.load(f)
print(f"      {len(data)} autores no arquivo original")

print(f"\n[2/3] Filtrando autores aptos (threshold: {MIN_ENRICHED}/{TEST_SIZE} enriquecidos)...")
print()

apt_authors = []
rejected = []

for idx, author in enumerate(data, 1):
    name = extract_name(author)
    apt, reason, n_unique, n_enr = is_apt(author, MIN_ENRICHED)

    if apt:
        apt_authors.append(author)
        status = "APTO"
    else:
        rejected.append({"name": name, "reason": reason, "n_unique": n_unique, "n_enr": n_enr})
        status = "REJ "

    marker = "[+]" if apt else "[-]"
    print(f"  {marker} {idx:>3} | {name[:35]:<35} | {status} | {reason}")

print()
print("=" * 75)
print(f"  RESUMO")
print("=" * 75)
print(f"  Total inicial:     {len(data)}")
print(f"  APTOS:             {len(apt_authors)}  ({100*len(apt_authors)/len(data):.1f}%)")
print(f"  Rejeitados:        {len(rejected)}  ({100*len(rejected)/len(data):.1f}%)")
print()

# Breakdown dos rejeitados
few_unique   = [r for r in rejected if "títulos únicos" in r["reason"]]
few_enriched = [r for r in rejected if "enriquecidos" in r["reason"]]
print(f"  Motivos de rejeição:")
print(f"    - Poucos títulos únicos:  {len(few_unique)}")
print(f"    - Poucos enriquecidos:    {len(few_enriched)}")
print()

# ─── SAÍDA ────────────────────────────────────────────────────────────────────
print(f"[3/3] Gravando {DATA_APT}...")
with open(DATA_APT, "w", encoding="utf-8") as f:
    json.dump(apt_authors, f, ensure_ascii=False, indent=2)

size_mb = Path(DATA_APT).stat().st_size / (1024*1024)
print(f"      Salvo: {len(apt_authors)} autores, {size_mb:.1f} MB")
print()
print("Próximo passo:")
print(f"  Modificar evaluate_online_replica.py pra ler data_apt.json")
print(f"  e reintroduzir a injeção dos 5 gold enriquecidos.")
