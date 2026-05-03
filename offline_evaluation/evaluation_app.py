import json
import os
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

# Caminhos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECOMENDACOES_FILE = os.path.join(BASE_DIR, "recomendacoes_sem_only.json")

# Configurações JSONBin.io (injetadas via Vercel Env Vars)
JSONBIN_BIN_ID = os.getenv("JSONBIN_BIN_ID")
JSONBIN_MASTER_KEY = os.getenv("JSONBIN_MASTER_KEY")

app = FastAPI(title="Avaliação Paperman")

def load_data():
    with open(RECOMENDACOES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

async def load_avaliacoes():
    """Lê as avaliações do JSONBin. Se falhar ou estiver vazio, retorna {}"""
    if not JSONBIN_BIN_ID or not JSONBIN_MASTER_KEY:
        print("Aviso: Chaves do JSONBin não encontradas. Usando dicionário vazio.")
        return {}
        
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
    headers = {"X-Master-Key": JSONBIN_MASTER_KEY}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get("record", {})
        else:
            print(f"Erro ao ler JSONBin: {response.status_code} - {response.text}")
            return {}

async def save_avaliacoes(data):
    """Salva/Atualiza as avaliações no JSONBin."""
    if not JSONBIN_BIN_ID or not JSONBIN_MASTER_KEY:
        print("Aviso: Chaves não configuradas. Dados NÃO foram salvos na nuvem.")
        return
        
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
    headers = {
        "Content-Type": "application/json",
        "X-Master-Key": JSONBIN_MASTER_KEY
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.put(url, headers=headers, json=data)
        if response.status_code != 200:
            print(f"Erro ao salvar JSONBin: {response.status_code} - {response.text}")

app = FastAPI(title="Avaliação Paperman")



class AvaliacaoItem(BaseModel):
    rank: int
    nota: int
    comentario: Optional[str] = ""

class AvaliacaoPayload(BaseModel):
    author: str
    avaliacoes: List[AvaliacaoItem]

# TEMPLATE HTML EMBUTIDO PARA FACILITAR (sem precisar de arquivos externos)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Avaliação de Recomendações</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; color: #333; }
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #2c3e50; }
        .search-box { display: flex; gap: 10px; margin-bottom: 20px; }
        .search-box input { flex: 1; padding: 12px; font-size: 16px; border-radius: 4px; border: 1px solid #ccc; }
        .btn-load { padding: 12px 20px; font-size: 16px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
        .btn-load:hover { background: #2980b9; }
        .paper-card h3 { margin-top: 0; color: #2980b9; }
        .rating-group { display: flex; gap: 15px; margin: 15px 0; align-items: center; }
        .rating-group label { cursor: pointer; padding: 8px 12px; background: #eee; border-radius: 4px; transition: 0.2s; }
        .rating-group input[type="radio"] { display: none; }
        .rating-group input[type="radio"]:checked + label { background: #3498db; color: white; font-weight: bold; }
        .comment-box { width: 100%; padding: 10px; margin-top: 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        button.submit-btn { width: 100%; padding: 15px; font-size: 18px; background: #27ae60; color: white; border: none; border-radius: 6px; cursor: pointer; transition: 0.3s; }
        button.submit-btn:hover { background: #2ecc71; }
        .hidden { display: none; }
        .status-badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-left: 10px; }
        .status-pendente { background: #f39c12; color: white; }
        .status-concluido { background: #27ae60; color: white; }
        #success-msg { text-align: center; color: #27ae60; font-size: 18px; margin-top: 20px; display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Avaliação do Sistema Paperman</h1>

        <div style="background:#eaf4fb; border-left: 4px solid #3498db; padding: 15px 20px; border-radius: 4px; margin-bottom: 25px; font-size: 15px; line-height: 1.7;">
            <strong>Prezado(a) pesquisador(a),</strong><br><br>
            Você está participando de um estudo de avaliação do <strong>Paperman</strong>, um sistema de recomendação de artigos científicos desenvolvido como trabalho de dissertação de mestrado.<br><br>
            O sistema analisou o título da sua pesquisa e gerou <strong>10 artigos científicos</strong> que considera relevantes para o seu tema. Sua tarefa é avaliar cada um desses artigos indicando o quanto ele é relevante para a sua área de pesquisa, em uma escala de <strong>1 (Totalmente Irrelevante)</strong> a <strong>5 (Muito Relevante)</strong>.<br><br>
            Sua participação é fundamental para validar a qualidade das recomendações geradas. Os dados coletados serão utilizados exclusivamente para fins acadêmicos.<br><br>
            <strong>Tempo estimado:</strong> 5 a 10 minutos. Obrigado pela colaboração! 🙏
        </div>

        <p style="text-align:center; font-size: 16px;">Selecione seu nome abaixo para começar:</p>

        <div class="search-box">
            <input list="author-list" id="author-input" placeholder="Comece a digitar seu nome..." autocomplete="off">
            <datalist id="author-list">
                {% for author in authors %}
                <option value="{{ author.name }}{% if author.status == 'concluido' %} [CONCLUÍDO]{% endif %}"></option>
                {% end汇 %}
            </datalist>
            <button id="btn-load" class="btn-load">Acessar</button>
        </div>

        <div id="evaluation-area" class="hidden">
            <div class="header-info">
                <strong>Seu Tema Base:</strong> <br>
                <span id="base-title" style="font-size: 1.1em; color: #555;"></span>
            </div>
            
            <p>Avalie os artigos abaixo em relação ao tema base (1 = Totalmente Irrelevante, 5 = Muito Relevante).</p>

            <form id="eval-form">
                <div id="papers-container"></div>
                <button type="submit" class="submit-btn">Salvar Avaliações</button>
            </form>
            <div id="success-msg">Avaliações salvas com sucesso! Muito obrigado pela participação.</div>
        </div>
    </div>

    <script>
        const data = {{ data_json | safe }};
        const avaliacoes = {{ avaliacoes_json | safe }};
        const input = document.getElementById('author-input');
        const btnLoad = document.getElementById('btn-load');
        const evalArea = document.getElementById('evaluation-area');
        const papersContainer = document.getElementById('papers-container');
        const baseTitle = document.getElementById('base-title');
        const form = document.getElementById('eval-form');
        const successMsg = document.getElementById('success-msg');

        btnLoad.addEventListener('click', () => {
            let authorName = input.value.trim();
            authorName = authorName.replace(' [CONCLUÍDO]', ''); // limpa a tag visual
            
            if (!authorName) {
                evalArea.classList.add('hidden');
                return;
            }
            
            const authorData = data.find(a => a.author === authorName);
            if (!authorData) {
                alert("Nome não encontrado! Por favor, selecione seu nome na lista que aparece ao digitar.");
                evalArea.classList.add('hidden');
                return;
            }
            
            successMsg.style.display = 'none';
            form.style.display = 'block';

            const savedEvals = avaliacoes[authorName] || [];

            baseTitle.textContent = authorData.base_title;
            papersContainer.innerHTML = '';

            authorData.recommendations.forEach(rec => {
                const saved = savedEvals.find(ev => ev.rank === rec.rank) || {};
                const nota = saved.nota || '';
                const comentario = saved.comentario || '';

                const div = document.createElement('div');
                div.className = 'paper-card';
                div.innerHTML = `
                    <h3>${rec.rank}. ${rec.title}</h3>
                    <p><strong>Autores:</strong> ${rec.authors.join(', ')} | <strong>Ano:</strong> ${rec.year} | <strong>Local:</strong> ${rec.venue || 'N/A'}</p>
                    <p style="margin-bottom: 5px;"><strong>Qual a relevância deste artigo para o seu tema?</strong></p>
                    <div class="rating-group" data-rank="${rec.rank}">
                        ${[1, 2, 3, 4, 5].map(n => `
                            <input type="radio" name="nota_${rec.rank}" id="nota_${rec.rank}_${n}" value="${n}" ${nota == n ? 'checked' : ''} required>
                            <label for="nota_${rec.rank}_${n}">${n}</label>
                        `).join('')}
                    </div>
                    <input type="text" class="comment-box" id="comentario_${rec.rank}" placeholder="Comentário opcional sobre por que deu essa nota..." value="${comentario}">
                `;
                papersContainer.appendChild(div);
            });

            evalArea.classList.remove('hidden');
        });

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = form.querySelector('.submit-btn');
            submitBtn.disabled = true;
            submitBtn.textContent = '⏳ Salvando...';

            let authorName = input.value.replace(' [CONCLUÍDO]', '').trim();
            const authorData = data.find(a => a.author === authorName);
            
            const avaliacoes_enviadas = authorData.recommendations.map(rec => {
                const nota = document.querySelector(`input[name="nota_${rec.rank}"]:checked`).value;
                const comentario = document.getElementById(`comentario_${rec.rank}`).value;
                return { rank: rec.rank, nota: parseInt(nota), comentario: comentario };
            });

            const payload = { author: authorName, avaliacoes: avaliacoes_enviadas };

            const res = await fetch('/api/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                form.style.display = 'none';
                successMsg.style.display = 'block';
                // Atualiza cache local visual
                avaliacoes[authorName] = avaliacoes_enviadas;
                input.value = `${authorName} [CONCLUÍDO]`;
            } else {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Salvar Avaliações';
                alert("Erro ao salvar avaliações. Por favor, tente novamente.");
            }
        });
    </script>
</body>
</html>
""".replace("{% end汇 %}", "{% endfor %}")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    data = load_data()
    avaliacoes = await load_avaliacoes()
    
    authors = []
    for a in data:
        status = "concluido" if a["author"] in avaliacoes and len(avaliacoes[a["author"]]) > 0 else "pendente"
        authors.append({"name": a["author"], "status": status})
        
    # Renderizamos de forma simples com replace para evitar configurar diretório de templates complexos agora
    html = HTML_TEMPLATE
    html = html.replace("{% for author in authors %}", "")
    
    # Tratando o for loop de forma simples em Python e injetando
    options_html = ""
    for a in authors:
        status_text = " [CONCLUÍDO]" if a["status"] == "concluido" else ""
        options_html += f'<option value="{a["name"]}{status_text}"></option>\n'
    
    html = HTML_TEMPLATE.split('{% for author in authors %}')[0] + options_html + HTML_TEMPLATE.split('{% endfor %}')[1]
    
    html = html.replace("{{ data_json | safe }}", json.dumps(data))
    html = html.replace("{{ avaliacoes_json | safe }}", json.dumps(avaliacoes))
    
    return HTMLResponse(content=html)

@app.post("/api/submit")
async def submit_eval(payload: AvaliacaoPayload):
    avaliacoes = await load_avaliacoes()
    avaliacoes[payload.author] = [item.dict() for item in payload.avaliacoes]
    await save_avaliacoes(avaliacoes)
    return {"status": "success"}

if __name__ == "__main__":
    print(f"Servidor rodando em http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
