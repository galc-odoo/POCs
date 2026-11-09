"""Manual de la prueba de concepto (PDF) para el consultor.

Explica qué datos se cargaron en la base, por qué (la lógica del análisis de
la IA) y, opcionalmente, un guión sugerido para presentar la demo.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from .fonts import BODY, BODY_BOLD, MONO, TITLE, TITLE_REGULAR, register, safe_text

ACCENT = colors.HexColor("#714B67")
LIGHT = colors.HexColor("#F3EEF2")
GREY = colors.HexColor("#5B5B5B")

CONTEXT_LABELS = {
    "cliente": "Cliente", "industria": "Giro / industria", "tamano_y_pais": "Tamaño y país",
    "sistemas_actuales": "Sistemas actuales", "procesos": "Procesos que opera",
    "dolores": "Dolores / problemas", "objetivo_demo": "Qué quiere ver en la demo",
    "notas_consultor": "Notas del consultor",
}


def plain(text) -> str:
    return safe_text(text)


def clean(text) -> str:
    """Texto seguro para las fuentes del PDF y para el marcado de Paragraph."""
    return escape(safe_text(text)).replace("\n", "<br/>")


def styles():
    """Estilos comunes de los manuales: títulos en Caveat, texto en Geist."""
    register()
    ss = getSampleStyleSheet()
    base = ParagraphStyle("base", parent=ss["Normal"], fontName=BODY, fontSize=9.5, leading=13.5)
    return {
        "base": base,
        "small": ParagraphStyle("small", parent=base, fontSize=8, leading=10.5),
        "muted": ParagraphStyle("muted", parent=base, textColor=GREY),
        "h1": ParagraphStyle("h1", parent=base, fontName=TITLE, fontSize=26, leading=30,
                             textColor=ACCENT, spaceBefore=8, spaceAfter=8),
        "h2": ParagraphStyle("h2", parent=base, fontName=TITLE, fontSize=19, leading=23,
                             textColor=ACCENT, spaceBefore=12, spaceAfter=5),
        "h3": ParagraphStyle("h3", parent=base, fontName=BODY_BOLD, fontSize=10.5, leading=14,
                             spaceBefore=7, spaceAfter=3),
        "title": ParagraphStyle("title", parent=base, fontName=TITLE, fontSize=46, leading=52,
                                textColor=ACCENT, alignment=TA_CENTER),
        "subtitle": ParagraphStyle("subtitle", parent=base, fontName=TITLE_REGULAR, fontSize=24, leading=28,
                                   alignment=TA_CENTER, textColor=GREY),
        "cell": ParagraphStyle("cell", parent=base, fontSize=8, leading=10.5),
        "cellb": ParagraphStyle("cellb", parent=base, fontSize=8, leading=10.5, fontName=BODY_BOLD,
                                textColor=colors.white),
        "code": ParagraphStyle("code", parent=base, fontName=MONO, fontSize=8, leading=11,
                               backColor=LIGHT, borderPadding=5, leftIndent=5, rightIndent=5,
                               spaceBefore=4, spaceAfter=6),
    }


_styles = styles


def _table(rows, widths, st, header=True):
    data = [[Paragraph(clean(c), st["cellb" if header and i == 0 else "cell"]) for c in r]
            for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D9D2D7")),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), ACCENT)]
        style += [("BACKGROUND", (0, i), (-1, i), LIGHT) for i in range(2, len(rows), 2)]
    t.setStyle(TableStyle(style))
    return t


def _bullets(items, st):
    return [Paragraph("- " + clean(x), st["base"]) for x in items or []]


# ------------------------------------------------------------ valores legibles
def label_for(valores: dict) -> str:
    for key in ("name", "display_name", "partner_id", "ref", "default_code"):
        v = valores.get(key)
        if isinstance(v, (str, int)) and v != "":
            return str(v)
    return ""


def _labels(plan: list[dict]) -> dict[str, str]:
    out = {}
    for step in plan:
        for r in step.get("registros", []):
            out[r.get("ref", "")] = label_for(r.get("valores", {})) or r.get("ref", "")
    return out


def _fmt(v, labels: dict[str, str]) -> str:
    if isinstance(v, str) and v.startswith("@"):
        return labels.get(v[1:], v[1:])
    if isinstance(v, str) and v.lower().startswith("$hoy"):
        return v.replace("$hoy", "hoy")
    if isinstance(v, dict):
        if "$buscar" in v:
            return str(v["$buscar"])
        return json.dumps(v, ensure_ascii=False)[:60]
    if isinstance(v, list):
        if v and all(isinstance(x, dict) for x in v):
            return f"{len(v)} línea(s)"
        return ", ".join(_fmt(x, labels) for x in v)
    if isinstance(v, bool):
        return "Sí" if v else "No"
    if isinstance(v, int) and not isinstance(v, bool):
        return str(v)
    return "" if v is None else str(v)


def _line_summary(rec: dict, labels: dict[str, str]) -> list[str]:
    out = []
    for field, val in rec.get("valores", {}).items():
        if isinstance(val, list) and val and all(isinstance(x, dict) for x in val):
            for line in val[:6]:
                parts = [f"{k}: {_fmt(x, labels)}" for k, x in list(line.items())[:4]]
                out.append(f"{rec.get('ref')} / {field}: " + "; ".join(parts))
    return out


def summary_for_ai(sess: dict) -> list[dict]:
    """Resumen compacto de lo cargado, para pedir el guión a la IA."""
    created = {c["ref"] for c in sess.get("creados", [])}
    labels = _labels(sess.get("plan", []))
    out = []
    for step in sess.get("plan", []):
        regs = [r for r in step.get("registros", []) if r.get("ref") in created]
        out.append({"modelo": step["model"],
                    "descripcion": sess.get("meta", {}).get("descripciones", {}).get(step["model"], ""),
                    "registros": len(regs),
                    "ejemplos": [{k: _fmt(v, labels) for k, v in list(r.get("valores", {}).items())[:6]}
                                 for r in regs[:5]]})
    return out


# ------------------------------------------------------------------- PDF
def build_pdf(sess: dict, guion: dict | None = None, out_path: str | None = None) -> str:
    st = _styles()
    meta = sess.get("meta", {})
    ctx = meta.get("contexto", {})
    an = meta.get("analisis", {}) or {}
    plan = sess.get("plan", [])
    names = meta.get("nombres_modelos", {})
    motivos = meta.get("motivos", {})
    descs = meta.get("descripciones", {})
    campos_motivo = meta.get("campos_motivo", {})
    labels = _labels(plan)
    created = sess.get("creados", [])
    created_refs = {c["ref"] for c in created}
    errors = sess.get("errores", [])
    cliente = ctx.get("cliente") or sess.get("titulo") or "Cliente"
    W = letter[0] - 3.6 * cm

    path = out_path or str(Path(sess["archivo"]).with_suffix(".pdf"))
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                            topMargin=2 * cm, bottomMargin=1.8 * cm,
                            title=f"Manual PoC - {cliente}", author="Generador de demos Odoo")

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont(BODY, 7.5)
        canvas.setFillColor(GREY)
        canvas.drawString(1.8 * cm, 1.1 * cm, plain(f"Manual de la prueba de concepto - {cliente}"))
        canvas.drawRightString(letter[0] - 1.8 * cm, 1.1 * cm, f"Página {d.page}")
        canvas.restoreState()

    s: list = []
    # ---------- portada
    s += [Spacer(1, 5 * cm), Paragraph("Manual de la prueba de concepto", st["title"]), Spacer(1, 10),
          Paragraph(clean(cliente), st["subtitle"]), Spacer(1, 1.5 * cm)]
    fecha = sess.get("fecha", datetime.now().isoformat())[:16].replace("T", " ")
    s.append(_table([["Base de datos", sess.get("db", "")], ["URL", sess.get("url", "")],
                     ["Versión de Odoo", meta.get("version", "")], ["Fecha de carga", fecha],
                     ["Nombre de la carga", sess.get("titulo", "")],
                     ["Consultor", meta.get("consultor", "") or "-"],
                     ["Análisis generado con", meta.get("ia", "")],
                     ["Registros creados", str(len(created))]],
                    [5 * cm, W - 5 * cm], st, header=False))
    s += [Spacer(1, 1 * cm), Paragraph(
        "Documento de apoyo para el consultor: describe qué información de prueba se cargó en la base, "
        "la lógica detrás de cada decisión y cómo aprovecharla durante la presentación.", st["muted"]),
          PageBreak()]

    # ---------- 1. contexto
    s.append(Paragraph("1. Contexto del cliente", st["h1"]))
    rows = [["Concepto", "Detalle"]] + [[CONTEXT_LABELS.get(k, k), v] for k, v in ctx.items() if v]
    if len(rows) > 1:
        s.append(_table(rows, [4.5 * cm, W - 4.5 * cm], st))
    if meta.get("notas_obsidian"):
        s += [Spacer(1, 6), Paragraph("Notas de la base de conocimiento (Obsidian) consideradas:", st["h3"])]
        s += _bullets(meta["notas_obsidian"], st)

    # ---------- 2. enfoque
    s.append(Paragraph("2. Enfoque de la demo y lógica del análisis", st["h1"]))
    if an.get("resumen"):
        s.append(Paragraph(clean(an["resumen"]), st["base"]))
    if an.get("procesos_a_demostrar"):
        s.append(Paragraph("Procesos que se demostrarán", st["h3"]))
        s += _bullets(an["procesos_a_demostrar"], st)
    if motivos:
        s.append(Paragraph("Por qué se eligió cada tipo de información", st["h3"]))
        s.append(_table([["Información", "Modelo", "Razón"]] +
                        [[names.get(m, m), m, motivos.get(m, "")] for m in [p["model"] for p in plan]],
                        [4 * cm, 4 * cm, W - 8 * cm], st))
    if an.get("recomendaciones"):
        s.append(Paragraph("Recomendaciones de configuración", st["h3"]))
        s += _bullets(an["recomendaciones"], st)
    if an.get("preguntas_al_consultor"):
        s.append(Paragraph("Preguntas abiertas para validar con el cliente", st["h3"]))
        s += _bullets(an["preguntas_al_consultor"], st)

    # ---------- 3. resumen de carga
    s.append(Paragraph("3. Resumen de datos cargados", st["h1"]))
    err_by_model: dict[str, int] = {}
    for e in errors:
        err_by_model[e["model"]] = err_by_model.get(e["model"], 0) + 1
    cnt: dict[str, int] = {}
    for c in created:
        cnt[c["model"]] = cnt.get(c["model"], 0) + 1
    acts = {}
    for a in sess.get("acciones_ok", []):
        acts.setdefault(a["model"], []).append(a.get("descripcion") or a["metodo"])
    rows = [["Orden", "Información", "Creados", "Errores", "Acciones aplicadas"]]
    for i, step in enumerate(plan, 1):
        m = step["model"]
        rows.append([str(i), f"{names.get(m, m)} ({m})", str(cnt.get(m, 0)), str(err_by_model.get(m, 0)),
                     ", ".join(acts.get(m, [])) or "-"])
    s.append(_table(rows, [1.3 * cm, 6.2 * cm, 1.8 * cm, 1.8 * cm, W - 11.1 * cm], st))
    s.append(Spacer(1, 4))
    s.append(Paragraph("El orden refleja las dependencias: primero se cargan los catálogos que los "
                       "documentos posteriores necesitan (por ejemplo, contactos y productos antes que "
                       "pedidos o facturas).", st["muted"]))

    # ---------- 4. detalle por modelo
    s += [PageBreak(), Paragraph("4. Detalle de la información cargada", st["h1"])]
    for i, step in enumerate(plan, 1):
        m = step["model"]
        regs = [r for r in step.get("registros", []) if r.get("ref") in created_refs]
        block = [Paragraph(clean(f"4.{i} {names.get(m, m)}  ({m})"), st["h2"])]
        if descs.get(m):
            block.append(Paragraph(f"<b>Qué representa:</b> {clean(descs[m])}", st["base"]))
        if motivos.get(m):
            block.append(Paragraph(f"<b>Por qué se cargó:</b> {clean(motivos[m])}", st["base"]))
        s.append(KeepTogether(block))

        fields = step.get("campos") or []
        fm = campos_motivo.get(m, {})
        if fields:
            s.append(Paragraph("Campos que se llenaron y para qué sirven", st["h3"]))
            s.append(_table([["Campo", "Uso en la demo"]] + [[f, fm.get(f, "")] for f in fields],
                            [4.5 * cm, W - 4.5 * cm], st))

        if regs:
            s.append(Paragraph(f"Registros creados ({len(regs)})", st["h3"]))
            cols = [f for f in fields if any(f in r.get("valores", {}) for r in regs)][:5]
            if not cols:
                cols = list(regs[0].get("valores", {}))[:5]
            rows = [["Referencia", *cols]]
            for r in regs[:30]:
                rows.append([r.get("ref", ""), *[_fmt(r["valores"].get(c, ""), labels)[:80] for c in cols]])
            wref = 3.2 * cm
            s.append(_table(rows, [wref] + [(W - wref) / max(len(cols), 1)] * len(cols), st))
            if len(regs) > 30:
                s.append(Paragraph(f"... y {len(regs) - 30} registros más.", st["muted"]))
            lines = [ln for r in regs[:10] for ln in _line_summary(r, labels)]
            if lines:
                s.append(Paragraph("Detalle de líneas (muestra)", st["h3"]))
                s += [Paragraph(clean(ln), st["small"]) for ln in lines[:25]]
        else:
            s.append(Paragraph("No se creó ningún registro de este tipo (ver incidencias).", st["muted"]))
        if acts.get(m):
            s.append(Paragraph("<b>Acciones aplicadas después de crear:</b> " + clean(", ".join(acts[m])),
                               st["base"]))

    # ---------- 5. guión
    if guion and guion.get("pasos"):
        s += [PageBreak(), Paragraph("5. Guión sugerido para la presentación", st["h1"])]
        if guion.get("introduccion"):
            s.append(Paragraph(clean(guion["introduccion"]), st["base"]))
        for j, p in enumerate(guion["pasos"], 1):
            blk = [Paragraph(clean(f"Paso {j}. {p.get('titulo', '')}"), st["h3"])]
            for label, key in (("Dónde", "menu"), ("Qué mostrar", "que_mostrar"),
                               ("Datos a usar", "datos"), ("Mensaje clave", "mensaje_clave")):
                if p.get(key):
                    blk.append(Paragraph(f"<b>{label}:</b> {clean(p[key])}", st["base"]))
            s.append(KeepTogether(blk))
        if guion.get("cierre"):
            s += [Paragraph("Cierre", st["h3"]), Paragraph(clean(guion["cierre"]), st["base"])]

    # ---------- 6. incidencias
    n = 6 if guion and guion.get("pasos") else 5
    s.append(Paragraph(f"{n}. Incidencias y notas técnicas", st["h1"]))
    if errors:
        s.append(Paragraph("Registros que Odoo no aceptó", st["h3"]))
        s.append(_table([["Modelo", "Referencia", "Motivo"]] +
                        [[e["model"], e["ref"], e["error"][:300]] for e in errors],
                        [4 * cm, 3.5 * cm, W - 7.5 * cm], st))
    else:
        s.append(Paragraph("Todos los registros planeados se crearon sin errores.", st["base"]))
    if sess.get("advertencias"):
        s.append(Paragraph("Advertencias", st["h3"]))
        s += [Paragraph("- " + clean(w), st["small"]) for w in sess["advertencias"][:40]]
    s += [Paragraph("Cómo revertir esta carga", st["h3"]),
          Paragraph("En Claude, abre una conversación, adjunta el <b>expediente JSON</b> de esta carga ("
                    + clean(Path(sess.get("archivo", "expediente.json")).name) + ") y pide <b>deshacer la carga "
                    "de demo</b> de la base <b>" + clean(sess.get("db", "")) + "</b>, con los datos de conexión. "
                    "Se borrarán en orden inverso todos los registros listados en este documento.", st["base"])]

    doc.build(s, onFirstPage=lambda c, d: None, onLaterPages=footer)
    return path
