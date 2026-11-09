"""Regenera la nota "Índice de PoCs.md" a partir de las notas de PoC del vault.

Uso:
  python scripts/indice.py --pocs /tmp/odoo_poc/vault/PoCs --salida /tmp/odoo_poc/salida

Lee las propiedades (frontmatter) de cada nota con `tipo: poc-odoo` y escribe
una tabla ordenada de la más reciente a la más antigua, con enlaces a cada PoC.
También sirve para responder "¿qué PoCs hemos hecho de X?" (opción --buscar).
"""
from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--pocs", required=True, help="carpeta con las notas de PoC (se busca recursivamente)")
p.add_argument("--salida", help="carpeta donde escribir 'Índice de PoCs.md'")
p.add_argument("--buscar", default="", help="filtra por texto (cliente, industria, consultor...)")
a = p.parse_args()


def props(text: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    out = {}
    if not m:
        return out
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip('"')
    return out


rows = []
for f in Path(a.pocs).rglob("*.md"):
    if f.name.startswith(("_", "Índice")):
        continue
    text = f.read_text(encoding="utf-8", errors="ignore")
    pr = props(text)
    if pr.get("tipo") != "poc-odoo":
        continue
    if a.buscar and a.buscar.lower() not in text.lower():
        continue
    pr["_nota"] = f.stem
    preguntas = re.findall(r"^- \[ \] (.+)$", text, re.M)
    pr["_pendientes"] = len(preguntas)
    rows.append(pr)
rows.sort(key=lambda r: r.get("fecha", ""), reverse=True)

L = ["---", "tipo: indice-pocs", f"actualizado: {date.today().isoformat()}", "---", "",
     "# Índice de PoCs", "",
     f"{len(rows)} PoCs registradas. Se actualiza automáticamente cada vez que Claude guarda una PoC.", "",
     "| Fecha | Cliente | Industria | Consultor | Registros | Base | Estado | Preguntas abiertas |",
     "|---|---|---|---|---|---|---|---|"]
for r in rows:
    L.append(f"| {r.get('fecha', '')} | [[{r['_nota']}\\|{r.get('cliente', r['_nota'])}]] | {r.get('industria', '')} | "
             f"{r.get('consultor', '')} | {r.get('registros_creados', '')} | {r.get('base', '')} | "
             f"{r.get('estado', 'cargada')} | {r['_pendientes']} |")
L.append("")

if a.salida:
    out = Path(a.salida) / "Índice de PoCs.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L), encoding="utf-8")
    print("ÍNDICE:", out)
print("\n".join(L[5:]))
