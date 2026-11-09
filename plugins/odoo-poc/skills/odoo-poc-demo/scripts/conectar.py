"""Conecta con la base Odoo del cliente y describe qué tiene instalado.

Uso:
  python scripts/conectar.py --url https://cliente.odoo.com --db cliente --usuario admin@x.com --api-key XXXX

Guarda las credenciales en el área de trabajo temporal (solo para esta
conversación) y escribe conexion.json con versión, módulos y modelos.
"""
from __future__ import annotations

import argparse

from _comun import CONEXION, escribir_json, es_error_de_red, fallar, guardar_credenciales, preparar
from odoo_lib.odoo_client import OdooClient, OdooError
from odoo_lib.schema import business_models, installed_modules, safety_report

p = argparse.ArgumentParser()
p.add_argument("--url", required=True)
p.add_argument("--db", required=True)
p.add_argument("--usuario", required=True)
p.add_argument("--api-key", required=True)
p.add_argument("--protocolo", default="auto", choices=["auto", "json2", "xmlrpc"])
a = p.parse_args()
preparar()

client = OdooClient(a.url, a.db, a.usuario, a.api_key, a.protocolo)
try:
    info = client.connect()
except OdooError as exc:
    msg = str(exc)
    if es_error_de_red(msg):
        msg += ("\n\nPOSIBLE CAUSA: el entorno de Claude no tiene permiso para salir a internet. "
                "En Claude: Configuración > Capacidades > activar 'Allow network egress' "
                "(acceso a red) y volver a intentar.")
    fallar(msg)

guardar_credenciales(client)
mods = installed_modules(client)
models = business_models(client)
seg = safety_report(client)
escribir_json(CONEXION, {"url": client.url, "db": client.db, "version": info["version"],
                         "protocolo": info["protocolo"], "modulos": mods, "modelos": models,
                         "seguridad": seg})

print(f"CONECTADO a {client.db} ({client.url})")
print(f"Odoo {info['version']} · protocolo {info['protocolo']}")
print(f"Módulos instalados ({len(mods)}): " + ", ".join(m["name"] for m in mods))
print(f"Modelos de negocio disponibles: {len(models)} (lista completa en {CONEXION} -> 'modelos')")
print(f"Contactos existentes: {seg['contactos']} · facturas publicadas: {seg['facturas_publicadas']}")
if seg["alerta"]:
    print("ALERTA: la base podría ser de PRODUCCIÓN -> " + " ".join(seg["motivos"]))
    print("Pide al consultor confirmación explícita de que es una base de prueba antes de cargar datos.")
