"""Revisa un plan contra la base real SIN escribir nada en Odoo.

Uso:
  python scripts/validar_plan.py --plan /tmp/odoo_poc/plan.json

Detecta: modelos o campos inexistentes, opciones de selección inválidas,
referencias "@ref" a registros que no existen o van después, búsquedas
{"$buscar"} sin resultado y campos obligatorios sin valor ni valor por defecto.
Termina con un resumen por modelo para mostrárselo al consultor.
"""
from __future__ import annotations

import argparse

from _comun import cliente, leer_json, mapa_plan
from odoo_lib.importer import PlanError, Resolver
from odoo_lib.odoo_client import OdooError
from odoo_lib.schema import SchemaCache

p = argparse.ArgumentParser()
p.add_argument("--plan", required=True)
a = p.parse_args()

plan_skill = leer_json(a.plan)
plan, *_ = mapa_plan(plan_skill)
client = cliente()
cache = SchemaCache(client)
refs: dict[str, int] = {}
warnings: list[str] = []
errores: list[str] = []
resolver = Resolver(client, cache, refs, warnings)
fake_id = -1
resumen = []

for step in plan:
    m = step["model"]
    try:
        fields = cache.full(m)
    except OdooError as exc:
        errores.append(f"{m}: el modelo no existe o no es accesible ({exc})")
        continue
    required = [n for n, f in fields.items() if f.get("required") and not f.get("readonly")
                and n not in ("id",)]
    defaults: dict = {}
    if required:
        try:
            defaults = client.call(m, "default_get", fields_list=required) or {}
        except OdooError:
            defaults = {}
    ok = 0
    for rec in step["registros"]:
        ref = rec.get("ref") or "?"
        vals = rec.get("valores", {})
        antes = len(errores)
        try:
            resolver.record_vals(m, vals, set(step["campos"]))
        except PlanError as exc:
            errores.append(f"{m} [{ref}]: {exc}")
        except OdooError as exc:
            errores.append(f"{m} [{ref}]: {exc}")
        missing = [n for n in required if n not in vals and n not in defaults]
        if missing:
            errores.append(f"{m} [{ref}]: faltan campos obligatorios sin valor por defecto: {', '.join(missing)}")
        if ref in refs:
            errores.append(f"{m} [{ref}]: la referencia está repetida")
        if len(errores) == antes:
            ok += 1
        refs[ref] = fake_id
        fake_id -= 1
    resumen.append((m, len(step["registros"]), ok, len(step["campos"]),
                    ", ".join(x.get("metodo", "") for x in step["acciones"]) or "-"))

print("RESUMEN DEL PLAN")
print("| Modelo | Registros | Válidos | Campos | Acciones |")
print("|---|---|---|---|---|")
for r in resumen:
    print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |")
if warnings:
    print("\nADVERTENCIAS (no bloquean; esos campos se omitirían):")
    for w in dict.fromkeys(warnings):
        print(" -", w)
if errores:
    print(f"\nERRORES ({len(errores)}) — corrige el plan antes de importar:")
    for e in errores:
        print(" -", e)
    raise SystemExit(1)
print("\nPLAN VÁLIDO: listo para mostrarlo al consultor y pedir confirmación.")
