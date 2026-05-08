#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merge_online_to_ab.py
Converte as recomendações online (sem_only + multiplicative) para o
formato recomendacoes_ab.json consumido pelo evaluation_app.py na Vercel.

Processa TODOS os autores presentes nos arquivos online gerados.
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

# ── Carrega os dois modelos ─────────────────────────────────────────────────────
data_a = load("recomendacoes_online_sem_only.json")
data_b = load("recomendacoes_online_multiplicative.json")

# Usa todos os autores presentes em ambos os arquivos
AUTHORS = [a for a in data_a if a in data_b]
print(f"Autores encontrados em ambos os modelos: {len(AUTHORS)}")

# ── Constrói entradas no formato AB ────────────────────────────────────────────
new_entries = {}
for author in AUTHORS:
    da = data_a[author]
    db = data_b[author]
    recs_a = da.get("recommendations", [])
    recs_b = db.get("recommendations", [])
    if not recs_a or not recs_b:
        print(f"[SKIP] {author} — lista vazia em um dos modelos.")
        continue
    new_entries[author] = {
        "author":     author,
        "base_title": da["base_title"],
        "lista_a":    [to_ab_item(r) for r in recs_a],
        "lista_b":    [to_ab_item(r) for r in recs_b],
    }
    print(f"[OK] {author}: {len(recs_a)}A / {len(recs_b)}B")

# ── Reconstrói o AB completo substituindo/inserindo todas as entradas ─────────
# Carrega AB existente para não perder avaliações já submetidas
with open(AB_JSON, encoding="utf-8") as f:
    ab_list = json.load(f)

ab_index = {entry["author"]: i for i, entry in enumerate(ab_list)}

updated = inserted = 0
for author, entry in new_entries.items():
    if author in ab_index:
        # Preserva avaliações já submetidas se existirem
        old = ab_list[ab_index[author]]
        if old.get("avaliacao_submetida"):
            print(f"[PRESERVE] {author} já avaliado — mantendo dados")
            continue
        ab_list[ab_index[author]] = entry
        updated += 1
    else:
        ab_list.append(entry)
        inserted += 1

# ── Salva ─────────────────────────────────────────────────────────────────────
with open(AB_JSON, "w", encoding="utf-8") as f:
    json.dump(ab_list, f, ensure_ascii=False, indent=2)

print(f"\nSalvo: {AB_JSON}")
print(f"Atualizados: {updated} | Inseridos: {inserted} | Total: {len(ab_list)}")
