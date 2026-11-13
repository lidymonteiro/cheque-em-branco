# Cheque em Branco: Raio-X da Câmara de Vereadores do Recife

Módulo de **jurimetria e grafos** da plataforma cívica *Cheque em Branco*, cujo objetivo é
permitir que a população acompanhe como os vereadores que elegeu de fato atuaram e votaram.

Esta parte coleta e analisa os **dados abertos da 18ª Legislatura** da Câmara Municipal do
Recife (eleição 15/11/2020, mandato 01/01/2021 – 31/12/2024) e explora o uso de
**aprendizagem de máquina com grafos** sobre eles.

## Fonte dos dados

API JSON pública da Câmara (`https://e-processo.recife.pe.leg.br`), sem autenticação.
A documentação oficial de cada endpoint está em [`docs/api/`](docs/api/) (arquivos `.odt`).

> ⚠️ **Bug de cache da API**: endpoints por *querystring* (`@@materias`, `@@normas`) têm um
> cache do servidor que ignora os parâmetros `ano`/`tipo` (chave = `path + page`, TTL ~20 s).
> A coleta desses endpoints é *cache-aware* (espera o TTL + valida o `description`). Endpoints
> por *path* são confiáveis. Detalhes em [`docs/plano-grafos.md`](docs/plano-grafos.md).

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install requests
```

Os scripts usam apenas `requests` (o resto é biblioteca padrão). 

## Como rodar a coleta

Da raiz do projeto, com a venv ativa (ou usando `venv/bin/python`):

```bash
python scripts/coleta_vereadores.py       # 49 vereadores + perfis completos
python scripts/coleta_sessoes.py          # 871 sessões + votação + presença
python scripts/coleta_materias.py         # 53.775 matérias (cache-aware, ~20 min)
python scripts/coleta_normas.py           # 842 normas (cache-aware)
python scripts/coleta_normas_detalhe.py   # detalhe das normas (vínculo matéria->lei)
python scripts/coleta_comissoes.py        # 18 comissões (composição histórica)
python scripts/medir_eixos.py             # medições de viabilidade (lê só arquivos locais)
```

- [`scripts/api.py`](scripts/api.py) — cliente HTTP compartilhado (`requests` com retry/timeout).
- Os coletores de sessões e normas-detalhe são **resumíveis** (pulam arquivos já salvos).
- Os nomes de campo são **os originais da API** (compatibilidade). PDFs: só os links.

## Estrutura dos dados

```
dados/18-legislatura/
├── _meta.json                 # proveniência da coleta
├── legislatura.json
├── vereadores/   _index.json + {id}.json
├── sessoes/      _index.json + {id}.json, {id}_votacao.json, {id}_presenca.json
├── materias/     _index.json
├── normas/       _index.json + detalhe/{id}.json
└── comissoes/    _index.json + {id}.json
```

| Dataset                         | Volume    |
| ------------------------------- | --------- |
| Vereadores                      | 49 perfis |
| Sessões (+votação+presença) | 871       |
| Matérias (todos os tipos)      | 53.775    |
| Normas (lista + detalhe)        | 842       |
| Comissões (com períodos)      | 18        |

## Achados principais (já medidos)

- **Votação**: só 606 das 51.882 votações são nominais; **172 contestadas** (88% dos votos são "Sim").
- **Co-autoria**: 193 matérias com ≥2 autores → grafo denso (40 nós, densidade 0,668).
- **Sucesso legislativo**: 586 leis originadas de matérias de vereadores; 47/49 emplacaram ≥1.
- **Presença**: 303 sessões com rol nominal.

## Documentação

- [`docs/plano-grafos.md`](docs/plano-grafos.md) — modelo de grafo, eixos, plano de ML.
- [`docs/resumo-para-cientista-de-dados.md`](docs/resumo-para-cientista-de-dados.md) — resumo técnico da base e do potencial de ML.
- [`docs/api/`](docs/api/) — documentação oficial dos endpoints.

## Status

Coleta completa. Próximos passos: `monta_grafos.py` (networkx → GraphML/JSON) e a camada de
ML (community detection, node2vec no bipartido de autoria), ver o plano de grafos.
