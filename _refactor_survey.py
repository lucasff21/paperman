import os

file_path = 'offline_evaluation/evaluation_app.py'
with open(file_path, 'r', encoding='utf-8', errors='surrogatepass') as f:
    content = f.read()

# 1. Models
old_models = '''class AvaliacaoPayload(BaseModel):
    author: str
    lista_a: List[AvaliacaoItem]
    lista_b: List[AvaliacaoItem]

class SurveyPayload(BaseModel):
    author: str
    relevancia: int
    diversidade: int
    precisao: int
    atualidade: int
    surpresa: int'''

new_models = '''class SurveyAnswers(BaseModel):
    relevancia: int
    diversidade: int
    precisao: int
    atualidade: int
    surpresa: int

class AvaliacaoPayload(BaseModel):
    author: str
    lista_a: List[AvaliacaoItem]
    lista_b: List[AvaliacaoItem]
    survey_a: Optional[SurveyAnswers] = None
    survey_b: Optional[SurveyAnswers] = None'''

content = content.replace(old_models, new_models)

# 2. HTML body
old_html = '''            <form id="eval-form">
                <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px;">Lista B</h2>
                <div id="papers-container-b"></div>

                <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px; margin-top: 40px;">Lista A</h2>
                <div id="papers-container-a"></div>
                
                <button type="submit" class="submit-btn" style="margin-top: 30px;">Salvar Avaliações</button>
            </form>
            <div id="success-msg">Avaliações salvas com sucesso! Muito obrigado pela participação.</div>

            <!-- Questionário pós-avaliação -->
            <div id="survey-area" style="display:none; margin-top:30px;">
                <div id="survey-questions-container"></div>
                <button id="survey-submit-btn" style="width:100%; padding:15px; font-size:18px; background:#27ae60; color:white; border:none; border-radius:6px; cursor:pointer; margin-top:10px;">Enviar Questionário</button>
            </div>'''

new_html = '''            <form id="eval-form">
                <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px;">Lista B</h2>
                <div id="papers-container-b"></div>
                <div id="survey-container-b"></div>

                <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px; margin-top: 40px;">Lista A</h2>
                <div id="papers-container-a"></div>
                <div id="survey-container-a"></div>
                
                <button type="submit" class="submit-btn" style="margin-top: 30px;">Salvar Avaliações e Questionários</button>
            </form>
            <div id="success-msg">Avaliações salvas com sucesso! Muito obrigado pela participação.</div>'''

content = content.replace(old_html, new_html)

# 3. JS Vars and renderSurvey
old_js1 = '''        const surveyArea = document.getElementById('survey-area');
        const surveySubmitBtn = document.getElementById('survey-submit-btn');

        function renderSurvey() {
            const questions = [
                { id: 'relevancia', title: '1. Relev\u00e2ncia', desc: 'Os artigos recomendados s\u00e3o relevantes para meus interesses de pesquisa ou para o tema investigado.' },
                { id: 'diversidade', title: '2. Diversidade', desc: 'As recomenda\u00e7\u00f5es abordaram diferentes perspectivas, sub\u00e1reas ou abordagens dentro do meu tema de pesquisa.' },
                { id: 'precisao', title: '3. Precis\u00e3o', desc: 'As recomenda\u00e7\u00f5es correspondem com precis\u00e3o ao assunto ou contexto de busca informado.' },
                { id: 'atualidade', title: '4. Atualidade', desc: 'Os artigos recomendados refletem publica\u00e7\u00f5es recentes ou abordagens atualizadas sobre o tema.' },
                { id: 'surpresa', title: '5. Surpresa (Serendipidade)', desc: 'As recomenda\u00e7\u00f5es apresentaram artigos inesperados, mas que ainda assim se mostraram \u00fateis ou potencialmente valiosos para minha pesquisa.' },
            ];
            const container = document.getElementById('survey-questions-container');
            container.innerHTML = `
                <h2 style="color:#2c3e50; border-top:2px solid #eee; padding-top:30px; margin-top:10px;">&#x1F4CB; Question\u00e1rio Final</h2>
                <p style="color:#555; margin-bottom:24px;">Avalie o sistema de recomenda\u00e7\u00e3o como um todo (1 = Discordo totalmente, 5 = Concordo totalmente).</p>
            `;
            questions.forEach(q => {
                const div = document.createElement('div');
                div.className = 'survey-question';
                const likertHtml = [1,2,3,4,5].map(n =>
                    `<input type="radio" name="sq_${q.id}" id="sq_${q.id}_${n}" value="${n}"><label for="sq_${q.id}_${n}">${n}</label>`
                ).join('');
                div.innerHTML = `
                    <p class="q-title">${q.title}</p>
                    <p class="q-desc">${q.desc}</p>
                    <div class="likert-group">${likertHtml}</div>
                `;
                container.appendChild(div);
            });
        }'''

