import json
path = r'c:\Users\Lucas\Documents\Paperman\paperman_back\paperman\offline_evaluation\recomendacoes_ab.json'
with open(path, encoding='utf-8') as f:
    data = json.load(f)

total_papers = 0
papers_with_doi = 0
samples = []

for entry in data:
    for lst in ['lista_a', 'lista_b']:
        for rec in entry.get(lst, []):
            total_papers += 1
            if rec.get('doi'):
                papers_with_doi += 1
                if len(samples) < 3:
                    samples.append(f"- {rec['title'][:50]}... -> {rec['doi']}")

print(f'Total de papers: {total_papers}')
print(f'Com DOI/Link: {papers_with_doi} ({(papers_with_doi/total_papers)*100:.1f}%)')
print('\nExemplos:')
for s in samples:
    print(s)
