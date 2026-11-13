#!/usr/bin/env python3
"""Coleta o DETALHE de cada norma (/@@normas/{id}), path-based.

Fonte: https://e-processo.recife.pe.leg.br (API JSON pública, sem autenticação)
O detalhe traz o vínculo com a matéria de origem (`materia`), os vínculos entre
normas (`normas_vinculadas`: altera/revoga/regulamenta) e anexos — base para o
Eixo 3 (taxa de conversão matéria->lei) e a genealogia de normas.
Resumível: pula arquivos já salvos. Nomes de campo originais. PDFs: só links.
"""
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from api import get, save

OUT = Path(__file__).resolve().parent.parent / "dados" / "18-legislatura"
NORM_DIR = OUT / "normas"
DET_DIR = NORM_DIR / "detalhe"
BR_TZ = timezone(timedelta(hours=-3))


def now():
    return datetime.now(BR_TZ).isoformat(timespec="seconds")


def main():
    import json
    DET_DIR.mkdir(parents=True, exist_ok=True)
    index = json.loads((NORM_DIR / "_index.json").read_text(encoding="utf-8"))
    ids = [str(it.get("id")) for it in index.get("items", [])]
    print(f"{len(ids)} normas para detalhar")

    errors = []
    for i, nid in enumerate(ids, 1):
        target = DET_DIR / f"{nid}.json"
        if target.exists():
            continue
        if i % 50 == 0:
            print(f"  [{i}/{len(ids)}]")
        try:
            save(target, get(f"/@@normas/{nid}"))
            time.sleep(0.2)
        except Exception as error:
            print(f"    ERROR {nid}: {error}")
            errors.append({"id": nid, "error": str(error)})

    meta_path = OUT / "_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta.setdefault("datasets", {}).setdefault("normas", {})["detalhe"] = {
        "endpoint": "/@@normas/{id}",
        "total": len(ids),
        "erros": errors,
        "coletado_em": now(),
    }
    save(meta_path, meta)
    print(f"Done. {len(ids) - len(errors)} detalhes, {len(errors)} erros.")


if __name__ == "__main__":
    main()
