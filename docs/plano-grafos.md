# Plano de montagem dos grafos: 18ª Legislatura (Recife, 2021–2024)

> Documento de projeto. Define o modelo de grafo, as features,
> os grafos a construir, o tratamento de presença e a etapa de medição de
> viabilidade dos eixos. Escrito a partir dos dados **já coletados** em
> `dados/18-legislatura/`.

## 0. Restrições reais do dado (carregar sempre)

- **Votação nominal é rara**: 606 votações com voto individual de 51.882 itens votados;
  destas, só **172 são contestadas** (≥1 Não/Abstenção). 88% dos votos são "Sim".
  → O voto é **camada secundária**, nunca o alicerce das conclusões.
- **Presença**: 303 das 871 sessões têm presença nominal, em **dois momentos**
  (`chamadaRegimental` e `ordemDia`), com justificativa. Dado forte.
- **Lista de matérias/normas** veio por coleta **cache-aware** (bug de cache do servidor;
  ver `memory/recife-api-cache-bug.md`). Nível lista; detalhe por id é sob demanda.
- **Nós pequenos**: 49 vereadores. Métodos clássicos (centralidade, Louvain) nos grafos
  projetados; node2vec só no bipartido grande (autoria).

## 1. Modelo de grafo (Knowledge Graph heterogêneo)

### Nós

| Tipo         | Chave         | Fonte                                            |
| ------------ | ------------- | ------------------------------------------------ |
| `Vereador` | id            | `vereadores/{id}.json`                         |
| `Partido`  | sigla (token) | filiações                                      |
| `Comissao` | id            | `comissoes/{id}.json`                          |
| `Materia`  | id            | `materias/_index.json` (+ detalhe sob demanda) |
| `Norma`    | id            | `normas/_index.json`                           |
| `Sessao`   | id            | `sessoes/{id}.json`                            |
| `Tema`     | slug          | derivado por NLP das ementas                     |

### Features de nó `Vereador`

- Mandato (natureza Titular/Suplente, datas), nº de legislaturas, votos recebidos.
- **Taxa de presença** (chamada e ordem do dia, separadas) — ver §3.
- **Taxa de esvaziamento** (presente na chamada, ausente na ordem do dia) — ver §3.
- Nº de matérias de autoria, nº de relatorias, taxa de conversão autoria→lei.
- Nº de trocas de partido; nº de cargos em comissão/mesa.

### Arestas

| Aresta        | De → Para           | Atributos                        | Fonte                                                                     |
| ------------- | -------------------- | -------------------------------- | ------------------------------------------------------------------------- |
| `AUTOR_DE`  | Vereador → Materia  | primeiro_autor                   | matérias `authorship` (casar por **nome**: a lista não traz id) |
| `RELATOU`   | Vereador → Materia  | parecer favorável/contrário    | detalhe matéria / comissões                                             |
| `VOTOU`     | Vereador → Votacao  | voto (Sim/Não/Abst.), data      | sessões `/votacao`                                                     |
| `MEMBRO_DE` | Vereador → Comissao | cargo, período                  | comissões `periodos`                                                   |
| `FILIADO`   | Vereador → Partido  | data_filiacao, data_desfiliacao  | filiações                                                               |
| `VIROU_LEI` | Materia → Norma     | —                               | normas `materia`                                                        |
| `VINCULA`   | Norma → Norma       | tipo_vinculo (altera/revoga/...) | normas `normas_vinculadas`                                              |
| `ATUA_EM`   | Vereador → Tema     | peso (nº matérias)             | NLP sobre ementas                                                         |

## 2. Grafos a construir (por eixo)

**Eixo 1 — Colaboração**

- G3 **Co-autoria** (Vereador–Vereador, peso = coassinaturas) → comunidades (Louvain/Leiden) + bootstrap.
- G4 **Bipartido Autoria** (Vereador×Materia) → **node2vec** + clustering temático.

**Eixo 2 — Poder / fluxo**

- G5 **Co-comissão** (Vereador–Vereador via comissão/período).
- G6 **Relatoria/gatekeeping** (Vereador→Materia com parecer) → centralidade de controle.

**Eixo 3 — Resultado**

- G9 **Matéria→Norma** (sucesso legislativo) + G4 → taxa de conversão por autor/tema.
- G8 **Genealogia de normas** (Norma→Norma: altera/revoga) → leis estruturantes.

**Camada secundária — Voto** (com ressalva dos 172)

- G1 **Co-votação** (concordância) → validação cruzada dos blocos de colaboração.

## 3. Presença (incluído conforme decidido)

1. **Feature de nó**: taxa de presença por vereador sobre as 303 sessões com dado nominal.
2. ~~**Esvaziamento estratégico**~~ — **DESCARTADO**. Verificado nas 303 sessões: a API
   registra **lista idêntica** em `chamadaRegimental` e `ordemDia` (0 casos de divergência).
   Os dois momentos são redundantes; presença é um rol único por sessão, não duas aferições.
3. **Grafo de CO-AUSÊNCIA** (não co-presença): Vereador–Vereador, peso = nº de sessões
   em que **ambos faltaram** (normalizado). Co-presença é quase completa → descartada como grafo.
4. **Absenteísmo × destino da matéria**: cruzar presença na ordem do dia com o resultado
   das votações e a tramitação (arquivado/aprovado).
5. **Ranking cívico**: assiduidade, % de faltas justificadas vs. não, evolução 2021–2024
   (testar queda em 2024, ano eleitoral).

**Reconciliação de nomes**: agregar sempre por `id` do vereador, nunca por `title`
(há variações de nome de exibição na presença). Casar com a lista dos 49 de
`vereadores/_index.json` antes de qualquer agregação.

## 4. Etapa de medição de viabilidade (rodar quando a coleta fechar)

Script `scripts/medir_eixos.py` deve reportar:

- **Eixo 1**: nº de matérias com ≥2 autores; densidade e grau médio do grafo de co-autoria.
- **Eixo 3**: nº de matérias que viraram norma (via `VIROU_LEI`); taxa de conversão global.
- **Educação**: nº de matérias cuja ementa casa termos de educação; destas, quantas
  viraram lei e quantas têm voto nominal **contestado**. Decide se "educação" é eixo ou estudo de caso.
- **Presença**: distribuição das taxas de presença e de esvaziamento; nº de pares com co-ausência relevante.

Esses números confirmam qual eixo sustenta as conclusões centrais.

## 5. Ferramentas

- Construção/análise: `networkx`; comunidades: `python-igraph` + `leidenalg`.
- Embeddings: `node2vec`/`pecanpy` (só no G4); viz/clustering: `scikit-learn` + `umap-learn`.
- NLP de temas: `spaCy` (pt) e/ou LLM para rotular clusters de ementas.
- Exploração visual: exportar `.graphml`/`.gexf` para o Gephi.
- Persistência: Neo4j (o modelo de §1 mapeia direto).

## 6. Caveats que vão para a metodologia 

- Conclusões de voto limitadas a 172 votações contestadas → sempre com teste de robustez.
- Clusters/comunidades são hipóteses, validadas por bootstrap, não fatos.
- Presença: base de 303 sessões (declarar explicitamente).
- Sem predição de voto individual (dado insuficiente); trocar por diagnóstico retrospectivo.
