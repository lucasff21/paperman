"""
Diagnóstico mais profundo: localiza os bytes do surrogate no arquivo Python
e mostra exatamente como eles estão armazenados no disco.
"""
target = 'offline_evaluation/evaluation_app.py'

with open(target, 'rb') as f:
    raw = f.read()

# Procura pela sequência \uD83D nos bytes (em diferentes encodings)
searches = [
    (b'\\uD83D', 'literal backslash-uD83D (ASCII)'),
    (b'\\ud83d', 'literal backslash-ud83d lowercase (ASCII)'),
    (b'\xed\xa0\xbd', 'WTF-8/CESU-8 de U+D83D (high surrogate)'),
    (b'\xf0\x9f\x93\x8b', 'UTF-8 direto do emoji U+1F4CB'),
]

for seq, desc in searches:
    idx = raw.find(seq)
    if idx >= 0:
        print(f'ENCONTRADO [{desc}] na posicao byte {idx}')
        print('Contexto raw:', raw[max(0,idx-30):idx+30+len(seq)])
        print()
    else:
        print(f'NAO encontrado: [{desc}]')
