"""Descubrimiento dinámico de la estructura de la base Odoo del cliente.

Nada está programado a mano: se leen los módulos instalados, los modelos
existentes (incluidos los personalizados) y los campos de cada modelo.
"""
from __future__ import annotations

from .odoo_client import OdooClient, OdooError

# Prefijos de modelos técnicos que nunca tienen sentido en una demo
TECH_PREFIXES = (
    "ir.", "base.", "base_import.", "bus.", "res.config", "res.users.", "mail.", "web_", "web.",
    "digest.", "auth_", "auth.", "iap.", "report.", "portal.", "sms.", "spreadsheet.", "html_",
    "onboarding.", "publisher_warranty", "change.password", "reset.view", "_unknown", "format.",
    "privacy.", "snailmail.", "phone.", "barcode.", "bus_", "discuss.", "rating.", "utm.",
    "google.", "microsoft.", "payment.provider", "theme.", "website.visitor", "website.track",
    "account.report", "account.edi", "l10n_", "resource.calendar.leaves", "fetchmail.",
)

MAGIC_FIELDS = {
    "id", "create_uid", "create_date", "write_uid", "write_date", "__last_update",
    "display_name", "access_url", "access_token", "access_warning",
}
NOISE_PREFIXES = ("message_", "activity_", "website_message", "has_message", "rating_",
                  "my_activity", "__")


def installed_modules(client: OdooClient) -> list[dict]:
    rows = client.search_read("ir.module.module", [["state", "=", "installed"]],
                              ["name", "shortdesc"], order="name")
    return [{"name": r["name"], "desc": r.get("shortdesc") or ""} for r in rows]


def business_models(client: OdooClient) -> list[dict]:
    """Modelos de negocio disponibles (sin transitorios ni técnicos)."""
    fields = ["model", "name"]
    domain = [["transient", "=", False]]
    try:
        rows = client.search_read("ir.model", domain, fields, order="model")
    except OdooError:
        rows = client.search_read("ir.model", [], fields, order="model")
    out = []
    for r in rows:
        m = r["model"]
        if m.startswith(TECH_PREFIXES) or "wizard" in m:
            continue
        out.append({"model": m, "name": r.get("name") or m})
    return out


def _useful_field(name: str, f: dict) -> bool:
    if name in MAGIC_FIELDS or name.startswith(NOISE_PREFIXES):
        return False
    if f.get("type") in ("binary", "image", "html", "properties", "properties_definition", "json"):
        return bool(f.get("required"))
    if f.get("store") is False and not f.get("required"):
        return False
    if f.get("readonly") and not f.get("required"):
        return False
    return True


def compact_fields(all_fields: dict) -> dict:
    """Versión reducida de fields_get para mandar a la IA."""
    out = {}
    for name, f in all_fields.items():
        if not _useful_field(name, f):
            continue
        item = {"t": f.get("type"), "label": f.get("string")}
        if f.get("required"):
            item["req"] = True
        if f.get("relation"):
            item["rel"] = f["relation"]
        if f.get("selection") and isinstance(f["selection"], list):
            item["opts"] = [s[0] for s in f["selection"][:20]]
        out[name] = item
    return out


def is_line_field(name: str, f: dict) -> bool:
    rel = f.get("relation") or ""
    return f.get("type") == "one2many" and (
        name.endswith(("line", "lines", "line_ids", "lines_ids")) or rel.endswith((".line", "_line"))
        or name in ("move_ids", "move_ids_without_package", "attribute_line_ids", "seller_ids",
                    "child_ids", "bom_line_ids")
    )


class SchemaCache:
    """Cachea fields_get por modelo para no repetir llamadas."""

    def __init__(self, client: OdooClient):
        self.client = client
        self._full: dict[str, dict] = {}

    def full(self, model: str) -> dict:
        if model not in self._full:
            self._full[model] = self.client.fields_get(model)
        return self._full[model]

    def for_ai(self, model: str) -> dict:
        """Campos útiles del modelo + sub-esquema de sus líneas (one2many)."""
        full = self.full(model)
        comp = compact_fields(full)
        lines = {}
        for name, f in full.items():
            if name in comp and is_line_field(name, f):
                try:
                    lines[name] = compact_fields(self.full(f["relation"]))
                except OdooError:
                    pass
        # one2many que no son líneas se quitan: suelen ser vistas inversas
        comp = {k: v for k, v in comp.items() if v["t"] != "one2many" or k in lines}
        return {"campos": comp, "lineas": lines}

    def related_targets(self, models: list[str]) -> set[str]:
        """Modelos destino de campos many2one/many2many usados por `models`."""
        targets: set[str] = set()
        for m in models:
            data = self.for_ai(m)
            groups = [data["campos"], *data["lineas"].values()]
            for g in groups:
                for f in g.values():
                    if f["t"] in ("many2one", "many2many") and f.get("rel"):
                        targets.add(f["rel"])
        return targets - set(models)


REFERENCE_DOMAINS = {
    "res.country": [["code", "in", ["MX", "US", "CO", "ES", "AR", "CL", "PE"]]],
    "res.currency": [["active", "=", True]],
}


def reference_data(client: OdooClient, targets: set[str], per_model: int = 15,
                   max_models: int = 45) -> dict[str, list]:
    """Registros existentes (id, nombre) de catálogos que la demo puede referenciar."""
    out: dict[str, list] = {}
    for model in sorted(targets)[:max_models]:
        if model.startswith(("ir.", "mail.", "bus.")):
            continue
        try:
            rows = client.search_read(model, REFERENCE_DOMAINS.get(model, []), ["display_name"],
                                      limit=per_model)
        except OdooError:
            continue
        if rows:
            out[model] = [[r["id"], r.get("display_name")] for r in rows]
    return out


def safety_report(client: OdooClient) -> dict:
    """Indicadores para detectar si la base parece de producción."""
    rep = {"contactos": 0, "facturas_publicadas": 0, "alerta": False, "motivos": []}
    try:
        rep["contactos"] = client.search_count("res.partner")
    except OdooError:
        pass
    try:
        rep["facturas_publicadas"] = client.search_count(
            "account.move", [["state", "=", "posted"], ["move_type", "in", ["out_invoice", "in_invoice"]]])
    except OdooError:
        pass
    if any(w in client.db.lower() for w in ("prod", "produccion", "production", "live")):
        rep["motivos"].append("El nombre de la base sugiere producción.")
    if rep["facturas_publicadas"] > 100:
        rep["motivos"].append(f"Tiene {rep['facturas_publicadas']} facturas publicadas.")
    if rep["contactos"] > 1000:
        rep["motivos"].append(f"Tiene {rep['contactos']} contactos.")
    rep["alerta"] = bool(rep["motivos"])
    return rep