new_js1 = '''        function renderSurvey(containerId, listId, listName, savedEvals) {
            const questions = [
                { id: 'relevancia', title: '1. Relev\u00e2ncia', desc: 'Os artigos recomendados s\u00e3o relevantes para meus interesses de pesquisa ou para o tema investigado.' },
                { id: 'diversidade', title: '2. Diversidade', desc: 'As recomenda\u00e7\u00f5es abordaram diferentes perspectivas, sub\u00e1reas ou abordagens dentro do meu tema de pesquisa.' },
                { id: 'precisao', title: '3. Precis\u00e3o', desc: 'As recomenda\u00e7\u00f5es correspondem com precis\u00e3o ao assunto ou contexto de busca informado.' },
                { id: 'atualidade', title: '4. Atualidade', desc: 'Os artigos recomendados refletem publica\u00e7\u00f5es recentes ou abordagens atualizadas sobre o tema.' },
                { id: 'surpresa', title: '5. Surpresa (Serendipidade)', desc: 'As recomenda\u00e7\u00f5es apresentaram artigos inesperados, mas que ainda assim se mostraram \u00fateis ou potencialmente valiosos para minha pesquisa.' },
            ];
            const container = document.getElementById(containerId);
            container.innerHTML = `
                <div style="background:#f8f9fa; border:1px solid #ddd; padding:20px; border-radius:8px; margin-top:20px; margin-bottom: 40px;">
                    <h3 style="color:#2c3e50; margin-top:0;">&#x1F4CB; Question\u00e1rio sobre a ${listName}</h3>
                    <p style="color:#555; margin-bottom:24px;">Avalie o conjunto de recomenda\u00e7\u00f5es da ${listName} (1 = Discordo totalmente, 5 = Concordo totalmente).</p>
                    <div class="questions-wrapper"></div>
                </div>
            `;
            const wrapper = container.querySelector('.questions-wrapper');
            questions.forEach(q => {
                const div = document.createElement('div');
                div.className = 'survey-question';
                div.style.marginBottom = '15px';
                
                const savedVal = savedEvals ? savedEvals[q.id] : null;
                
                const likertHtml = [1,2,3,4,5].map(n =>
                    `<input type="radio" name="sq_${listId}_${q.id}" id="sq_${listId}_${q.id}_${n}" value="${n}" ${savedVal == n ? 'checked' : ''}><label for="sq_${listId}_${q.id}_${n}">${n}</label>`
                ).join('');
                div.innerHTML = `
                    <p class="q-title" style="font-weight:bold; margin-bottom:5px;">${q.title}</p>
                    <p class="q-desc" style="font-size:13px; color:#666; margin-bottom:10px;">${q.desc}</p>
                    <div class="likert-group">${likertHtml}</div>
                `;
                wrapper.appendChild(div);
            });
        }'''

content = content.replace(old_js1, new_js1)


# 4. JS Author Change
old_js2 = '''            const savedListaA = Array.isArray(savedData) ? [] : (savedData.lista_a || []);
            const savedListaB = Array.isArray(savedData) ? [] : (savedData.lista_b || []);

            baseTitle.textContent = authorData.base_title;
            
            renderList(papersContainerA, authorData.lista_a, 'a', savedListaA);
            renderList(papersContainerB, authorData.lista_b, 'b', savedListaB);

            evalArea.classList.remove('hidden');'''

new_js2 = '''            const savedListaA = Array.isArray(savedData) ? [] : (savedData.lista_a || []);
            const savedListaB = Array.isArray(savedData) ? [] : (savedData.lista_b || []);
            const savedSurveyA = Array.isArray(savedData) ? null : (savedData.survey_a || null);
            const savedSurveyB = Array.isArray(savedData) ? null : (savedData.survey_b || null);

            baseTitle.textContent = authorData.base_title;
            
            renderList(papersContainerB, authorData.lista_b, 'b', savedListaB);
            renderSurvey('survey-container-b', 'b', 'Lista B', savedSurveyB);

            renderList(papersContainerA, authorData.lista_a, 'a', savedListaA);
            renderSurvey('survey-container-a', 'a', 'Lista A', savedSurveyA);

            evalArea.classList.remove('hidden');'''

content = content.replace(old_js2, new_js2)


# 5. JS Form Submit

