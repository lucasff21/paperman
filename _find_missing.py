import json
with open('offline_evaluation/recomendacoes_ab.json', encoding='utf-8') as f:
    data = json.load(f)
for cand in data:
    if len(cand['lista_a']) != 10 or len(cand['lista_b']) != 10:
        print(f"{cand['author']}: A={len(cand['lista_a'])}, B={len(cand['lista_b'])}")
