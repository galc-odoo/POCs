"""Importa a Odoo un plan YA CONFIRMADO por el consultor.

Uso:
  python scripts/importar.py --plan /tmp/odoo_poc/plan.json --analisis /tmp/odoo_poc/analisis.json \
      --titulo "Demo Eléctrica del Norte" --ia "Claude (Sonnet)"

Crea los registros en orden, ejecuta las acciones confirmadas y guarda un
expediente JSON con todo lo creado (sirve para el PDF, el historial y deshacer).
"""
from __future__ import annotations

import argparse
from collections import Counter

from _comun import CONEXION, cliente, leer_json, mapa_plan
from odoo_lib.importer import run_import

p = argparse.ArgumentParser()
p.add_argument("--plan", required=True)
p.add_argument("--analisis", required=True)
p.add_argument("--titulo", required=True)
p.add_argument("--ia", default="Claude")
p.add_argument("--confirmado", action="store_true",
               help="obligatorio: indica que el consultor aprobó el plan en la conversación")
a = p.parse_args()
if not a.confirmado:
    raise SystemExit("ERROR: falta --confirmado. Solo se importa después de que el consultor apruebe el plan.")

plan_skill = leer_json(a.plan)
analisis = leer_json(a.analisis)
plan, descs, motivos, campos_motivo = mapa_plan(plan_skill)
con = leer_json(CONEXION) if CONEXION.exists() else {}
nombres = {m["model"]: m["name"] for m in con.get("modelos", [])}
# Si el paso del plan no trae motivo, se usa el del análisis
for m in analisis.get("modelos", []):
    if not motivos.get(m.get("model")):
        motivos[m.get("model")] = m.get("motivo", "")

meta = {
    "contexto": analisis.get("contexto", {}),
    "analisis": analisis,
    "nombres_modelos": nombres,
    "motivos": motivos,
    "descripciones": descs,
    "campos_motivo": campos_motivo,
    "notas_obsidian": analisis.get("notas_obsidian", []),
    "version": con.get("version", ""),
    "ia": a.ia,
    "consultor": analisis.get("consultor", ""),
}

client = cliente()
total = sum(len(s["registros"]) for s in plan)
print(f"Importando {total} registros en {client.db}...")
sess = run_import(client, plan, a.titulo, meta=meta)

por_modelo = Counter(c["model"] for c in sess["creados"])
print("\nRESULTADO")
print("| Modelo | Creados |")
print("|---|---|")
for m, n in por_modelo.items():
    print(f"| {m} | {n} |")
for x in sess.get("acciones_ok", []):
    print(f"Acción {x['model']}.{x['metodo']} aplicada a {x['registros']} registro(s)")
if sess["errores"]:
    print(f"\nERRORES ({len(sess['errores'])}):")
    for e in sess["errores"]:
        print(f" - {e['model']} [{e['ref']}]: {e['error']}")
if sess["advertencias"]:
    print("\nADVERTENCIAS:")
    for w in sess["advertencias"]:
        print(" -", w)
print(f"\nEXPEDIENTE: {sess['archivo']}")
