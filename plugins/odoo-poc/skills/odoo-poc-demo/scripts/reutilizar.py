"""Extrae el análisis y el plan de un expediente anterior para reutilizarlos.

Uso:
  python scripts/reutilizar.py --expediente expediente_Cliente_2026-10-20.json

Escribe /tmp/odoo_poc/analisis.json y /tmp/odoo_poc/plan.json en el formato
del skill, listos para ajustarse al nuevo cliente y validarse.
"""
from __future__ import annotations

import argparse

from _comun import TRABAJO, escribir_json, leer_json, preparar

p = argparse.ArgumentParser()
p.add_argument("--expediente", required=True)
a = p.parse_args()
preparar()

s = leer_json(a.expediente)
meta = s.get("meta", {})
an = dict(meta.get("analisis", {}))
an["contexto"] = meta.get("contexto", an.get("contexto", {}))
an["origen"] = s.get("archivo", a.expediente)
plan = []
for step in s.get("plan", []):
    m = step["model"]
    cm = meta.get("campos_motivo", {}).get(m, {})
    plan.append({"model": m, "descripcion": meta.get("descripciones", {}).get(m, ""),
                 "motivo": meta.get("motivos", {}).get(m, ""),
                 "campos": [{"campo": c, "motivo": cm.get(c, "")} for c in step.get("campos", [])],
                 "registros": step.get("registros", []), "acciones": step.get("acciones", [])})
escribir_json(TRABAJO / "analisis.json", an)
escribir_json(TRABAJO / "plan.json", plan)
print(f"Cliente original: {an['contexto'].get('cliente', '')} · {len(plan)} modelos · "
      f"{sum(len(p['registros']) for p in plan)} registros")
print("Escritos:", TRABAJO / "analisis.json", "y", TRABAJO / "plan.json")
