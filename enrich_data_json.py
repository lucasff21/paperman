#!/usr/bin/env python3
"""
enrich_data_json.py — Enriquece data.json (ORCID) com citações via Semantic Scholar
====================================================================================

Para cada work-summary do ORCID que possui DOI, consulta a Semantic Scholar API
e anexa metadados ausentes:
  - citationCount  (contagem de citações)
  - venue          (nome do veículo de publicação)
  - year           (ano confirmado)
  - references     (lista de paper IDs citados)
  - externalIds    (DOI, MAG, ArXiv, etc.)

Resultado é salvo como anotação `_enriched` dentro de cada work-summary,
preservando a estrutura original. Saída em `data_enriched.json`.

Cache local em `ss_cache.json` evita re-consultas em execuções subsequentes.

USO:
  python enrich_data_json.py
  python enrich_data_json.py --api-key SUA_CHAVE   # opcional, aumenta limite
  python enrich_data_json.py --max-authors 5       # teste com poucos autores

API key gratuita (recomendado): https://www.semanticscholar.org/product/api
Sem key: ~1 req/s rate limit oficial. Com key: 1000 req/s.
"""

import json
import time
import argparse
from pathlib import Path
from typing import Dict, Optional

import requests

# ─── CONFIG ───────────────────────────────────────────────────────────────────
DATA_JSON_IN  = r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados\data.json"
DATA_JSON_OUT = r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados\data_enriched.json"
CACHE_FILE    = r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados\ss_cache.json"

SS_API = "https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
SS_FIELDS = "citationCount,venue,year,references.paperId,externalIds"

REQUEST_TIMEOUT  = 15      # segundos por request
SLEEP_BASE       = 1.1     # base entre requests sem API key (~1 req/s)
SLEEP_WITH_KEY   = 0.05    # com key (~20 req/s, conservador)
RETRY_MAX        = 3       # tentativas em caso de 429/erro de rede
RETRY_BACKOFF    = 5       # segundos entre retries (cresce exponencialmente)


# ─── ARGS ─────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--api-key", type=str, default=None,
                    help="API key opcional do Semantic Scholar (eleva rate limit)")
parser.add_argument("--max-authors", type=int, default=None,
                    help="Limita ao primeiro N autores (útil pra teste)")
parser.add_argument("--force-refresh", action="store_true",
                    help="Ignora cache e re-consulta tudo")
args = parser.parse_args()

HEADERS = {"x-api-key": args.api_key} if args.api_key else {}
SLEEP   = SLEEP_WITH_KEY if args.api_key else SLEEP_BASE


# ─── CACHE ────────────────────────────────────────────────────────────────────
def load_cache() -> Dict:
    if not args.force_refresh and Path(CACHE_FILE).exists():
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache: Dict) -> None:
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


# ─── SEMANTIC SCHOLAR ─────────────────────────────────────────────────────────
def fetch_doi(doi: str) -> Optional[Dict]:
    """Consulta SS para um DOI. Retorna o payload ou None em caso de falha."""
    url = SS_API.format(doi=doi)
    params = {"fields": SS_FIELDS}

    for attempt in range(RETRY_MAX):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return {"_not_found": True}  # DOI não está no SS
            if r.status_code == 429:
                # Rate limit: dorme e tenta de novo
                wait = RETRY_BACKOFF * (2 ** attempt)
                print(f"    [429] aguardando {wait}s...")
                time.sleep(wait)
                continue
            if r.status_code in (500, 502, 503, 504):
                # Erro transiente do servidor
                time.sleep(RETRY_BACKOFF)
                continue
            # Outros: desiste
            return {"_error": f"HTTP {r.status_code}"}
        except requests.RequestException as e:
            time.sleep(RETRY_BACKOFF)
            continue

    return {"_error": "max_retries_exceeded"}


# ─── EXTRACTION ───────────────────────────────────────────────────────────────
def extract_doi(work_summary: Dict) -> Optional[str]:
    """Extrai o DOI de um work-summary do ORCID, se existir."""
    ext_ids = work_summary.get("external-ids") or {}
    items = ext_ids.get("external-id") or []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("external-id-type") == "doi":
            val = item.get("external-id-value")
            if val:
                return val.strip().lower()
    return None


