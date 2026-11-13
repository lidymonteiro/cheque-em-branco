#!/usr/bin/env python3
"""Coleta as sessões plenárias da 18ª Legislatura (2021–2024) da Câmara do Recife.

Fonte: https://e-processo.recife.pe.leg.br (API JSON pública, sem autenticação)
Endpoints por path (confiáveis; não sofrem o bug de cache por querystring).
Para cada sessão coleta: detalhe, votação nominal e presença.
Os nomes de campo originais da API são preservados. PDFs: apenas os links.
"""
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from api import BASE, get, save

YEARS = (2021, 2022, 2023, 2024)
OUT = Path(__file__).resolve().parent.parent / "dados" / "18-legislatura"
SESS_DIR = OUT / "sessoes"
BR_TZ = timezone(timedelta(hours=-3))


def now():
    return datetime.now(BR_TZ).isoformat(timespec="seconds")


def discover_types():
    """Return the list of session types [(id, title), ...]."""
    data = get("/@@sessoes")
    return [(t.get("id"), t.get("title")) for t in data.get("filtros", {}).get("tipo", [])]


def main():
    SESS_DIR.mkdir(parents=True, exist_ok=True)
    types = discover_types()
    print(f"{len(types)} session types, years {YEARS}")

    # 1) Collect the session lists (one path per type/year)
    index = []
    for type_id, type_title in types:
        for year in YEARS:
            path = f"/@@sessoes/tipo/{type_id}/ano/{year}"
            data = get(path)
            items = data.get("items", [])
            if items:
                print(f"  tipo={type_id} ({type_title.strip()}) ano={year}: {len(items)} sessões")
            for item in items:
                item["_tipo_id"] = type_id
                item["_ano"] = year
                index.append(item)
            time.sleep(0.2)

    save(SESS_DIR / "_index.json", {
        "@type": "SessoesPlenarias",
        "legislatura": 18,
        "description": "Sessões plenárias da 18ª Legislatura (2021-2024)",
        "total": len(index),
        "items": index,
    })
    print(f"Total de sessões: {len(index)}")

    # 2) Detail + votacao + presenca for each session
    errors = []
    for i, item in enumerate(index, 1):
        sid = str(item.get("id"))
        print(f"  [{i}/{len(index)}] sessão {sid}")
        for suffix, fname in (("", f"{sid}.json"),
                              ("/votacao", f"{sid}_votacao.json"),
                              ("/presenca", f"{sid}_presenca.json")):
            target = SESS_DIR / fname
            if target.exists():
                continue  # resumable: skip already-collected files
            try:
                data = get(f"/@@sessoes/id/{sid}{suffix}")
                save(target, data)
                time.sleep(0.2)
            except Exception as error:
                print(f"    ERROR {sid}{suffix}: {error}")
                errors.append({"id": sid, "suffix": suffix, "error": str(error)})

    # 3) Update _meta.json with the sessoes dataset
    meta_path = OUT / "_meta.json"
    meta = {}
    if meta_path.exists():
        import json
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.setdefault("datasets", {})["sessoes"] = {
        "endpoint": "/@@sessoes/tipo/{t}/ano/{a} (+ /id/{id}/votacao, /presenca)",
        "anos": list(YEARS),
        "total_sessoes": len(index),
        "erros": errors,
        "coletado_em": now(),
    }
    save(meta_path, meta)
    print(f"Done. {len(index)} sessões, {len(errors)} erros.")


if __name__ == "__main__":
    main()
