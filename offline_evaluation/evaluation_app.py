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
RECOMENDACOES_FILE = os.path.join(BASE_DIR, "recomendacoes_ab.json")

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

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return data.get("record", {})
            else:
                print(f"Erro ao ler JSONBin: {response.status_code} - {response.text}")
                return {}
    except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.TimeoutException, Exception) as e:
        print(f"Timeout/Erro ao conectar JSONBin: {e}. Retornando vazio.")
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

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.put(url, headers=headers, json=data)
            if response.status_code != 200:
                print(f"Erro ao salvar JSONBin: {response.status_code} - {response.text}")
                raise HTTPException(status_code=500, detail="Falha ao salvar no JSONBin")
    except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.TimeoutException) as e:
        print(f"Timeout ao salvar JSONBin: {e}")
        raise HTTPException(status_code=503, detail="Timeout ao conectar ao JSONBin. Tente novamente.")

app = FastAPI(title="Avaliação Paperman")



class AvaliacaoItem(BaseModel):
    rank: int
    nota: int
    comentario: Optional[str] = ""

class AvaliacaoPayload(BaseModel):
    author: str
    lista_a: List[AvaliacaoItem]
    lista_b: List[AvaliacaoItem]

class SurveyPayload(BaseModel):
    author: str
    relevancia: int
    diversidade: int
    precisao: int
    interesse: int
    surpresa: int

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
        .search-box select { flex: 1; padding: 12px; font-size: 16px; border-radius: 4px; border: 1px solid #ccc; background: white; cursor: pointer; }
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
        .abstract-box { display: block; background: #f8f9fa; border-left: 3px solid #aaa; padding: 8px 12px; margin: 8px 0; font-size: 13px; color: #444; border-radius: 3px; line-height: 1.6; }
        .btn-abstract { background: none; border: 1px solid #aaa; border-radius: 4px; padding: 3px 10px; font-size: 12px; cursor: pointer; color: #555; margin-bottom: 4px; }
        .btn-abstract:hover { background: #eee; }
        #success-msg { text-align: center; color: #27ae60; font-size: 18px; margin-top: 20px; display: none; }
        /* Survey */
        #survey-area { display: none; margin-top: 30px; }
        .survey-question { background: #f8f9fa; border-radius: 8px; padding: 20px; margin-bottom: 20px; border-left: 4px solid #3498db; }
        .survey-question p.q-title { font-weight: bold; font-size: 16px; margin: 0 0 4px 0; color: #2c3e50; }
        .survey-question p.q-desc { font-size: 14px; color: #555; margin: 0 0 14px 0; line-height: 1.5; }
        .likert-group { display: flex; gap: 10px; flex-wrap: wrap; }
        .likert-group input[type="radio"] { display: none; }
        .likert-group label { cursor: pointer; padding: 10px 18px; background: #eee; border-radius: 6px; font-weight: bold; font-size: 15px; transition: 0.2s; }
        .likert-group input[type="radio"]:checked + label { background: #3498db; color: white; }
        .likert-group label:hover { background: #d0e8f7; }
        #survey-submit-btn { width: 100%; padding: 15px; font-size: 18px; background: #27ae60; color: white; border: none; border-radius: 6px; cursor: pointer; margin-top: 10px; transition: 0.3s; }
        #survey-submit-btn:hover { background: #2ecc71; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Avaliação do Sistema Paperman</h1>

        <div style="background:#eaf4fb; border-left: 4px solid #3498db; padding: 15px 20px; border-radius: 4px; margin-bottom: 25px; font-size: 15px; line-height: 1.8;">
            Com base no título da sua pesquisa, o <strong>Paperman</strong> selecionou <strong>duas listas (Lista A e Lista B) com 10 artigos científicos cada</strong> para você avaliar.<br>
            Para cada artigo, indique o quanto ele é relevante para o seu tema usando a escala de <strong>1</strong> (Totalmente Irrelevante) a <strong>5</strong> (Muito Relevante).<br>
            <span style="color:#555;">⏱ Tempo estimado: 10 a 15 minutos. Obrigado pela participação!</span>
        </div>

        <p style="text-align:center; font-size: 16px;">Selecione seu nome abaixo para começar:</p>

        <div class="search-box">
            <select id="author-input">
                <option value="" disabled selected>Selecione seu nome...</option>
                {% for author in authors %}
                <option value="{{ author.name }}">{{ author.name }}{% if author.status == 'concluido' %} [CONCLUÍDO]{% endif %}</option>
                {% end汇 %}
            </select>
            <button id="btn-load" class="btn-load">Acessar</button>
        </div>

        <div id="evaluation-area" class="hidden">
            <div class="header-info">
                <strong>Seu Tema Base:</strong> <br>
                <span id="base-title" style="font-size: 1.1em; color: #555;"></span>
            </div>
            
            <p>Avalie os artigos abaixo em relação ao tema base (1 = Totalmente Irrelevante, 5 = Muito Relevante).</p>

            <form id="eval-form">
                <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px;">Lista B</h2>
                <div id="papers-container-b"></div>

                <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px; margin-top: 40px;">Lista A</h2>
                <div id="papers-container-a"></div>
                
                <button type="submit" class="submit-btn" style="margin-top: 30px;">Salvar Avaliações</button>
            </form>
            <div id="success-msg">Avaliações salvas com sucesso! Muito obrigado pela participação.</div>

            <!-- Questionário pós-avaliação -->
            <div id="survey-area">
                <h2 style="color: #2c3e50; border-top: 2px solid #eee; padding-top: 30px; margin-top: 10px;">📋 Questionário Final</h2>
                <p style="color:#555; margin-bottom: 24px;">Avalie o sistema de recomendação como um todo (1 = Discordo totalmente, 5 = Concordo totalmente).</p>

                <div class="survey-question">
                    <p class="q-title">1. Relevância</p>
                    <p class="q-desc">Os artigos recomendados são relevantes para meus interesses de pesquisa ou para o tema investigado.</p>
                    <div class="likert-group">
                        ${[1,2,3,4,5].map(n => `<input type="radio" name="sq_relevancia" id="sq_rel_${n}" value="${n}"><label for="sq_rel_${n}">${n}</label>`).join('')}
                    </div>
                </div>

                <div class="survey-question">
                    <p class="q-title">2. Diversidade</p>
                    <p class="q-desc">As recomendações abordaram diferentes perspectivas, subáreas ou abordagens dentro do meu tema de pesquisa.</p>
                    <div class="likert-group">
                        ${[1,2,3,4,5].map(n => `<input type="radio" name="sq_diversidade" id="sq_div_${n}" value="${n}"><label for="sq_div_${n}">${n}</label>`).join('')}
                    </div>
                </div>

                <div class="survey-question">
                    <p class="q-title">3. Precisão</p>
                    <p class="q-desc">As recomendações correspondem com precisão ao assunto ou contexto de busca informado.</p>
                    <div class="likert-group">
                        ${[1,2,3,4,5].map(n => `<input type="radio" name="sq_precisao" id="sq_pre_${n}" value="${n}"><label for="sq_pre_${n}">${n}</label>`).join('')}
                    </div>
                </div>

                <div class="survey-question">
                    <p class="q-title">4. Interesse</p>
                    <p class="q-desc">Os artigos recomendados despertam meu interesse e motivariam uma leitura mais aprofundada.</p>
                    <div class="likert-group">
                        ${[1,2,3,4,5].map(n => `<input type="radio" name="sq_interesse" id="sq_int_${n}" value="${n}"><label for="sq_int_${n}">${n}</label>`).join('')}
                    </div>
                </div>

                <div class="survey-question">
                    <p class="q-title">5. Surpresa (Serendipidade)</p>
                    <p class="q-desc">As recomendações apresentaram artigos inesperados, mas que ainda assim se mostraram úteis ou potencialmente valiosos para minha pesquisa.</p>
                    <div class="likert-group">
                        ${[1,2,3,4,5].map(n => `<input type="radio" name="sq_surpresa" id="sq_sur_${n}" value="${n}"><label for="sq_sur_${n}">${n}</label>`).join('')}
                    </div>
                </div>

                <button id="survey-submit-btn">Enviar Questionário</button>
            </div>
        </div>
    </div>

    <script>
        const data = {{ data_json | safe }};
        const avaliacoes = {{ avaliacoes_json | safe }};
        const input = document.getElementById('author-input');
        const btnLoad = document.getElementById('btn-load');
        const evalArea = document.getElementById('evaluation-area');
        const papersContainerA = document.getElementById('papers-container-a');
        const papersContainerB = document.getElementById('papers-container-b');
        const baseTitle = document.getElementById('base-title');
        const form = document.getElementById('eval-form');
        const successMsg = document.getElementById('success-msg');
        const surveyArea = document.getElementById('survey-area');
        const surveySubmitBtn = document.getElementById('survey-submit-btn');

        function renderList(container, recommendations, listId, savedEvals) {
            container.innerHTML = '';
            recommendations.forEach(rec => {
                const saved = savedEvals.find(ev => ev.rank === rec.rank) || {};
                const nota = saved.nota || '';
                const comentario = saved.comentario || '';
                const abstractHtml = rec.abstract
                    ? `<button type="button" class="btn-abstract" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none'; this.textContent = this.textContent === '▲ Ocultar resumo' ? '▼ Ver resumo' : '▲ Ocultar resumo';">▲ Ocultar resumo</button><div class="abstract-box">${rec.abstract}</div>`
                    : '';

                const div = document.createElement('div');
                div.className = 'paper-card';
                div.innerHTML = `
                    <h3>${rec.rank}. ${rec.doi ? `<a href="${rec.doi}" target="_blank" rel="noopener noreferrer" style="color:#2980b9;text-decoration:none;" onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">${rec.title}</a>` : rec.title}</h3>
                    <p><strong>Autores:</strong> ${rec.authors.join(', ')} | <strong>Ano:</strong> ${rec.year} | <strong>Local:</strong> ${rec.venue || 'N/A'}</p>
                    ${abstractHtml}
                    <p style="margin-bottom: 5px;"><strong>Qual a relevância deste artigo para o seu tema?</strong></p>
                    <div class="rating-group" data-rank="${rec.rank}">
                        ${[1, 2, 3, 4, 5].map(n => `
                            <input type="radio" name="nota_${listId}_${rec.rank}" id="nota_${listId}_${rec.rank}_${n}" value="${n}" ${nota == n ? 'checked' : ''}>
                            <label for="nota_${listId}_${rec.rank}_${n}">${n}</label>
                        `).join('')}
                    </div>
                    <input type="text" class="comment-box" id="comentario_${listId}_${rec.rank}" placeholder="Comentário opcional sobre por que deu essa nota..." value="${comentario}">
                `;
                container.appendChild(div);
            });
        }

        btnLoad.addEventListener('click', () => {
            const authorName = input.value.trim();

            if (!authorName) {
                evalArea.classList.add('hidden');
                return;
            }

            const authorData = data.find(a => a.author === authorName);
            if (!authorData) {
                alert("Nome não encontrado! Por favor, selecione seu nome na lista.");
                evalArea.classList.add('hidden');
                return;
            }
            
            successMsg.style.display = 'none';
            form.style.display = 'block';

            const savedData = avaliacoes[authorName] || { lista_a: [], lista_b: [] };
            
            // Retrocompatibilidade para quem já avaliou no modelo antigo: converte array simples para lista_a vazia e reseta
            const savedListaA = Array.isArray(savedData) ? [] : (savedData.lista_a || []);
            const savedListaB = Array.isArray(savedData) ? [] : (savedData.lista_b || []);

            baseTitle.textContent = authorData.base_title;
            
            renderList(papersContainerA, authorData.lista_a, 'a', savedListaA);
            renderList(papersContainerB, authorData.lista_b, 'b', savedListaB);

            evalArea.classList.remove('hidden');
        });

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = form.querySelector('.submit-btn');
            submitBtn.disabled = true;
            submitBtn.textContent = '⏳ Salvando...';

            const authorName = input.value.trim();
            const authorData = data.find(a => a.author === authorName);
            
            const extractEvals = (recommendations, listId) => {
                // Validação rigorosa: garantir que todos foram avaliados
                for (let rec of recommendations) {
                    const checked = document.querySelector(`input[name="nota_${listId}_${rec.rank}"]:checked`);
                    if (!checked) {
                        const listaNome = listId === 'a' ? 'Lista A' : 'Lista B';
                        throw new Error(`Por favor, forneça uma nota para o artigo ${rec.rank} da ${listaNome}.`);
                    }
                }

                return recommendations.map(rec => {
                    const nota = document.querySelector(`input[name="nota_${listId}_${rec.rank}"]:checked`).value;
                    const comentario = document.getElementById(`comentario_${listId}_${rec.rank}`).value;
                    return { rank: rec.rank, nota: parseInt(nota), comentario: comentario };
                });
            };

            let avaliacoes_a, avaliacoes_b;
            try {
                avaliacoes_a = extractEvals(authorData.lista_a, 'a');
                avaliacoes_b = extractEvals(authorData.lista_b, 'b');
            } catch (error) {
                alert(error.message);
                submitBtn.disabled = false;
                submitBtn.textContent = 'Salvar Avaliações';
                return; // Interrompe o envio
            }

            const payload = { author: authorName, lista_a: avaliacoes_a, lista_b: avaliacoes_b };

            const res = await fetch('/api/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                form.style.display = 'none';
                // Mostra o questionario pos-avaliacao
                surveyArea.style.display = 'block';
                surveyArea.innerHTML = surveyArea.innerHTML; // Força re-render das labels com template literals
                window.scrollTo({ top: surveyArea.offsetTop - 20, behavior: 'smooth' });
                // Atualiza cache local visual
                avaliacoes[authorName] = { lista_a: avaliacoes_a, lista_b: avaliacoes_b };
                const opt = Array.from(input.options).find(o => o.value === authorName);
                if (opt && !opt.textContent.includes('[CONCLUÍDO]')) {
                    opt.textContent = opt.textContent + ' [CONCLUÍDO]';
                }
            } else {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Salvar Avaliações';
                alert("Erro ao salvar avaliações. Por favor, tente novamente.");
            }
        });

        surveySubmitBtn.addEventListener('click', async () => {
            const fields = ['relevancia', 'diversidade', 'precisao', 'interesse', 'surpresa'];
            const nomes = ['Relevância', 'Diversidade', 'Precisão', 'Interesse', 'Surpresa'];
            const respostas = {};
            for (let i = 0; i < fields.length; i++) {
                const checked = document.querySelector(`input[name="sq_${fields[i]}"]:checked`);
                if (!checked) {
                    alert(`Por favor, responda a pergunta "${nomes[i]}" antes de enviar.`);
                    return;
                }
                respostas[fields[i]] = parseInt(checked.value);
            }

            surveySubmitBtn.disabled = true;
            surveySubmitBtn.textContent = '⏳ Enviando...';

            const surveyPayload = {
                author: input.value.trim(),
                ...respostas
            };

            const res = await fetch('/api/submit-survey', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(surveyPayload)
            });

            if (res.ok) {
                surveyArea.style.display = 'none';
                successMsg.style.display = 'block';
            } else {
                surveySubmitBtn.disabled = false;
                surveySubmitBtn.textContent = 'Enviar Questionário';
                alert('Erro ao enviar questionário. Por favor, tente novamente.');
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
        # Se for um dit com lista_a e tiver > 0
        tem_avaliacao = False
        if a["author"] in avaliacoes:
            av = avaliacoes[a["author"]]
            if isinstance(av, dict) and len(av.get("lista_a", [])) > 0:
                tem_avaliacao = True
            elif isinstance(av, list) and len(av) > 0: # formato legado
                tem_avaliacao = True

        status = "concluido" if tem_avaliacao else "pendente"
        authors.append({"name": a["author"], "status": status})
        
    # Renderizamos de forma simples com replace para evitar configurar diretório de templates complexos agora
    html = HTML_TEMPLATE
    html = html.replace("{% for author in authors %}", "")
    
    # Tratando o for loop de forma simples em Python e injetando
    options_html = ""
    for a in authors:
        status_text = " [CONCLUÍDO]" if a["status"] == "concluido" else ""
        options_html += f'<option value="{a["name"]}">{a["name"]}{status_text}</option>\n'
    
    html = HTML_TEMPLATE.split('{% for author in authors %}')[0] + options_html + HTML_TEMPLATE.split('{% endfor %}')[1]
    
    html = html.replace("{{ data_json | safe }}", json.dumps(data))
    html = html.replace("{{ avaliacoes_json | safe }}", json.dumps(avaliacoes))
    
    return HTMLResponse(content=html)

@app.post("/api/submit")
async def submit_eval(payload: AvaliacaoPayload):
    avaliacoes = await load_avaliacoes()
    existing = avaliacoes.get(payload.author, {})
    if isinstance(existing, dict):
        questionario = existing.get("questionario", None)
    else:
        questionario = None
    avaliacoes[payload.author] = {
        "lista_a": [item.dict() for item in payload.lista_a],
        "lista_b": [item.dict() for item in payload.lista_b],
        "questionario": questionario,  # preserva questionário já submetido
    }
    await save_avaliacoes(avaliacoes)
    return {"status": "success"}

@app.post("/api/submit-survey")
async def submit_survey(payload: SurveyPayload):
    avaliacoes = await load_avaliacoes()
    existing = avaliacoes.get(payload.author, {})
    if isinstance(existing, dict):
        existing["questionario"] = {
            "relevancia":   payload.relevancia,
            "diversidade":  payload.diversidade,
            "precisao":     payload.precisao,
            "interesse":    payload.interesse,
            "surpresa":     payload.surpresa,
        }
        avaliacoes[payload.author] = existing
    await save_avaliacoes(avaliacoes)
    return {"status": "success"}

if __name__ == "__main__":
    print(f"Servidor rodando em http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
