#!/usr/bin/env python3
"""Coleta as matérias legislativas da 18ª Legislatura (2021–2024), todos os tipos.

Fonte: https://e-processo.recife.pe.leg.br (API JSON pública, sem autenticação)

A lista `/@@materias?ano=&tipo=` sofre um bug de cache do servidor: a chave é
(path + page), ignorando ano/tipo, com TTL ~20s. Em cache MISS o backend calcula
com o ano/tipo corretos; em HIT devolve o blob anterior. Estratégia cache-aware:
antes de cada grupo (ano, tipo) espera-se o TTL expirar, garantindo que cada página
seja um MISS calculado com o filtro certo. Cada página é validada pelo `description`;
se não bater, espera e tenta de novo.

Nível coletado: LISTA (todos os tipos). O detalhe por id (/@@materias/{id}) é
path-based e pode ser coletado à parte, sob demanda.
Nomes de campo originais da API preservados. PDFs: apenas os links.
"""
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from api import get, save

YEARS = (2021, 2022, 2023, 2024)
OUT = Path(__file__).resolve().parent.parent / "dados" / "18-legislatura"
MAT_DIR = OUT / "materias"
BR_TZ = timezone(timedelta(hours=-3))

CACHE_TTL = 23      # segundos de espera antes de cada grupo (TTL do cache ~20s)
PAGE_PAUSE = 0.3    # pausa entre páginas de um mesmo grupo
MAX_RETRY = 4       # tentativas quando a página volta com cache errado


def now():
    return datetime.now(BR_TZ).isoformat(timespec="seconds")


def discover_types():
    """Return {type_id: title} available for matérias."""
    data = get("/@@materias")
    return {t.get("id"): t.get("title") for t in data.get("filtros", {}).get("tipo", [])}


def fetch_page(year, type_id, page, expected_desc):
    """Fetch one page, retrying until the response matches the expected filter."""
    for attempt in range(MAX_RETRY):
        data = get(f"/@@materias?ano={year}&tipo={type_id}&page={page}")
        if data.get("description") == expected_desc:
            return data
        # cache miss failed to refresh with our filter: wait the TTL and retry
        time.sleep(CACHE_TTL)
    raise RuntimeError(
        f"cache nao refrescou para ano={year} tipo={type_id} page={page}: "
        f"desc={data.get('description')!r} (esperado {expected_desc!r})"
    )


def collect_group(year, type_id, title):
    """Collect every page of one (year, type) group. Returns the list of items."""
    expected_desc = f"Lista de {title} do ano de {year}"
    time.sleep(CACHE_TTL)  # deixa as chaves de página do grupo anterior expirarem

    first = fetch_page(year, type_id, 1, expected_desc)
    pagination = first.get("pagination", {})
    page_count = pagination.get("page_count", 1)
    total = pagination.get("total", len(first.get("items", [])))
    items = list(first.get("items", []))

    for page in range(2, page_count + 1):
        time.sleep(PAGE_PAUSE)
        data = fetch_page(year, type_id, page, expected_desc)
        items.extend(data.get("items", []))

    return items, total


def main():
    MAT_DIR.mkdir(parents=True, exist_ok=True)
    types = discover_types()
    print(f"{len(types)} tipos, anos {YEARS} -> {len(types) * len(YEARS)} grupos")

    index = []
    summary = {}
    errors = []
    group_num = 0
    n_groups = len(types) * len(YEARS)
    for type_id, title in types.items():
        for year in YEARS:
            group_num += 1
            label = f"[{group_num}/{n_groups}] ano={year} tipo={type_id} ({title})"
            try:
                items, total = collect_group(year, type_id, title)
                for it in items:
                    it["_tipo_id"] = type_id
                    it["_ano"] = year
                index.extend(items)
                summary[f"{title}/{year}"] = {"coletados": len(items), "total_api": total}
                print(f"  {label}: {len(items)} (total API {total})")
            except Exception as error:
                print(f"  {label}: ERRO {error}")
                errors.append({"ano": year, "tipo": type_id, "error": str(error)})

    save(MAT_DIR / "_index.json", {
        "@type": "Materias",
        "legislatura": 18,
        "description": "Matérias legislativas da 18ª Legislatura (2021-2024), todos os tipos",
        "total": len(index),
        "items": index,
    })

    # Atualiza _meta.json
    meta_path = OUT / "_meta.json"
    meta = {}
    if meta_path.exists():
        import json
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.setdefault("datasets", {})["materias"] = {
        "endpoint": "/@@materias?ano=&tipo= (cache-aware)",
        "nivel": "lista",
        "anos": list(YEARS),
        "total": len(index),
        "por_grupo": summary,
        "erros": errors,
        "coletado_em": now(),
    }
    save(meta_path, meta)
    print(f"Done. {len(index)} matérias, {len(errors)} grupos com erro.")


if __name__ == "__main__":
    main()
