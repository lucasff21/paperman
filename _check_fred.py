import json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados"
AUTHOR = "Frederico Araújo Durão"

for model in ['sem_only', 'multiplicative']:
    path = os.path.join(BASE, f"recomendacoes_online_{model}.json")
    with open(path, encoding="utf-8") as f:
        data = {d["author"]: d for d in json.load(f)}

    entry = data.get(AUTHOR, {})
    print(f"\n=== {model.upper()} | Título: {entry.get('base_title','')} ===")
    print(f"    Keywords: {', '.join(entry.get('keywords_used', []))}\n")
    for r in entry.get("recommendations", []):
        sc = r.get("scores", {})
        print(f"  {r['rank']:2}. [{r['year']}] sem={sc.get('score_sem',0):.3f} cit={sc.get('score_cit',0):.3f} | {r['title']}")
        print(f"      Venue: {r.get('venue','') or '—'}")
