"""Cliente unificado para la API externa de Odoo.

Soporta dos protocolos:
  * JSON-2  (Odoo 19 en adelante)  ->  POST /json/2/<modelo>/<metodo>
  * XML-RPC (Odoo 18 y anteriores) ->  /xmlrpc/2/common y /xmlrpc/2/object

El resto de la aplicación solo usa los métodos de alto nivel de esta clase
(search_read, fields_get, create, call, name_search, unlink), así que no
necesita saber qué protocolo hay debajo.
"""
from __future__ import annotations

import xmlrpc.client
from dataclasses import dataclass, field
from typing import Any

import requests


class OdooError(Exception):
    """Error devuelto por Odoo o por la conexión."""


def normalize_url(url: str) -> str:
    """Deja solo esquema + dominio (+ puerto).

    Desde Odoo 17.2 la barra del navegador muestra rutas como
    https://cliente.odoo.com/odoo/action-123; si se copian, la API no responde.
    """
    from urllib.parse import urlsplit
    url = url.strip()
    if not url:
        return url
    if "://" not in url:
        url = "https://" + url
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


@dataclass
class OdooClient:
    url: str
    db: str
    login: str
    api_key: str
    protocol: str = "auto"          # auto | json2 | xmlrpc
    timeout: int = 120
    version: str = ""
    major: int = 0
    uid: int | None = None
    _session: requests.Session = field(default_factory=requests.Session, repr=False)

    # ------------------------------------------------------------------ setup
    def __post_init__(self) -> None:
        self.url = normalize_url(self.url)
        self.db = self.db.strip()
        self.login = self.login.strip()
        self.api_key = self.api_key.strip()

    def connect(self) -> dict:
        """Detecta versión, elige protocolo y valida credenciales.

        En modo auto prueba los protocolos en el orden más probable y, si uno
        falla, intenta el otro antes de reportar el error.
        """
        self._detect_version()
        if self.protocol in ("json2", "xmlrpc"):
            order = [self.protocol]
        elif self.major >= 19:
            order = ["json2", "xmlrpc"]
        elif self.major > 0:
            order = ["xmlrpc"]
        else:
            order = ["xmlrpc", "json2"]

        errors = []
        for proto in order:
            try:
                self._auth(proto)
                self.protocol = proto
                return {"version": self.version or "desconocida", "protocolo": proto}
            except OdooError as exc:
                errors.append(f"{'JSON-2' if proto == 'json2' else 'XML-RPC'}: {exc}")
        raise OdooError(self._diagnose(errors))

    def _auth(self, proto: str) -> None:
        self.protocol = proto
        if proto == "xmlrpc":
            common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common", allow_none=True)
            try:
                self.uid = common.authenticate(self.db, self.login, self.api_key, {})
            except xmlrpc.client.ProtocolError as exc:
                raise OdooError(f"HTTP {exc.errcode} (la ruta /xmlrpc no responde)") from exc
            except xmlrpc.client.Fault as exc:
                last = str(exc.faultString).strip().splitlines()
                raise OdooError(last[-1] if last else str(exc)) from exc
            except Exception as exc:  # noqa: BLE001
                raise OdooError(str(exc)[:200]) from exc
            if not self.uid:
                raise OdooError("credenciales rechazadas (usuario, base de datos o API key)")
        else:
            self.call("res.users", "context_get")

    def _diagnose(self, errors: list[str]) -> str:
        ver = f"Odoo {self.version}" if self.version else "versión no detectada"
        hints = [
            f"Revisa que la URL sea solo el dominio, sin rutas: se usó **{self.url}**.",
            f"Revisa el nombre exacto de la base de datos: se usó **{self.db}**. En Odoo Online suele ser "
            "el subdominio (cliente.odoo.com → cliente); en Odoo.sh es el nombre que aparece en el panel "
            "de Odoo.sh (ej. proyecto-main-123456).",
            "Revisa que la API key sea del mismo usuario que pusiste en Login.",
        ]
        if any("404" in e for e in errors):
            hints.insert(0, "Un 404 indica que el servidor no reconoce la ruta de la API: URL con ruta extra, "
                            "base de datos inexistente, o la API externa no disponible en el plan de Odoo "
                            "Online (requiere plan Custom).")
        if any("401" in e or "403" in e or "rechazadas" in e for e in errors):
            hints.insert(0, "El servidor respondió pero rechazó el acceso: casi siempre es la API key, el "
                            "login o el nombre de la base.")
        return (f"No se pudo conectar ({ver}).\n\n" + "\n".join(f"- {e}" for e in errors)
                + "\n\n**Qué revisar:**\n" + "\n".join(f"- {h}" for h in hints))

    def _detect_version(self) -> None:
        # 1) /web/version (Odoo 17+, GET)
        try:
            r = self._session.get(f"{self.url}/web/version", timeout=20)
            if r.ok and "json" in r.headers.get("content-type", ""):
                data = r.json()
                self._set_version(data.get("version") or "", data.get("version_info"))
                if self.major:
                    return
        except Exception:  # noqa: BLE001
            pass
        # 2) /web/webclient/version_info (JSON-RPC, todas las versiones recientes)
        try:
            r = self._session.post(f"{self.url}/web/webclient/version_info",
                                   json={"jsonrpc": "2.0", "method": "call", "params": {}}, timeout=20)
            if r.ok and "json" in r.headers.get("content-type", ""):
                res = r.json().get("result") or {}
                self._set_version(res.get("server_version", ""), res.get("server_version_info"))
                if self.major:
                    return
        except Exception:  # noqa: BLE001
            pass
        # 3) XML-RPC common.version()
        try:
            common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common", allow_none=True)
            info = common.version()
            self._set_version(info.get("server_version", ""), info.get("server_version_info"))
        except Exception:  # noqa: BLE001
            self.version, self.major = "", 0

    def _set_version(self, version: str, info: Any) -> None:
        self.version = str(version)
        major = 0
        if isinstance(info, (list, tuple)) and info:
            first = str(info[0])
            major = int("".join(ch for ch in first if ch.isdigit()) or 0)
        if not major and self.version:
            digits = self.version.replace("saas~", "").split(".")[0]
            major = int("".join(ch for ch in digits if ch.isdigit()) or 0)
        self.major = major

    # --------------------------------------------------------------- llamadas
    def call(self, model: str, method: str, ids: list[int] | None = None, **params: Any) -> Any:
        """Llama un método del modelo. `params` siempre van con nombre."""
        if self.protocol == "xmlrpc":
            return self._call_xmlrpc(model, method, ids, params)
        return self._call_json2(model, method, ids, params)

    def _call_json2(self, model: str, method: str, ids: list[int] | None, params: dict) -> Any:
        body = dict(params)
        if ids is not None:
            body["ids"] = ids
        headers = {
            "Authorization": f"bearer {self.api_key}",
            "X-Odoo-Database": self.db,
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "odoo-demo-builder",
        }
        try:
            r = self._session.post(f"{self.url}/json/2/{model}/{method}", json=body,
                                   headers=headers, timeout=self.timeout)
        except requests.RequestException as exc:
            raise OdooError(f"Error de red: {exc}") from exc
        if r.ok:
            return r.json() if r.content else None
        ctype = r.headers.get("content-type", "")
        if "json" in ctype:
            try:
                err = r.json()
                msg = err.get("message") or err.get("name") or str(err)[:300]
            except ValueError:
                msg = r.text[:300]
        else:
            # Página HTML de error: no sirve mostrarla
            msg = {404: "la ruta /json/2 no existe en este servidor o la base no se encontró",
                   401: "API key inválida o no autorizada",
                   403: "acceso denegado"}.get(r.status_code, "respuesta inesperada del servidor")
        raise OdooError(f"{model}.{method}: {msg} (HTTP {r.status_code})")

    def _call_xmlrpc(self, model: str, method: str, ids: list[int] | None, params: dict) -> Any:
        obj = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object", allow_none=True)
        args: list = []
        kwargs = dict(params)
        # Métodos más comunes con argumento posicional
        if ids is not None:
            args = [ids]
        elif method == "create":
            args = [kwargs.pop("vals_list")]
        elif method in ("search_read", "search_count", "search"):
            args = [kwargs.pop("domain", [])]
        elif method == "name_search":
            args = [kwargs.pop("name", "")]
            if "domain" in kwargs:
                kwargs["args"] = kwargs.pop("domain")
        try:
            return obj.execute_kw(self.db, self.uid, self.api_key, model, method, args, kwargs)
        except xmlrpc.client.Fault as exc:
            msg = str(exc.faultString).strip().splitlines()
            raise OdooError(f"{model}.{method}: {msg[-1] if msg else exc}") from exc
        except Exception as exc:  # noqa: BLE001
            raise OdooError(f"{model}.{method}: {exc}") from exc

    # ---------------------------------------------------------- alto nivel
    def search_read(self, model: str, domain: list | None = None, fields: list[str] | None = None,
                    limit: int | None = None, order: str | None = None) -> list[dict]:
        params: dict[str, Any] = {"domain": domain or [], "fields": fields or []}
        if limit:
            params["limit"] = limit
        if order:
            params["order"] = order
        return self.call(model, "search_read", **params) or []

    def search_count(self, model: str, domain: list | None = None) -> int:
        return int(self.call(model, "search_count", domain=domain or []) or 0)

    def fields_get(self, model: str) -> dict:
        attrs = ["type", "string", "required", "readonly", "relation", "selection", "store", "help"]
        return self.call(model, "fields_get", attributes=attrs) or {}

    def create(self, model: str, vals: dict) -> int:
        res = self.call(model, "create", vals_list=[vals])
        if isinstance(res, list):
            return int(res[0])
        return int(res)

    def name_search(self, model: str, name: str, limit: int = 5) -> list:
        res = self.call(model, "name_search", name=name, limit=limit) or []
        return res

    def unlink(self, model: str, ids: list[int]) -> Any:
        return self.call(model, "unlink", ids=ids)

    def model_exists(self, model: str) -> bool:
        try:
            return bool(self.search_count("ir.model", [["model", "=", model]]))
        except OdooError:
            return False
