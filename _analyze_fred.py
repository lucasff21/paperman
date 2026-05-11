import json
import sys

with open('offline_evaluation/recomendacoes_ab.json', encoding='utf-8') as f:
    data = json.load(f)

for author_data in data:
    if 'Fred' in author_data['author']:
        print(f"Encontrado: {author_data['author']}")
        lista_a = {item['title']: item['doi'] for item in author_data['lista_a']}
        lista_b = {item['title']: item['doi'] for item in author_data['lista_b']}
        
        intersect_titles = set(lista_a.keys()).intersection(set(lista_b.keys()))
        if intersect_titles:
            print(f"Repetições encontradas ({len(intersect_titles)}):")
            for i, t in enumerate(intersect_titles, 1):
                print(f"  {i}. {t} (DOI: {lista_a[t]})")
        else:
            print("=> Nenhum artigo repetiu entre a Lista A e a Lista B para este autor.")
        sys.exit()

print("Autor Fred não encontrado no JSON.")
