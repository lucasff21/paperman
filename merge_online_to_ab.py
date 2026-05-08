#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merge_online_to_ab.py
Converte as recomendações online (sem_only + multiplicative) para o
formato recomendacoes_ab.json consumido pelo evaluation_app.py na Vercel.

Atualiza (ou insere) as entradas de Fred e Lucas no arquivo existente.
"""
import json, os

BASE_RES = r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados"
AB_JSON  = r"c:\Users\Lucas\Documents\Paperman\paperman_back\paperman\offline_evaluation\recomendacoes_ab.json"

def load(filename):
    path = os.path.join(BASE_RES, filename)
    with open(path, encoding="utf-8") as f:
        return {d["author"]: d for d in json.load(f)}

def to_ab_item(rec):
    """Converte item do formato online para o formato lista_a/lista_b."""
    scores = rec.get("scores", {})
    return {
        "rank":             rec["rank"],
        "title":            rec["title"],
        "year":             rec["year"],
        "venue":            rec.get("venue", ""),
        "authors":          rec.get("authors", []),
        "n_citation":       rec.get("n_citation", 0),
        "abstract":         rec.get("abstract", ""),
        "scores": {
            "score_total":  scores.get("score_total", 0),
            "score_sem":    scores.get("score_sem",   0),
            "score_rec":    scores.get("score_rec",   0),
            "score_cit":    scores.get("score_cit",   0),
            "qua_term":     scores.get("qua_term",    0),
            "qua_raw":      scores.get("qua_raw",     0),
        },
        "avaliacao_usuario": None,
        "comentario":       None,
    }

# ── Carrega os dois modelos ───────────────────────────────────────────────────
data_a = load("recomendacoes_online_sem_only.json")
data_b = load("recomendacoes_online_multiplicative.json")

AUTHORS = ["Frederico Araújo Durão", "Lucas França Freitas"]

# ── Constrói entradas no formato AB ──────────────────────────────────────────
new_entries = {}
for author in AUTHORS:
    da = data_a.get(author)
    db = data_b.get(author)
    if not da or not db:
        print(f"[SKIP] {author} não encontrado em um dos arquivos.")
        continue
    new_entries[author] = {
        "author":     author,
        "base_title": da["base_title"],
        "lista_a":    [to_ab_item(r) for r in da["recommendations"]],
        "lista_b":    [to_ab_item(r) for r in db["recommendations"]],
    }
    print(f"[OK] {author}: {len(da['recommendations'])} items A / {len(db['recommendations'])} items B")

# ── Carrega AB existente e substitui/insere Fred e Lucas ─────────────────────
with open(AB_JSON, encoding="utf-8") as f:
    ab_list = json.load(f)

# Índice para lookup rápido
ab_index = {entry["author"]: i for i, entry in enumerate(ab_list)}

for author, entry in new_entries.items():
    if author in ab_index:
        print(f"[UPDATE] Substituindo entrada existente de '{author}' (índice {ab_index[author]})")
        ab_list[ab_index[author]] = entry
    else:
        print(f"[INSERT] Adicionando nova entrada de '{author}'")
        ab_list.append(entry)

# ── Salva ─────────────────────────────────────────────────────────────────────
with open(AB_JSON, "w", encoding="utf-8") as f:
    json.dump(ab_list, f, ensure_ascii=False, indent=2)

print(f"\nSalvo: {AB_JSON}")
print(f"Total de autores no arquivo: {len(ab_list)}")
