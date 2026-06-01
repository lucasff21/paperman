import json, math, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

THRESHOLD = 3  # nota >= 3 = relevante

with open(r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados\resultado_avaliacao_online.json", encoding="utf-8") as f:
    raw = json.load(f)

data = {k: v for k, v in raw.items() if k != "_reset"}

def get_notas(lista):
    """Retorna notas ordenadas pela posicao ordinal (nao pelo rank raw)."""
    sorted_items = sorted(lista, key=lambda x: x["rank"])
    return [item["nota"] for item in sorted_items]

def mrr(notas):
    for i, n in enumerate(notas, 1):
        if n >= THRESHOLD:
            return 1.0 / i
    return 0.0

def ap(notas):
    hits, total_rel, running_prec = 0, 0, 0.0
    total_rel = sum(1 for n in notas if n >= THRESHOLD)
    if total_rel == 0:
        return 0.0
    for i, n in enumerate(notas, 1):
        if n >= THRESHOLD:
            hits += 1
            running_prec += hits / i
    return running_prec / total_rel

def dcg(notas):
    return sum((n) / math.log2(i + 1) for i, n in enumerate(notas, 1))

def ndcg(notas):
    ideal = sorted(notas, reverse=True)
    idcg = dcg(ideal)
    return dcg(notas) / idcg if idcg > 0 else 0.0

def p_at_k(notas, k):
    top = notas[:k]
    return sum(1 for n in top if n >= THRESHOLD) / k

results = {}
for name, info in data.items():
    la = get_notas(info.get("lista_a", []))
    lb = get_notas(info.get("lista_b", []))
    results[name] = {
        "lista_a": {
            "notas": la,
            "mrr3": mrr(la[:3]), "mrr5": mrr(la[:5]), "mrr10": mrr(la[:10]),
            "map3": ap(la[:3]), "map5": ap(la[:5]), "map10": ap(la[:10]),
            "ndcg3": ndcg(la[:3]), "ndcg5": ndcg(la[:5]), "ndcg10": ndcg(la[:10]),
            "p3": p_at_k(la, 3), "p5": p_at_k(la, 5), "p10": p_at_k(la, 10),
            "media": sum(la)/len(la) if la else 0,
        },
        "lista_b": {
            "notas": lb,
            "mrr3": mrr(lb[:3]), "mrr5": mrr(lb[:5]), "mrr10": mrr(lb[:10]),
            "map3": ap(lb[:3]), "map5": ap(lb[:5]), "map10": ap(lb[:10]),
            "ndcg3": ndcg(lb[:3]), "ndcg5": ndcg(lb[:5]), "ndcg10": ndcg(lb[:10]),
            "p3": p_at_k(lb, 3), "p5": p_at_k(lb, 5), "p10": p_at_k(lb, 10),
            "media": sum(lb)/len(lb) if lb else 0,
        },
        "survey_a": info.get("survey_a", {}),
        "survey_b": info.get("survey_b", {}),
    }

def avg_metric(metric):
    va = [results[n]["lista_a"][metric] for n in results]
    vb = [results[n]["lista_b"][metric] for n in results]
    return sum(va)/len(va), sum(vb)/len(vb)

metrics = ["mrr3", "mrr5", "mrr10", "map3", "map5", "map10", "ndcg3", "ndcg5", "ndcg10", "p3", "p5", "p10", "media"]
agg = {m: avg_metric(m) for m in metrics}

SURVEY_KEYS = ["relevancia", "diversidade", "precisao", "atualidade", "surpresa"]
def avg_survey(key):
    va = [results[n]["survey_a"].get(key, 0) for n in results if results[n]["survey_a"]]
    vb = [results[n]["survey_b"].get(key, 0) for n in results if results[n]["survey_b"]]
    return (sum(va)/len(va) if va else 0), (sum(vb)/len(vb) if vb else 0)

survey_agg = {k: avg_survey(k) for k in SURVEY_KEYS}

# Salva JSON para o HTML
output = {"agg": {m: {"a": agg[m][0], "b": agg[m][1]} for m in metrics}}
with open(r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados\_metrics_online_k.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print("Salvo em _metrics_online_k.json")

