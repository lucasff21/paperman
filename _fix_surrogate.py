"""
Corrige o par surrogate \uD83D\uDCCB (emoji 📋) que está sendo interpretado
como Unicode escapes dentro da string HTML_TEMPLATE do Python,
causando UnicodeEncodeError ao tentar servir o HTML via UTF-8.
"""
target = 'offline_evaluation/evaluation_app.py'

# Lê o arquivo preservando surrogates
with open(target, encoding='utf-8', errors='surrogatepass') as f:
    content = f.read()

# Encontra e exibe a linha problemática
surrogate_hi = '\uD83D'
surrogate_lo = '\uDCCB'
surrogate_pair = surrogate_hi + surrogate_lo

if surrogate_pair in content:
    idx = content.find(surrogate_pair)
    print(f'Surrogate encontrado na posicao {idx}')
    print('Contexto:', repr(content[max(0,idx-40):idx+40]))
    # Substitui pelo HTML entity que é ASCII-safe
    content = content.replace(surrogate_pair, '&#x1F4CB;')
    with open(target, 'w', encoding='utf-8') as f:
        f.write(content)
    print('CORRIGIDO: surrogate substituido por &#x1F4CB;')
else:
    print('Surrogate NAO encontrado - verificar outro problema')
