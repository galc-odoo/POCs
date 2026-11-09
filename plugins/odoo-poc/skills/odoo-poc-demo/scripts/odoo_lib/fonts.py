"""Fuentes de los manuales PDF: Caveat para títulos y Geist para el texto.

Los archivos .ttf vienen incluidos en assets/fonts (licencia SIL Open Font
License), así que no hace falta instalarlas en la computadora.
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"

TITLE = "Caveat-Bold"        # títulos principales
TITLE_REGULAR = "Caveat"
BODY = "Geist"               # texto
BODY_BOLD = "Geist-Bold"
MONO = "GeistMono"

_FILES = {
    "Caveat": "Caveat-Regular.ttf",
    "Caveat-Bold": "Caveat-Bold.ttf",
    "Geist": "Geist-Regular.ttf",
    "Geist-Bold": "Geist-Bold.ttf",
    "GeistMono": "GeistMono-Regular.ttf",
}
_registered = False
_cmap: set[int] = set()


def register() -> None:
    """Registra las fuentes en reportlab (una sola vez)."""
    global _registered, _cmap
    if _registered:
        return
    for name, fn in _FILES.items():
        path = FONT_DIR / fn
        if not path.exists():
            raise FileNotFoundError(f"Falta la fuente {fn} en {FONT_DIR}")
        pdfmetrics.registerFont(TTFont(name, str(path)))
    # Permite <b>...</b> dentro de los párrafos con Geist
    addMapping(BODY, 0, 0, BODY)
    addMapping(BODY, 1, 0, BODY_BOLD)
    addMapping(BODY, 0, 1, BODY)
    addMapping(BODY, 1, 1, BODY_BOLD)
    addMapping(TITLE_REGULAR, 1, 0, TITLE)
    addMapping(TITLE_REGULAR, 0, 0, TITLE_REGULAR)
    _cmap = set(pdfmetrics.getFont(BODY).face.charToGlyph.keys())
    _registered = True


_REPL = {"•": "-", " ": " ", "→": "->", "←": "<-", "≤": "<=", "≥": ">="}


def safe_text(text) -> str:
    """Quita caracteres que Geist no puede dibujar (emojis, símbolos raros)."""
    register()
    s = "" if text is None else str(text)
    for a, b in _REPL.items():
        if ord(a) not in _cmap:
            s = s.replace(a, b)
    return "".join(c for c in s if c in "\n\t" or ord(c) in _cmap)
