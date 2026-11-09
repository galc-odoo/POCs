"""Lista los modelos de negocio de la base conectada (para el análisis).

Uso:
  python scripts/modelos.py                # todos
  python scripts/modelos.py --filtro sale  # solo los que contienen el texto
"""
from __future__ import annotations

import argparse

from _comun import CONEXION, fallar, leer_json

p = argparse.ArgumentParser()
p.add_argument("--filtro", default="")
a = p.parse_args()
if not CONEXION.exists():
    fallar("Ejecuta primero scripts/conectar.py")
data = leer_json(CONEXION)
f = a.filtro.lower()
rows = [m for m in data["modelos"] if f in m["model"].lower() or f in (m["name"] or "").lower()]
for m in rows:
    print(f"{m['model']}: {m['name']}")
print(f"\n{len(rows)} modelos")
