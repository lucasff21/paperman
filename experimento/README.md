# Recademy 1.0 — Artefatos do Experimento

Esta pasta congela os artefatos que sustentam os resultados relatados na dissertação
*"Recademy: Um Modelo Multifatorial para Recomendação Personalizada de Artigos Científicos"*
(PGCOMP/UFBA). Ela corresponde à versão avaliada do sistema, anterior a qualquer
substituição do motor semântico.

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `figuras/` | Figuras do Capítulo 6 (offline, ranqueamento online, percepção subjetiva) e o script `gerar_graficos.py` que as reproduz. Inclui também os gráficos usados nos slides. |
| `historico/` | Saída bruta das 16 rodadas do experimento *offline* sobre o corpus DBLP-v10, uma por arquivo. Os nomes de autor presentes aqui são de autores indexados no DBLP, ou seja, dado bibliográfico público. |
| `metricas/` | `experiment_log.json` com a configuração e as métricas de cada rodada, além das métricas agregadas por K. |
| `relatorios/` | Ferramentas de geração do relatório comparativo entre modelos. |
| `documentos/` | Dissertação, slides, formalização matemática e material de apoio. |

## Configuração do experimento avaliado

- **Offline:** corpus DBLP-v10, 49 autores, protocolo *Hold-Out* com *Candidate Injection*
  (20 títulos de treino, 10 de gabarito), janela temporal 2013 a 2017, pool médio de 45 candidatos.
- **Online:** teste A/B cego com 27 pesquisadores, recomendações pré-geradas pelo pipeline
  `gerar_recomendacoes_online.py`, candidatos recuperados via API do OpenAlex.
- **Modelos comparados:** Baseline Aleatório, Baseline Semântico, Multiplicativo e Aditivo.

## O que NÃO está nesta pasta, e por quê

### Dados pessoais dos participantes

Os arquivos abaixo existem localmente, mas **foram deliberadamente mantidos fora do
controle de versão** por conterem dados pessoais identificáveis (nome completo, ORCID,
linha de pesquisa e notas atribuídas por pessoa):

- `CANDIDATOS.xlsx`
- `candidatos_reais.json`
- `recomendacoes_online_multiplicative.json`
- `recomendacoes_online_sem_only.json`
- `resultado_avaliacao_online.json`
- `resultado_avaliacao_online.html`

A dissertação registra, na Seção 6.3.6, que o sistema coletou nome, identificador ORCID e
avaliações dos participantes sem uma política formal de privacidade alinhada à LGPD.
Enquanto essa pendência não for tratada, esses arquivos permanecem apenas em ambiente local.
Uma versão anonimizada, com os participantes identificados por códigos (`P01` a `P29`),
é o caminho previsto para eventual publicação.

### Arquivos grandes

Não versionados por excederem os limites do GitHub:

- `dblp-v10.csv` (cerca de 1,3 GB). Corpus público, disponível em
  <https://www.kaggle.com/datasets/nechbamohammed/research-papers-dataset>.
- `cbow_s100.vectors.npy` (cerca de 355 MB). Vetores Word2Vec pré-treinados.
- `data.json`, `data_apt.json`, `data_enriched.json`. Derivados intermediários, regeráveis
  a partir do corpus.

### Material de terceiros

Dissertações de outros autores usadas como referência de formatação não foram incluídas.

## Reprodução

Os gráficos do Capítulo 6 são regerados com:

```bash
python figuras/gerar_graficos.py
```

O script é autocontido: os valores das métricas estão embutidos nele, extraídos das tabelas
do experimento. Ele grava PNG em 300 dpi e PDF vetorial na própria pasta.
