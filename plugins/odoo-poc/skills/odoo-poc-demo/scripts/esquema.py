"""Lee los campos reales de los modelos elegidos y los catálogos existentes.

Uso:
  python scripts/esquema.py --modelos res.partner,product.template,sale.order

Imprime, por modelo, los campos útiles para la demo (t=tipo, req=obligatorio,
rel=modelo relacionado, opts=opciones de selección) y el sub-esquema de sus
líneas. Al final imprime registros existentes (id, nombre) de los catálogos
relacionados, que el plan puede usar por id. Todo se guarda en esquema.json.
"""
from __future__ import annotations

import argparse
import json

from _comun import TRABAJO, cliente, escribir_json
from odoo_lib.odoo_client import OdooError
from odoo_lib.schema import SchemaCache, reference_data

p = argparse.ArgumentParser()
p.add_argument("--modelos", required=True, help="lista separada por comas")
a = p.parse_args()
models = [m.strip() for m in a.modelos.split(",") if m.strip()]

client = cliente()
cache = SchemaCache(client)
out, faltan = {}, []
for m in models:
    try:
        out[m] = cache.for_ai(m)
    except OdooError as exc:
        faltan.append(f"{m}: {exc}")
targets = cache.related_targets(list(out)) if out else set()
ref = reference_data(client, targets)
escribir_json(TRABAJO / "esquema.json", {"modelos": out, "referencias": ref})

for m, data in out.items():
    print(f"=== {m}")
    print(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
print("=== REGISTROS EXISTENTES (modelo: [[id, nombre], ...])")
print(json.dumps(ref, ensure_ascii=False, separators=(",", ":")))
for f in faltan:
    print("NO DISPONIBLE:", f)
