"""Validación del plan contra la base real, importación y deshacer."""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from .odoo_client import OdooClient, OdooError
from .schema import SchemaCache

SESSIONS_DIR = Path("/tmp/odoo_poc/sesiones")  # los scripts lo cambian según --trabajo
REL_DATE = re.compile(r"^\$hoy\s*([+-]\s*\d+)?$", re.I)

# Cómo devolver a borrador/cancelar antes de borrar, por modelo
UNDO_STEPS = {
    "account.move": ["button_draft"],
    "account.payment": ["action_draft"],
    "sale.order": ["action_cancel"],
    "purchase.order": ["button_cancel"],
    "stock.picking": ["action_cancel"],
    "mrp.production": ["action_cancel"],
    "pos.order": [],
}


class PlanError(Exception):
    pass


# ----------------------------------------------------------------- valores
def resolve_date(value: str, kind: str) -> str:
    m = REL_DATE.match(value.strip())
    if not m:
        return value
    delta = int(m.group(1).replace(" ", "")) if m.group(1) else 0
    d = date.today() + timedelta(days=delta)
    if kind == "datetime":
        return datetime.combine(d, datetime.min.time()).replace(hour=10).strftime("%Y-%m-%d %H:%M:%S")
    return d.isoformat()


class Resolver:
    def __init__(self, client: OdooClient, cache: SchemaCache, refs: dict[str, int],
                 warnings: list[str]):
        self.client, self.cache, self.refs, self.warnings = client, cache, refs, warnings
        self._search_cache: dict[tuple, int | None] = {}

    def record_vals(self, model: str, vals: dict, allowed: set[str] | None = None) -> dict:
        fields = self.cache.full(model)
        out: dict[str, Any] = {}
        for name, value in vals.items():
            if allowed is not None and name not in allowed:
                continue
            f = fields.get(name)
            if not f:
                self.warnings.append(f"{model}: el campo '{name}' no existe; se omitió.")
                continue
            try:
                out[name] = self.value(model, name, f, value)
            except PlanError as exc:
                if f.get("required"):
                    raise
                self.warnings.append(f"{model}.{name}: {exc}; se omitió.")
        return out

    def value(self, model: str, name: str, f: dict, value: Any) -> Any:
        t = f.get("type")
        if value is None:
            return False
        if t == "many2one":
            return self.m2o(f["relation"], value)
        if t == "many2many":
            items = value if isinstance(value, list) else [value]
            ids = [self.m2o(f["relation"], v) for v in items]
            return [[6, 0, [i for i in ids if i]]]
        if t == "one2many":
            items = value if isinstance(value, list) else [value]
            cmds = []
            for line in items:
                if not isinstance(line, dict):
                    raise PlanError("las líneas deben ser objetos")
                cmds.append([0, 0, self.record_vals(f["relation"], line)])
            return cmds
        if t in ("date", "datetime") and isinstance(value, str):
            return resolve_date(value, t)
        if t == "selection" and isinstance(f.get("selection"), list):
            keys = [s[0] for s in f["selection"]]
            if value in keys:
                return value
            for k, label in f["selection"]:
                if str(label).lower() == str(value).lower():
                    return k
            raise PlanError(f"valor '{value}' no válido (opciones: {keys[:10]})")
        if t in ("integer",) and isinstance(value, str):
            return int(float(value))
        if t in ("float", "monetary") and isinstance(value, str):
            return float(value)
        return value

    def m2o(self, relation: str, value: Any) -> int | bool:
        if value in (False, "", 0):
            return False
        if isinstance(value, bool):
            return False
        if isinstance(value, int):
            return value
        if isinstance(value, list) and value and isinstance(value[0], int):
            return value[0]
        if isinstance(value, str) and value.startswith("@"):
            ref = value[1:]
            if ref not in self.refs:
                raise PlanError(f"la referencia '{value}' no se ha creado (¿falló o va después?)")
            return self.refs[ref]
        text = value.get("$buscar") if isinstance(value, dict) else str(value)
        if not text:
            raise PlanError(f"valor no reconocido: {value}")
        key = (relation, text)
        if key not in self._search_cache:
            res = self.client.name_search(relation, text, limit=1)
            self._search_cache[key] = res[0][0] if res else None
        found = self._search_cache[key]
        if not found:
            raise PlanError(f"no se encontró '{text}' en {relation}")
        return found


