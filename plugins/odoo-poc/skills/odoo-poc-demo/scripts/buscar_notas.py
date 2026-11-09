"""Busca en notas de Obsidian adjuntas (archivos .md, carpetas o un .zip del vault).

Uso:
  python scripts/buscar_notas.py --origen /ruta/nota1.md /ruta/vault.zip --consulta "distribuidora crédito cobranza" -k 6
"""
from __future__ import annotations

import argparse
import shutil
import tempfile
import zipfile
from pathlib import Path

from odoo_lib.knowledge import Vault, notes_to_context

p = argparse.ArgumentParser()
p.add_argument("--origen", nargs="+", required=True, help="archivos .md, carpetas o .zip")
p.add_argument("--consulta", required=True)
p.add_argument("-k", type=int, default=6)
p.add_argument("--max-caracteres", type=int, default=3000)
a = p.parse_args()

tmp = Path(tempfile.mkdtemp(prefix="vault_"))
for src in a.origen:
    s = Path(src)
    if not s.exists():
        print(f"(no existe: {s})")
        continue
    if s.suffix.lower() == ".zip":
        with zipfile.ZipFile(s) as z:
            for member in z.namelist():
                # Solo notas Markdown y sin rutas que escapen de la carpeta
                if member.lower().endswith(".md") and ".." not in Path(member).parts:
                    z.extract(member, tmp / s.stem)
    elif s.is_dir():
        shutil.copytree(s, tmp / s.name, dirs_exist_ok=True)
    elif s.suffix.lower() == ".md":
        shutil.copy(s, tmp / s.name)

v = Vault(str(tmp))
n = v.load()
notes = v.search(a.consulta, k=a.k)
print(f"{n} notas leídas · {len(notes)} relevantes para: {a.consulta}\n")
print(notes_to_context(notes, a.max_caracteres) if notes else "Ninguna nota coincide con la consulta.")
