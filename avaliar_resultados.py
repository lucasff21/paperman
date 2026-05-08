import json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados"
OFF_TOPIC_VENUES = ['medic','health','bio','natur','lancet','jama','heart','cardio','climate','vaccine','genomic','cancer']

for model in ['sem_only', 'multiplicative']:
    path = os.path.join(BASE, f"recomendacoes_online_{model}.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    print(f"\n{'='*70}")
    print(f"  MODELO: {model.upper()}")
    print(f"{'='*70}")

    for author_data in data:
        author = author_data["author"]
        n_pub  = author_data.get("n_orcid_titles", 0)
        kws    = author_data.get("keywords_used", [])
        recs   = author_data.get("recommendations", [])

        on_topic  = 0
        off_topic = 0

        print(f"\n  Candidato : {author}")
        print(f"  Pub ORCID : {n_pub}")
        print(f"  Keywords  : {', '.join(kws)}")
        print(f"  {'Rank':<4} {'Sem':>5} {'Cit':>5}  Titulo")
        print(f"  {'-'*4} {'-'*5} {'-'*5}  {'-'*55}")

        for r in recs:
            sc    = r.get("scores", {})
            sem   = sc.get("score_sem", 0)
            cit   = sc.get("score_cit", 0)
            venue = (r.get("venue") or "").lower()
            title = r.get("title", "")

            is_off = sem < 0.20 or any(x in venue for x in OFF_TOPIC_VENUES)
            flag   = "  <-- OFF-TOPIC" if is_off else ""
            if is_off:
                off_topic += 1
            else:
                on_topic += 1

            print(f"  {r['rank']:<4} {sem:>5.3f} {cit:>5.3f}  {title[:60]}{flag}")

        total = on_topic + off_topic
        pct   = round(on_topic / total * 100) if total else 0
        print(f"\n  Resumo: {on_topic}/{total} on-topic ({pct}%) | {off_topic} off-topic")
