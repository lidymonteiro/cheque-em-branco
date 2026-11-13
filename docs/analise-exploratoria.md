# Base de dados: Câmara de Vereadores do Recife, 18ª Legislatura (2021–2024)

**Resumo técnico para avaliação de aprendizagem de máquina com grafos.**

Eleição 15/11/2020 · Mandato 01/01/2021 – 31/12/2024 · 49 vereadores (titulares + suplentes).

---

## 1. Fonte e método

- API JSON pública da Câmara (`https://e-processo.recife.pe.leg.br`), sem autenticação,
  backend Plone/waitress. Coleta em Python (`requests`), nomes de campo **originais da API**.
- **Alerta para re-coleta**: a API tem um **bug de cache** (chave = `path + page`, ignora
  `ano`/`tipo`, TTL ~20 s). Endpoints por *querystring* (`@@materias`, `@@normas`) exigem
  coleta *cache-aware* (esperar o TTL entre grupos + validar o `description`); endpoints por
  *path* são confiáveis. Já tratado nos scripts.
- PDFs (pautas, atas, textos integrais, pareceres): **só os links** foram guardados.

## 2. O que foi coletado (114 MB, ~3.500 arquivos JSON)

| Dataset                             | Volume             | Conteúdo-chave                                                                                                            |
| ----------------------------------- | ------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| **Vereadores**                | 49 perfis          | filiações (histórico partidário), mandatos, mesas, comissões, proposições, votações, frequência, votos recebidos |
| **Sessões**                  | 871                | detalhe + **votação** + **presença** por sessão                                                            |
| **Matérias** (proposições) | 53.775             | tipo, ementa, autoria, data (todos os 11 tipos, 2021–2024)                                                                |
| **Normas** (leis)             | 842 + 842 detalhes | texto, **vínculo com a matéria de origem**, vínculos norma↔norma (altera/revoga), anexos                         |
| **Comissões**                | 18                 | membros atuais + **composição histórica** (`periodos`)                                                          |

Estrutura em disco: `dados/18-legislatura/{vereadores,sessoes,materias,normas,comissoes}/`,
cada um com `_index.json` (lista) e `{id}.json` (detalhe). `_meta.json` traz a proveniência.

## 3. Características estatísticas relevantes para modelagem

**Votações** (crítico): dos 51.882 itens votados, só **606 são nominais** (com voto
individual) e destes **apenas 172 são contestados** (≥1 Não/Abstenção) — 434 são unânimes.
Distribuição dos votos individuais: **10.027 Sim / 1.370 Não / 28 Abstenção** (88% Sim).
→ *A Câmara vota de forma muito consensual; o sinal discriminativo de voto é escasso.*

**Autoria**: 99,6% das matérias têm autor único; **193 têm ≥2 autores** (coautoria).
A autoria na lista vem por **nome** (sem id) — exige reconciliação com os 49 vereadores.

**Presença**: 303 das 871 sessões têm rol nominal. `chamadaRegimental` e `ordemDia`
são **listas idênticas** (verificado) — presença é um rol único por sessão.

**Sucesso legislativo**: das 842 normas, **586 originam-se de matérias de vereadores**
(212 do Executivo, 69 institucionais); **47 dos 49** emplacaram ≥1 lei.

## 4. Modelo de grafo proposto (Knowledge Graph heterogêneo)

**Nós**: `Vereador` (49), `Partido`, `Comissao` (18), `Materia` (53.775), `Norma` (842),
`Sessao` (871), `Tema` (derivado por NLP das ementas).

**Arestas**: `AUTOR_DE` (Vereador→Materia), `RELATOU` (Vereador→Materia, favorável/contrário),
`VOTOU` (Vereador→Votacao, Sim/Não), `MEMBRO_DE` (Vereador→Comissao, cargo/período),
`FILIADO` (Vereador→Partido, datas), `VIROU_LEI` (Materia→Norma),
`VINCULA` (Norma→Norma, altera/revoga), `ATUA_EM` (Vereador→Tema).

**Features de nó `Vereador`**: partido, mandato (titular/suplente), votos recebidos,
taxa de presença, nº de autorias, nº de relatorias, nº de leis emplacadas, nº de trocas de partido.

## 5. Potencial de ML com grafos (com dimensionamento honesto)

| Técnica                                                       | Onde aplicar                                              | Observação                                             |
| -------------------------------------------------------------- | --------------------------------------------------------- | -------------------------------------------------------- |
| **Centralidade / community detection** (Louvain, Leiden) | grafos projetados vereador–vereador (49 nós)            | método principal: robusto e interpretável em N pequeno |
| **node2vec**                                             | **bipartido Vereador×Matéria** (milhares de nós) | só vale no grafo grande; em 49 nós rende pouco         |
| **Link prediction**                                      | bipartido autoria; co-votação                           | prever coautorias/afinidades                             |
| **GNN** (GraphSAGE/GCN)                                  | grafo grande com features                                 | risco de overfit se restrito aos 49 nós                 |

**Grafos já prototipados (networkx):**

- **Co-autoria** (vereador–vereador): 40 nós, 521 arestas, **densidade 0,668**, grau médio 26.
  Pares fortes: Dani Portela–Ivan Moraes (100×), Cida Pedrosa–Liana Cirne (38×). Clusters nítidos.
- **Co-ausência** (faltam juntos): sinal presente (pares reincidentes 17–22×).
- **Sucesso legislativo**: Cida Pedrosa (53 leis), Samuel Salazar (37), Liana Cirne (24)…

## 6. Perguntas de pesquisa por viabilidade (dado real)

**Tier A — dado forte:**

1. Protagonismo e **taxa de conversão matéria→lei** por autor/tema.
2. **Redes de colaboração** (co-autoria) cruzando partidos.
3. **Gatekeeping**: controle de fluxo via relatoria + presidência de comissão.
4. **Absenteísmo** × destino das matérias.
5. **Recomposição partidária** ao longo de 2021–2024 (migrações).
6. **Genealogia legislativa** (rede norma→norma; leis mais estruturantes).

**Tier B — viável com teste de robustez (os 172 votos):**
7. Bancadas reais vs. oficiais (comunidade na co-votação, com bootstrap).
8. Coesão/disciplina partidária nas votações contestadas.

**Tier C — não recomendado como pergunta central:**
9. Predição de voto individual (88% Sim → modelo trivial; dado insuficiente).
10. Recorte temático estreito (ex.: educação = 3.152 matérias, mas só 191 PLs) → estudo de caso.

## 7. Limitações que precisam ir para a metodologia

- Conclusões de **voto** limitadas a 172 votações → sempre com teste de robustez.
- Grafos projetados têm **49 nós** → preferir métodos clássicos; node2vec/GNN só no bipartido grande.
- **Comunidades são hipóteses** (validar por bootstrap), não fatos.
- Presença: base de **303 sessões** (declarar).
- Autoria reconciliada por **nome** (não há id na lista de matérias).

## 8. Próximos passos 

1. `monta_grafos.py`: construir os grafos (networkx) → exportar **GraphML** (Gephi) + JSON de
   nós/arestas (Python).
2. NLP das ementas (spaCy pt / LLM) para gerar a camada `Tema`.
3. Baseline de comunidade (Louvain) + node2vec no bipartido; comparar com partido (ARI/NMI).
4. Modelos de **diagnóstico** (não predição): o que explica dissidência / sucesso legislativo.
