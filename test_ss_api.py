import urllib.request, urllib.parse, json, time

def search_openalex(query, year_min=2013, year_max=2018, limit=20):
    params = urllib.parse.urlencode({
        'search': query,
        'filter': f'publication_year:{year_min}-{year_max}',
        'select': 'title,publication_year,primary_location,cited_by_count,authorships,abstract_inverted_index',
        'per_page': limit,
        'mailto': 'paperman@experiment.com'
    })
    url = f'https://api.openalex.org/works?{params}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Paperman/1.0'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def reconstruct_abstract(inv_index):
    """OpenAlex retorna abstract como índice invertido: {word: [pos1, pos2]}"""
    if not inv_index:
        return ""
    words = {}
    for word, positions in inv_index.items():
        for pos in positions:
            words[pos] = word
    return ' '.join(words[i] for i in sorted(words))[:500]

# Teste 1: Lucas
print('=== paper recommendation system ===')
data = search_openalex('paper recommendation system')
for p in data.get('results', [])[:5]:
    title = p.get('title', '')[:70]
    year = p.get('publication_year', '?')
    cit = p.get('cited_by_count', 0)
    venue = (p.get('primary_location') or {}).get('source') or {}
    venue_name = venue.get('display_name', '') if isinstance(venue, dict) else ''
    authors = [a['author']['display_name'] for a in (p.get('authorships') or [])[:2]]
    print(f'  [{year}] {title}')
    print(f'         venue={venue_name} | cit={cit} | authors={authors}')

print()
time.sleep(1)

# Teste 2: Fred
print('=== calibrated recommender systems fairness ===')
data2 = search_openalex('calibrated recommender systems fairness')
for p in data2.get('results', [])[:5]:
    title = p.get('title', '')[:70]
    year = p.get('publication_year', '?')
    cit = p.get('cited_by_count', 0)
    venue = (p.get('primary_location') or {}).get('source') or {}
    venue_name = venue.get('display_name', '') if isinstance(venue, dict) else ''
    print(f'  [{year}] {title}')
    print(f'         venue={venue_name} | cit={cit}')

print('\nOpenAlex API OK!')