# ─── PIPELINE ─────────────────────────────────────────────────────────────────
def main():
    print("[1/4] Carregando data.json...")
    with open(DATA_JSON_IN, encoding="utf-8") as f:
        data = json.load(f)
    print(f"      {len(data)} autores no arquivo")

    if args.max_authors:
        data = data[:args.max_authors]
        print(f"      Limitado a {len(data)} autores (--max-authors)")

    print("[2/4] Carregando cache local...")
    cache = load_cache()
    print(f"      {len(cache)} DOIs já em cache")

    print("[3/4] Coletando DOIs únicos do dataset...")
    all_dois = set()
    work_summaries_with_doi = 0
    for author in data:
        works = (author.get("activities-summary", {})
                       .get("works", {})
                       .get("group", []))
        for group in works:
            for ws in group.get("work-summary", []) or []:
                doi = extract_doi(ws)
                if doi:
                    all_dois.add(doi)
                    work_summaries_with_doi += 1
    new_dois = all_dois - set(cache.keys())
    print(f"      {len(all_dois)} DOIs únicos | {work_summaries_with_doi} work-summaries com DOI")
    print(f"      {len(new_dois)} novos a consultar (resto via cache)")

    if new_dois:
        eta_min = (len(new_dois) * SLEEP) / 60
        print(f"\n[4/4] Consultando Semantic Scholar (~{eta_min:.1f} min estimado)")
        print(f"      Rate limit ativo: {SLEEP}s entre requests "
              f"({'COM' if args.api_key else 'SEM'} api-key)")
        print()
        stats = {"ok": 0, "not_found": 0, "error": 0}
        for i, doi in enumerate(sorted(new_dois), 1):
            payload = fetch_doi(doi)
            if payload is None:
                stats["error"] += 1
                cache[doi] = {"_error": "null_payload"}
            elif payload.get("_not_found"):
                stats["not_found"] += 1
                cache[doi] = payload
            elif payload.get("_error"):
                stats["error"] += 1
                cache[doi] = payload
            else:
                stats["ok"] += 1
                cache[doi] = payload

            # Save cache periodicamente (cada 50 lookups)
            if i % 50 == 0:
                save_cache(cache)
                print(f"      [{i:>4}/{len(new_dois)}] ok={stats['ok']} 404={stats['not_found']} err={stats['error']}")

            time.sleep(SLEEP)

        save_cache(cache)
        print(f"\n      DONE: ok={stats['ok']} | 404={stats['not_found']} | erro={stats['error']}")
    else:
        print("[4/4] Nada a consultar — cache cobre todo o dataset.")

    # ─── ANEXA ENRICHMENT NO DATA ─────────────────────────────────────────────
    print("\n[5/5] Anexando enrichment ao data e salvando...")
    enriched_count = 0
    not_found_count = 0
    no_doi_count = 0
    for author in data:
        works = (author.get("activities-summary", {})
                       .get("works", {})
                       .get("group", []))
        for group in works:
            for ws in group.get("work-summary", []) or []:
                doi = extract_doi(ws)
                if not doi:
                    no_doi_count += 1
                    continue
                payload = cache.get(doi)
                if not payload or payload.get("_error") or payload.get("_not_found"):
                    not_found_count += 1
                    continue
                ws["_enriched"] = {
                    "doi":            doi,
                    "citationCount":  payload.get("citationCount", 0),
                    "venue":          payload.get("venue") or "",
                    "year":           payload.get("year"),
                    "references":     [r.get("paperId") for r in (payload.get("references") or []) if r.get("paperId")],
                }
                enriched_count += 1

    with open(DATA_JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Saída: {DATA_JSON_OUT}")
    print(f"     Work-summaries enriquecidos : {enriched_count}")
    print(f"     Sem DOI                     : {no_doi_count}")
    print(f"     DOI não-achado/erro no SS   : {not_found_count}")


if __name__ == "__main__":
    main()
