# 📊 Formalização Matemática do Motor de Recomendação

Esta equação define a função de pontuação (*scoring function*) utilizada pelo sistema Paperman para avaliar um item $p$ em relação a um usuário $u$, combinando diferentes critérios ponderados:

$$Score(p, u) = Sem(p, u) + Rec(p) + Cit(p) + Qua(p)$$

---

## 📌 Interpretação dos Termos (Normalizados em [0,1])

Para que o somatório seja justo, todas as variáveis são processadas de forma a estarem na mesma escala, variando de 0.0 a 1.0:

1.  **$Sem(p, u)$** – Similaridade semântica entre o item e o usuário (média de distâncias de cosseno via Word2Vec das palavras-chave).
2.  **$Rec(p)$** – Recência do item (calculada através da normalização temporal Min-Max nos filtros estabelecidos como estado da arte).
3.  **$Cit(p)$** – Número de citações (Impacto científico log-normalizado por probabilidade temporal, isto é, por seus anos de vida).
4.  **$Qua(p)$** – Qualidade do item (Representado pelo ranking Qualis da publicação, mapeado linearmente para valores de 1.0 a 0.0).

---

## ⚙️ O Modelo de Somatório Estrito

Optou-se pela utilização de um algoritmo de **soma simples** em vez do clássico paradigma de pesos arbitrários ajustados sem Grid-Search ou testes estressados pelo Machine Learning. 

Dado que os quatro alicerces formativos já passam pelos respectivos tratamentos de escala linear ou logarítmica (o teto absoluto da similaridade é 1.0, assim como o do Qualis A1 é 1.0), uma publicação impecável em todos os quesitos obeteria um $Score$ teórico perfeito de **4.0**.

Desta forma, os resultados em bancas e avaliações experimentais tornam-se inquestionáveis, blindando a pesquisa contra discussões referentes à imposição enviesada da preferência humana frente a fatores metodológicos puros.
