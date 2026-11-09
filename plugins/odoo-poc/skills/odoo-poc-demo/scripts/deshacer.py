"""Borra de Odoo todo lo creado por una carga (en orden inverso).

Uso (requiere haber ejecutado conectar.py contra LA MISMA base):
  python scripts/deshacer.py --expediente expediente_Cliente_2026-10-20.json --confirmado
"""
from __future__ import annotations

import argparse

from _comun import cliente, fallar, leer_json
from odoo_lib.importer import undo_session

p = argparse.ArgumentParser()
p.add_argument("--expediente", required=True)
p.add_argument("--confirmado", action="store_true")
a = p.parse_args()

s = leer_json(a.expediente)
s["archivo"] = a.expediente
if not a.confirmado:
    fallar("Falta --confirmado: pide al consultor confirmación explícita antes de borrar.")
if s.get("deshecho"):
    fallar("Esta carga ya fue deshecha anteriormente.")
client = cliente()
if client.db != s.get("db") or client.url.rstrip("/") != s.get("url", "").rstrip("/"):
    fallar(f"La conexión activa es {client.db} ({client.url}) pero el expediente es de "
           f"{s.get('db')} ({s.get('url')}). Conéctate a la base correcta.")
print(f"Borrando {len(s.get('creados', []))} registros de {client.db}...")
r = undo_session(client, s)
print(f"Borrados: {r['borrados']}")
for f in r["fallidos"]:
    print(" -", f)
print("Expediente actualizado (marcado como deshecho):", a.expediente)
