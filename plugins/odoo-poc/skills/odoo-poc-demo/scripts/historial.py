"""Arma la carpeta de la PoC para el vault de Obsidian.

Uso:
  python scripts/historial.py --expediente /tmp/odoo_poc/sesiones/XXXX.json \
      --pdf /tmp/odoo_poc/salida/Manual_PoC_X.pdf --salida /tmp/odoo_poc/salida

Crea  <salida>/<fecha> <cliente>/  con:
  * "PoC - <cliente> - <fecha>.md": nota de Obsidian (propiedades para filtrar,
    contexto, lógica, lo cargado, preguntas abiertas y el PDF incrustado).
  * el manual PDF de la PoC.
  * "expediente_<cliente>_<fecha>.json": respaldo técnico para deshacer o reutilizar.
Esa carpeta completa se copia a <vault>/PoCs/.
"""
from __future__ import annotations

import argparse
import re
import shutil
from collections import Counter
from pathlib import Path

from _comun import leer_json

p = argparse.ArgumentParser()
p.add_argument("--expediente", required=True)
p.add_argument("--salida", required=True)
p.add_argument("--pdf", default="", help="ruta del PDF generado; se copia a la carpeta y se incrusta en la nota")
a = p.parse_args()

s = leer_json(a.expediente)
meta = s.get("meta", {})
ctx = meta.get("contexto", {})
an = meta.get("analisis", {})
cliente = ctx.get("cliente") or s.get("titulo") or "Cliente"
fecha = s.get("fecha", "")[:10]
slug = re.sub(r"[^\w\-]+", "_", cliente).strip("_")[:40]
industria = ctx.get("industria", "")
tag_ind = re.sub(r"[^\w]+", "-", industria.lower()).strip("-") if industria else ""
creados = Counter(c["model"] for c in s.get("creados", []))
nombres = meta.get("nombres_modelos", {})

L = ["---", "tipo: poc-odoo", f"cliente: \"{cliente}\"", f"industria: \"{industria}\"", f"fecha: {fecha}",
     f"consultor: \"{meta.get('consultor', '')}\"", f"base: \"{s.get('db', '')}\"",
     f"odoo: \"{meta.get('version', '')}\"", f"ia: \"{meta.get('ia', '')}\"",
     f"registros_creados: {len(s.get('creados', []))}",
     f"estado: {'deshecha' if s.get('deshecho') else 'cargada'}",
     "tags: [poc, odoo" + (f", {tag_ind}" if tag_ind else "") + "]", "---", "",
     f"# PoC · {cliente}", ""]
L += ["## Contexto del cliente", ""]
etiquetas = {"industria": "Industria", "tamano_y_pais": "Tamaño y país", "sistemas_actuales": "Sistemas actuales",
             "procesos": "Procesos", "dolores": "Dolores", "objetivo_demo": "Qué quería ver",
             "notas_consultor": "Notas del consultor"}
for k, v in ctx.items():
    if v and k != "cliente":
        L.append(f"- **{etiquetas.get(k, k)}:** {v}")
L += ["", "## Enfoque y lógica de la demo", "", an.get("resumen", ""), ""]
if an.get("procesos_a_demostrar"):
    L += ["**Procesos demostrados**", ""] + [f"- {x}" for x in an["procesos_a_demostrar"]] + [""]
L += ["## Datos cargados", "", "| Información | Modelo | Creados | Por qué |", "|---|---|---|---|"]
for step in s.get("plan", []):
    m = step["model"]
    motivo = (meta.get("motivos", {}).get(m) or "").replace("|", "/")
    L.append(f"| {nombres.get(m, m)} | `{m}` | {creados.get(m, 0)} | {motivo} |")
L.append("")
if s.get("acciones_ok"):
    L += ["**Acciones aplicadas:** " + "; ".join(f"{x['descripcion'] or x['metodo']} ({x['model']}, "
                                                 f"{x['registros']})" for x in s["acciones_ok"]), ""]
if s.get("errores"):
    L += [f"**Registros rechazados:** {len(s['errores'])} (ver expediente)", ""]
if an.get("recomendaciones"):
    L += ["## Recomendaciones", ""] + [f"- {x}" for x in an["recomendaciones"]] + [""]
if an.get("preguntas_al_consultor"):
    L += ["## Preguntas abiertas con el cliente", ""] + [f"- [ ] {x}" for x in an["preguntas_al_consultor"]] + [""]
if meta.get("notas_obsidian"):
    L += ["## Notas consultadas", ""] + [f"- [[{Path(n).stem}]]" for n in meta["notas_obsidian"]] + [""]
pdf_name = Path(a.pdf).name if a.pdf else ""
exp_name = f"expediente_{slug}_{fecha}.json"
L += ["## Archivos", ""]
L.append(f"- Expediente técnico (para deshacer o reutilizar): `{exp_name}`")
if pdf_name:
    L += ["", "## Manual de la PoC", "", f"![[{pdf_name}]]"]
L.append("")

carpeta = Path(a.salida) / re.sub(r'[\\/:*?"<>|]+', "-", f"{fecha} {cliente}").strip()
carpeta.mkdir(parents=True, exist_ok=True)
nota = carpeta / re.sub(r'[\\/:*?"<>|]+', "-", f"PoC - {cliente} - {fecha}.md")
nota.write_text("\n".join(L), encoding="utf-8")
shutil.copy(a.expediente, carpeta / exp_name)
if a.pdf and Path(a.pdf).resolve() != (carpeta / pdf_name).resolve():
    shutil.copy(a.pdf, carpeta / pdf_name)
print("CARPETA:", carpeta)
for f in sorted(carpeta.iterdir()):
    print("  -", f.name)
