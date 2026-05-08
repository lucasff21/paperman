#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados"
OUT  = r"c:\Users\Lucas\Documents\Paperman\paperman_back\relatorio_online_ab.html"

with open(os.path.join(BASE, "recomendacoes_online_sem_only.json"), encoding="utf-8") as f:
    data_a = {d["author"]: d for d in json.load(f)}
with open(os.path.join(BASE, "recomendacoes_online_multiplicative.json"), encoding="utf-8") as f:
    data_b = {d["author"]: d for d in json.load(f)}

AUTHORS = ["Frederico Araújo Durão", "Lucas França Freitas"]

def stars(n):
    return "★" * n + "☆" * (5 - n)

def nota_color(n):
    colors = {1: "#c62828", 2: "#e65100", 3: "#f57f17", 4: "#558b2f", 5: "#1b5e20"}
    return colors.get(n, "#aaa")

def score_bar(val, max_val=1.0):
    pct = min(100, round((val / max_val) * 100)) if max_val > 0 else 0
    color = "#1565c0" if val > 0.3 else "#e65100" if val > 0.1 else "#ccc"
    return f'<div style="display:flex;align-items:center;gap:6px;"><div style="flex:1;background:#eee;border-radius:3px;height:8px;"><div style="width:{pct}%;background:{color};height:8px;border-radius:3px;"></div></div><span style="font-size:.75em;color:#555;min-width:38px;">{val:.3f}</span></div>'

def card(rec, model_cls):
    scores = rec.get("scores", {})
    tot  = scores.get("score_total", 0)
    sem  = scores.get("score_sem", 0)
    cit  = scores.get("score_cit", 0)
    qua  = scores.get("qua_raw", 0)
    rec_s= scores.get("score_rec", 0)
    authors = ", ".join(rec.get("authors", [])[:2])
    if len(rec.get("authors", [])) > 2:
        authors += " et al."
    abstract = rec.get("abstract", "")[:200] + ("..." if len(rec.get("abstract","")) > 200 else "")
    border = "#1565c0" if model_cls == "a" else "#c62828"
    bg = "#f0f4ff" if model_cls == "a" else "#fff0f0"
    return f"""
<div style="background:{bg};border-left:4px solid {border};border-radius:6px;padding:14px;margin:10px 0;position:relative;">
  <div style="font-weight:bold;color:#111;font-size:.95em;margin-bottom:4px;">
    <span style="background:{border};color:white;border-radius:50%;width:22px;height:22px;display:inline-flex;align-items:center;justify-content:center;font-size:.8em;margin-right:6px;">{rec['rank']}</span>
    {rec['title']}
  </div>
  <div style="font-size:.78em;color:#666;margin-bottom:8px;">{authors} &nbsp;|&nbsp; {rec.get('year','?')} &nbsp;|&nbsp; {rec.get('venue','') or '—'} &nbsp;|&nbsp; {rec.get('n_citation',0)} cit.</div>
  {"<div style='font-size:.75em;color:#888;font-style:italic;margin-bottom:8px;'>" + abstract + "</div>" if abstract else ""}
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px 16px;font-size:.78em;">
    <div><span style="color:#555;">Total</span> {score_bar(tot)}</div>
    <div><span style="color:#555;">Semântica</span> {score_bar(sem)}</div>
    <div><span style="color:#555;">Citações</span> {score_bar(cit)}</div>
    <div><span style="color:#555;">Qualis</span> {score_bar(qua)}</div>
  </div>
</div>"""

sections = ""
for author in AUTHORS:
    da = data_a.get(author, {})
    db = data_b.get(author, {})
    kw_a = da.get("keywords_used", [])
    kw_b = db.get("keywords_used", [])
    n_orcid = da.get("n_orcid_titles", 0)
    base_title = da.get("base_title", "")
    recs_a = da.get("recommendations", [])
    recs_b = db.get("recommendations", [])

    cards_a = "".join(card(r, "a") for r in recs_a)
    cards_b = "".join(card(r, "b") for r in recs_b)
    kw_pills_a = " ".join(f'<span style="background:#e3f2fd;color:#1565c0;padding:2px 8px;border-radius:10px;font-size:.75em;font-weight:bold;">"{k}"</span>' for k in kw_a)
    kw_pills_b = " ".join(f'<span style="background:#fce4ec;color:#c62828;padding:2px 8px;border-radius:10px;font-size:.75em;font-weight:bold;">"{k}"</span>' for k in kw_b)

    sections += f"""
<div style="background:white;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,.08);padding:24px;margin-bottom:32px;">
  <h2 style="margin:0 0 4px;color:#1a237e;">{author}</h2>
  <p style="margin:0 0 12px;color:#666;font-size:.9em;">
    Perfil ORCID: <strong>{n_orcid} publicações</strong> &nbsp;|&nbsp;
    Título âncora: <em>{base_title}</em>
  </p>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;">
    <div>
      <div style="background:#1565c0;color:white;padding:10px 16px;border-radius:8px 8px 0 0;font-weight:bold;">
        🅐 Lista A — sem_only (Semântica Pura)
      </div>
      <div style="padding:8px 0;">
        <div style="font-size:.78em;color:#666;margin-bottom:8px;">Keywords usadas: {kw_pills_a}</div>
        {cards_a}
      </div>
    </div>
    <div>
      <div style="background:#c62828;color:white;padding:10px 16px;border-radius:8px 8px 0 0;font-weight:bold;">
        🅑 Lista B — multiplicative (Sem × Cit × Qualis × Rec)
      </div>
      <div style="padding:8px 0;">
        <div style="font-size:.78em;color:#666;margin-bottom:8px;">Keywords usadas: {kw_pills_b}</div>
        {cards_b}
      </div>
    </div>
  </div>
</div>"""

html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Relatório A/B — Pipeline Online Paperman</title>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; padding: 24px; color: #222; }}
  h1 {{ color: #1a237e; margin-bottom: 4px; }}
  .subtitle {{ color: #666; font-style: italic; margin-bottom: 28px; }}
  .info-box {{ background: #fff8e1; border-left: 4px solid #f57f17; padding: 12px 16px; border-radius: 4px; margin-bottom: 24px; font-size: .9em; }}
</style>
</head>
<body>
<h1>📊 Relatório A/B — Pipeline Online Paperman</h1>
<p class="subtitle">Motor de Busca: OpenAlex API &nbsp;|&nbsp; Perfil: ORCID API &nbsp;|&nbsp; Scoring: Word2Vec + Qualis CAPES</p>

<div class="info-box">
  <strong>Metodologia:</strong> Para cada candidato, o sistema buscou seu perfil no ORCID, extraiu bigramas dos títulos,
  consultou a OpenAlex API por até 500 papers da área, aplicou um pré-filtro semântico (≥0.15) e
  então pontuou com dois modelos: <strong>Lista A</strong> (semântica pura) e <strong>Lista B</strong> (multiplicativo).
</div>

{sections}
</body>
</html>"""

with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print(f"HTML gerado: {OUT}")
