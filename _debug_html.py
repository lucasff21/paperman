import sys, os
os.chdir('offline_evaluation')
sys.path.insert(0, '.')

import json
from evaluation_app import HTML_TEMPLATE

with open('recomendacoes_ab.json', encoding='utf-8') as f:
    data = json.load(f)

options_html = '<option value="Lucas">Lucas</option>\n'
html = HTML_TEMPLATE.split('{% for author in authors %}')[0] + options_html + HTML_TEMPLATE.split('{% endfor %}')[1]
html = html.replace('{{ data_json | safe }}', json.dumps(data))
html = html.replace('{{ avaliacoes_json | safe }}', '{}')

try:
    html.encode('utf-8')
    print('OK - HTML encodable sem erros')
except UnicodeEncodeError as e:
    print('ERRO:', e)
    pos = e.start
    print('Contexto:', repr(html[max(0, pos-80):pos+80]))