# ----------------------------------------------------------------- sesiones
def new_session(client: OdooClient, title: str) -> dict:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = re.sub(r"[^\w\-]+", "_", title)[:40] or "demo"
    return {
        "archivo": str(SESSIONS_DIR / f"{stamp}_{client.db}_{safe}.json"),
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "url": client.url, "db": client.db, "titulo": title,
        "creados": [], "errores": [], "advertencias": [], "deshecho": False,
    }


def save_session(sess: dict) -> None:
    Path(sess["archivo"]).write_text(json.dumps(sess, ensure_ascii=False, indent=2), encoding="utf-8")


def list_sessions() -> list[dict]:
    if not SESSIONS_DIR.exists():
        return []
    out = []
    for p in sorted(SESSIONS_DIR.glob("*.json"), reverse=True):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return out


# ----------------------------------------------------------------- importar
def run_import(client: OdooClient, plan: list[dict], title: str,
               progress: Callable[[float, str], None] | None = None, meta: dict | None = None) -> dict:
    """Ejecuta un plan aprobado. Cada paso: model, campos (permitidos), registros, acciones.

    `meta` (contexto, análisis, motivos, etc.) se guarda en la sesión para el PDF de la PoC.
    """
    cache = SchemaCache(client)
    sess = new_session(client, title)
    sess["meta"] = meta or {}
    sess["plan"] = plan
    sess["acciones_ok"] = []
    refs: dict[str, int] = {}
    resolver = Resolver(client, cache, refs, sess["advertencias"])
    total = sum(len(s["registros"]) for s in plan) or 1
    done = 0

    for step in plan:
        model = step["model"]
        allowed = set(step["campos"]) if step.get("campos") else None
        created_here: dict[str, int] = {}
        for rec in step["registros"]:
            ref = rec.get("ref") or f"{model}_{done}"
            done += 1
            if progress:
                progress(done / total, f"{model}: {ref}")
            try:
                vals = resolver.record_vals(model, rec.get("valores", {}), allowed)
                rid = client.create(model, vals)
            except (OdooError, PlanError) as exc:
                sess["errores"].append({"model": model, "ref": ref, "error": str(exc)})
                save_session(sess)
                continue
            refs[ref] = rid
            created_here[ref] = rid
            sess["creados"].append({"model": model, "id": rid, "ref": ref})
            save_session(sess)

        for act in step.get("acciones", []):
            targets = act.get("refs") or list(created_here)
            ids = [created_here[r] for r in targets if r in created_here]
            if not ids:
                continue
            try:
                res = client.call(model, act["metodo"], ids=ids)
                sess["acciones_ok"].append({"model": model, "metodo": act["metodo"],
                                            "descripcion": act.get("descripcion", ""), "registros": len(ids)})
                if isinstance(res, dict) and res.get("type", "").startswith("ir.actions"):
                    sess["advertencias"].append(
                        f"{model}.{act['metodo']} abrió un asistente; termínalo manualmente en Odoo.")
            except OdooError as exc:
                # Si falla en lote, se intenta registro por registro
                for rid in ids:
                    try:
                        client.call(model, act["metodo"], ids=[rid])
                    except OdooError as exc2:
                        sess["errores"].append({"model": model, "ref": f"id {rid}",
                                                "error": f"{act['metodo']}: {exc2}"})
                sess["advertencias"].append(f"{model}.{act['metodo']} en lote falló ({exc}); se reintentó uno por uno.")
        save_session(sess)

    save_session(sess)
    return sess


def undo_session(client: OdooClient, sess: dict,
                 progress: Callable[[float, str], None] | None = None) -> dict:
    """Borra en orden inverso lo creado por una sesión."""
    results = {"borrados": 0, "fallidos": []}
    items = list(reversed(sess.get("creados", [])))
    for i, item in enumerate(items, 1):
        model, rid = item["model"], item["id"]
        if progress:
            progress(i / max(len(items), 1), f"{model} #{rid}")
        for method in UNDO_STEPS.get(model, []):
            try:
                client.call(model, method, ids=[rid])
            except OdooError:
                pass
        try:
            client.unlink(model, [rid])
            results["borrados"] += 1
        except OdooError as exc:
            # Último recurso: archivar si el modelo lo permite
            try:
                client.call(model, "write", ids=[rid], vals={"active": False})
                results["fallidos"].append(f"{model} #{rid}: no se pudo borrar, se archivó ({exc})")
            except OdooError:
                results["fallidos"].append(f"{model} #{rid}: {exc}")
    sess["deshecho"] = True
    sess["resultado_deshacer"] = results
    save_session(sess)
    return results
