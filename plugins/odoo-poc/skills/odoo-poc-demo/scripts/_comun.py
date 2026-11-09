"""Utilidades compartidas por los scripts del skill."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from odoo_lib import importer  # noqa: E402
from odoo_lib.odoo_client import OdooClient, OdooError  # noqa: E402

TRABAJO = Path(os.environ.get("ODOO_POC_DIR", "/tmp/odoo_poc"))
CRED = TRABAJO / "credenciales.json"
CONEXION = TRABAJO / "conexion.json"


def preparar() -> None:
    TRABAJO.mkdir(parents=True, exist_ok=True)
    importer.SESSIONS_DIR = TRABAJO / "sesiones"


def leer_json(path: str | Path) -> dict | list:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def escribir_json(path: str | Path, data) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return p


def guardar_credenciales(client: OdooClient) -> None:
    preparar()
    escribir_json(CRED, {"url": client.url, "db": client.db, "login": client.login,
                         "api_key": client.api_key, "protocol": client.protocol})
    os.chmod(CRED, 0o600)


def cliente() -> OdooClient:
    """Cliente ya conectado con las credenciales de conectar.py."""
    preparar()
    if not CRED.exists():
        fallar("No hay conexión activa. Ejecuta primero scripts/conectar.py.")
    c = leer_json(CRED)
    client = OdooClient(c["url"], c["db"], c["login"], c["api_key"], c.get("protocol", "auto"))
    try:
        client.connect()
    except OdooError as exc:
        fallar(str(exc))
    return client


def fallar(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}")
    sys.exit(code)


def es_error_de_red(msg: str) -> bool:
    m = msg.lower()
    return any(w in m for w in ("proxy", "tunnel", "name resolution", "nodename", "connection refused",
                                "max retries", "failed to establish", "temporary failure", "403 forbidden",
                                "network is unreachable", "timed out"))


def mapa_plan(plan_skill: list[dict]) -> tuple[list[dict], dict, dict, dict]:
    """Convierte el plan del skill al formato del importador.

    Devuelve (plan_importador, descripciones, motivos, campos_motivo).
    """
    plan, descs, motivos, campos_motivo = [], {}, {}, {}
    for step in plan_skill:
        m = step["model"]
        campos = step.get("campos") or []
        names = [c["campo"] if isinstance(c, dict) else c for c in campos]
        # Los campos usados en los registros también cuentan como confirmados
        for r in step.get("registros", []):
            for k in r.get("valores", {}):
                if k not in names:
                    names.append(k)
        plan.append({"model": m, "campos": names, "registros": step.get("registros", []),
                     "acciones": step.get("acciones", [])})
        descs[m] = step.get("descripcion", "")
        motivos[m] = step.get("motivo", "")
        campos_motivo[m] = {c["campo"]: c.get("motivo", "") for c in campos if isinstance(c, dict)}
    return plan, descs, motivos, campos_motivo
