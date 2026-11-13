"""Cliente HTTP compartilhado para a API de dados abertos da Câmara do Recife.

Fonte: https://e-processo.recife.pe.leg.br (API JSON pública, sem autenticação)
"""
import json
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://e-processo.recife.pe.leg.br"

_session = None


def session():
    """Return a shared requests.Session with retry and a default timeout."""
    global _session
    if _session is None:
        s = requests.Session()
        s.headers.update({"User-Agent": "open-data-collector/1.0"})
        retry = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        adapter = HTTPAdapter(max_retries=retry)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        _session = s
    return _session


def get(path, timeout=60):
    """GET {BASE}{path} and return the parsed JSON body."""
    response = session().get(f"{BASE}{path}", timeout=timeout)
    response.raise_for_status()
    return response.json()


def save(file_path: Path, data):
    """Write `data` as pretty UTF-8 JSON, creating parent folders."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
