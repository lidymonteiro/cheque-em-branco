#!/usr/bin/env python3
"""Coleta os vereadores da 18ª Legislatura da Câmara Municipal do Recife.

Fonte: https://e-processo.recife.pe.leg.br (API JSON pública, sem autenticação)
Os nomes de campo originais da API são preservados (para compatibilidade).
PDFs: apenas os links são mantidos (sem download).
"""
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from api import BASE, get, save

LEGISLATURE = 18
OUT = Path(__file__).resolve().parent.parent / "dados" / "18-legislatura"
BR_TZ = timezone(timedelta(hours=-3))


def now():
    return datetime.now(BR_TZ).isoformat(timespec="seconds")


def main():
    (OUT / "vereadores").mkdir(parents=True, exist_ok=True)

    # 1) Legislature 18 (metadata + list of councilmembers)
    print(f"GET /@@legislaturas/{LEGISLATURE}")
    legislature = get(f"/@@legislaturas/{LEGISLATURE}")
    save(OUT / "legislatura.json", legislature)

    items = legislature.get("items", [])
    # Deduplicate by id (the API repeats some entries)
    seen = {}
    for member in items:
        member_id = str(member.get("id"))
        if member_id not in seen:
            seen[member_id] = member
    member_ids = list(seen.keys())
    print(f"  {len(items)} entries, {len(member_ids)} distinct councilmembers")

    # 2) _index.json (deduplicated list, original API field names)
    save(OUT / "vereadores" / "_index.json", {
        "@type": "Vereadores",
        "legislatura": LEGISLATURE,
        "description": "Councilmembers of the 18th Legislature (deduplicated list)",
        "total": len(member_ids),
        "items": list(seen.values()),
    })

    # 3) Detail for each councilmember
    errors = []
    for index, member_id in enumerate(member_ids, 1):
        try:
            print(f"  [{index}/{len(member_ids)}] GET /@@vereadores/{member_id}")
            detail = get(f"/@@vereadores/{member_id}")
            save(OUT / "vereadores" / f"{member_id}.json", detail)
            time.sleep(0.3)  # be gentle with the server
        except Exception as error:
            print(f"    ERROR on {member_id}: {error}")
            errors.append({"id": member_id, "error": str(error)})

    # 4) _meta.json
    save(OUT / "_meta.json", {
        "legislatura": LEGISLATURE,
        "periodo": {"inicio": legislature.get("start"), "fim": legislature.get("end")},
        "data_eleicao": legislature.get("data_eleicao"),
        "fonte": BASE,
        "coletado_em": now(),
        "datasets": {
            "vereadores": {
                "endpoint": f"/@@legislaturas/{LEGISLATURE}",
                "entradas_brutas": len(items),
                "distintos": len(member_ids),
                "erros": errors,
            }
        },
    })
    print(f"Done. {len(member_ids) - len(errors)} profiles saved, {len(errors)} errors.")


if __name__ == "__main__":
    main()