old_js3_start = '''            let avaliacoes_a, avaliacoes_b;
            try {
                avaliacoes_a = extractEvals(authorData.lista_a, 'a');
                avaliacoes_b = extractEvals(authorData.lista_b, 'b');
            } catch (error) {'''

old_js3_mid = '''            }

            const payload = { author: authorName, lista_a: avaliacoes_a, lista_b: avaliacoes_b };

            const res = await fetch('/api/submit', {'''

old_js3_end = '''            if (res.ok) {
                form.style.display = 'none';
                // Renderiza e exibe o questionário pós-avaliação
                renderSurvey();
                surveyArea.style.display = 'block';
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
            const fields = ['relevancia', 'diversidade', 'precisao', 'atualidade', 'surpresa'];
            const nomes = ['Relevância', 'Diversidade', 'Precisão', 'Atualidade', 'Surpresa'];
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
                window.scrollTo({ top: 0, behavior: 'smooth' });
            } else {
                surveySubmitBtn.disabled = false;
                surveySubmitBtn.textContent = 'Enviar Questionário';
                alert("Erro ao salvar o questionário. Por favor, tente novamente.");
            }
        });'''

import re
pattern = re.compile(re.escape(old_js3_start) + r'.*?' + re.escape(old_js3_end), re.DOTALL)

new_js3 = '''            const extractSurvey = (listId, listName) => {
                const fields = ['relevancia', 'diversidade', 'precisao', 'atualidade', 'surpresa'];
                const nomes = ['Relevância', 'Diversidade', 'Precisão', 'Atualidade', 'Surpresa'];
                const respostas = {};
                for (let i = 0; i < fields.length; i++) {
                    const checked = document.querySelector(`input[name="sq_${listId}_${fields[i]}"]:checked`);
                    if (!checked) {
                        throw new Error(`Por favor, responda a pergunta "${nomes[i]}" do questionário da ${listName} antes de enviar.`);
                    }
                    respostas[fields[i]] = parseInt(checked.value);
                }
                return respostas;
            };

            let avaliacoes_a, avaliacoes_b, survey_a, survey_b;
            try {
                avaliacoes_b = extractEvals(authorData.lista_b, 'b');
                survey_b = extractSurvey('b', 'Lista B');
                
                avaliacoes_a = extractEvals(authorData.lista_a, 'a');
                survey_a = extractSurvey('a', 'Lista A');
            } catch (error) {
                alert(error.message);
                submitBtn.disabled = false;
                submitBtn.textContent = 'Salvar Avaliações e Questionários';
                return;
            }

            const payload = { 
                author: authorName, 
                lista_a: avaliacoes_a, 
                lista_b: avaliacoes_b,
                survey_a: survey_a,
                survey_b: survey_b
            };

            const res = await fetch('/api/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                form.style.display = 'none';
                successMsg.style.display = 'block';
                window.scrollTo({ top: 0, behavior: 'smooth' });
                avaliacoes[authorName] = { lista_a: avaliacoes_a, lista_b: avaliacoes_b, survey_a: survey_a, survey_b: survey_b };
                const opt = Array.from(input.options).find(o => o.value === authorName);
                if (opt && !opt.textContent.includes('[CONCLUÍDO]')) {
                    opt.textContent = opt.textContent + ' [CONCLUÍDO]';
                }
            } else {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Salvar Avaliações e Questionários';
                alert("Erro ao salvar avaliações. Por favor, tente novamente.");
            }
        });'''

content = pattern.sub(new_js3, content)

# 6. Python endpoints
old_py_endpoints = '''@app.post("/api/submit")
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
            "atualidade":    payload.atualidade,
            "surpresa":     payload.surpresa,
        }
        avaliacoes[payload.author] = existing
    await save_avaliacoes(avaliacoes)
    return {"status": "success"}'''

new_py_endpoints = '''@app.post("/api/submit")
async def submit_eval(payload: AvaliacaoPayload):
    avaliacoes = await load_avaliacoes()
    
    survey_a_dict = payload.survey_a.dict() if payload.survey_a else None
    survey_b_dict = payload.survey_b.dict() if payload.survey_b else None
    
    avaliacoes[payload.author] = {
        "lista_a": [item.dict() for item in payload.lista_a],
        "lista_b": [item.dict() for item in payload.lista_b],
        "survey_a": survey_a_dict,
        "survey_b": survey_b_dict,
    }
    await save_avaliacoes(avaliacoes)
    return {"status": "success"}'''

content = content.replace(old_py_endpoints, new_py_endpoints)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Substituição completa.")
