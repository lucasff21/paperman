import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from gerar_recomendacoes_online import load_candidates

cands = load_candidates()
print(f"Total: {len(cands)} candidatos carregados\n")
for c in cands:
    flag = " [TRADUZIDO]" if c["title"] != c["title_original"] else ""
    print(f"  {c['name']}: {c['title'][:70]}{flag}")
