"""Genera el manual PDF de la prueba de concepto (títulos Caveat, texto Geist).

Uso:
  python scripts/generar_pdf.py --expediente /tmp/odoo_poc/sesiones/XXXX.json \
      --guion /tmp/odoo_poc/guion.json --salida /mnt/user-data/outputs
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from _comun import escribir_json, leer_json
from odoo_lib.report import build_pdf

p = argparse.ArgumentParser()
p.add_argument("--expediente", required=True)
p.add_argument("--guion", help="JSON con introduccion, pasos[], cierre (opcional)")
p.add_argument("--salida", required=True, help="carpeta donde dejar el PDF para el consultor")
a = p.parse_args()

sess = leer_json(a.expediente)
sess.setdefault("archivo", a.expediente)
if a.guion:
    sess["guion"] = leer_json(a.guion)
    escribir_json(a.expediente, sess)

cliente = (sess.get("meta", {}).get("contexto", {}).get("cliente") or sess.get("titulo") or "cliente")
slug = re.sub(r"[^\w\-]+", "_", cliente).strip("_")[:40]
fecha = sess.get("fecha", "")[:10]
out = Path(a.salida) / f"Manual_PoC_{slug}_{fecha}.pdf"
out.parent.mkdir(parents=True, exist_ok=True)
print("PDF:", build_pdf(sess, sess.get("guion"), str(out)))
