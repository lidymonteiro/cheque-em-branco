#!/usr/bin/env python3
"""Coleta as comissões da Câmara do Recife, com composição histórica (periodos).

Fonte: https://e-processo.recife.pe.leg.br (API JSON pública, sem autenticação)
Endpoints por path (confiáveis). Coleta a lista e o detalhe de cada comissão
(membros atuais + períodos históricos, úteis para recortar a 18ª Legislatura).
Nomes de campo originais da API preservados. PDFs: apenas os links.
"""
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from api import get, save

OUT = Path(__file__).resolve().parent.parent / "dados" / "18-legislatura"
COM_DIR = OUT / "comissoes"
BR_TZ = timezone(timedelta(hours=-3))


def now():
    return datetime.now(BR_TZ).isoformat(timespec="seconds")


def main():
    COM_DIR.mkdir(parents=True, exist_ok=True)

    lista = get("/@@comissoes")
    save(COM_DIR / "_index.json", lista)
    items = lista.get("items", [])
    print(f"{len(items)} comissões")

    errors = []
    for i, item in enumerate(items, 1):
        cid = str(item.get("id"))
        print(f"  [{i}/{len(items)}] GET /@@comissoes/{cid}")
        try:
            save(COM_DIR / f"{cid}.json", get(f"/@@comissoes/{cid}"))
            time.sleep(0.2)
        except Exception as error:
            print(f"    ERROR {cid}: {error}")
            errors.append({"id": cid, "error": str(error)})

    meta_path = OUT / "_meta.json"
    meta = {}
    if meta_path.exists():
        import json
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.setdefault("datasets", {})["comissoes"] = {
        "endpoint": "/@@comissoes/{id}",
        "total": len(items),
        "erros": errors,
        "coletado_em": now(),
    }
    save(meta_path, meta)
    print(f"Done. {len(items)} comissões, {len(errors)} erros.")


if __name__ == "__main__":
    main()
