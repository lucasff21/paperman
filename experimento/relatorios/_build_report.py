import json, re

with open(r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados\_metrics_output.json", encoding="utf-8") as f:
    data = json.load(f)

with open(r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados\_report_template.html", encoding="utf-8") as f:
    html = f.read()

# Inject user data
users_json = json.dumps(data["users"], ensure_ascii=False, indent=2)
html = html.replace("%%USERS_JSON%%", users_json)

# Inject correct AGG and SURVEY
agg_js = json.dumps(data["agg"], ensure_ascii=False)
survey_js = json.dumps(data["survey"], ensure_ascii=False)
html = html.replace(
    'const AGG = {"mrr":{"a":0.6319,"b":0.6602},"map":{"a":0.5439,"b":0.6022},"ndcg":{"a":0.8895,"b":0.8550},"p5":{"a":0.3852,"b":0.5037},"p10":{"a":0.4074,"b":0.5259},"media":{"a":2.3259,"b":2.7815}};',
    f'const AGG = {agg_js};'
)
html = html.replace(
    'const SURVEY = {"relevancia":{"a":2.56,"b":3.07},"diversidade":{"a":2.78,"b":3.04},"precisao":{"a":1.96,"b":2.67},"atualidade":{"a":2.59,"b":3.48},"surpresa":{"a":2.15,"b":2.85}};',
    f'const SURVEY = {survey_js};'
)

# Fix participant count badge
n = len(data["users"])
html = html.replace('>27 participantes<', f'>{n} participantes<')

out_path = r"c:\Users\Lucas\Documents\Paperman\paperman_back\resultados\resultado_avaliacao_online.html"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"HTML gerado com {n} participantes: {out_path}")
