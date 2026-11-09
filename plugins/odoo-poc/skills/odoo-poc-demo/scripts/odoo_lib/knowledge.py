"""Lectura de la base de conocimiento de Obsidian.

Un vault de Obsidian es una carpeta de archivos Markdown, así que se lee
directo del disco: no requiere plugins ni que Obsidian esté abierto.
"""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

SKIP_DIRS = {".obsidian", ".trash", ".git", "node_modules"}
STOPWORDS = set("""a al algo con como de del el en es esta este ha la las le lo los mas me mi muy
no o para pero por que se si sin sobre su sus te tiene un una uno unos y ya the and of to for in on
is are be cliente clientes empresa quiere necesita demo""".split())


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def _terms(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9_]{3,}", _norm(text)) if t not in STOPWORDS]


@dataclass
class Note:
    path: Path
    rel: str
    title: str
    text: str
    tags: list[str]


class Vault:
    def __init__(self, root: str):
        self.root = Path(os.path.expanduser(root)).resolve()
        self.notes: list[Note] = []

    def load(self) -> int:
        if not self.root.is_dir():
            raise FileNotFoundError(f"No existe la carpeta del vault: {self.root}")
        self.notes = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                if not fn.lower().endswith(".md"):
                    continue
                p = Path(dirpath) / fn
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                tags = re.findall(r"(?:^|\s)#([\w/\-áéíóúñ]+)", text)
                self.notes.append(Note(p, str(p.relative_to(self.root)), p.stem, text, tags))
        return len(self.notes)

    def titles(self) -> list[str]:
        return sorted(n.rel for n in self.notes)

    def search(self, query: str, k: int = 6, folder: str = "") -> list[Note]:
        q = _terms(query)
        if not q:
            return []
        scored = []
        for n in self.notes:
            if folder and not n.rel.lower().startswith(folder.lower().strip("/")):
                continue
            body = _norm(n.text)
            head = _norm(n.title + " " + " ".join(n.tags))
            score = 0.0
            for t in set(q):
                c = body.count(t)
                if c:
                    score += 1 + min(c, 10) * 0.3
                if t in head:
                    score += 4
            if score:
                scored.append((score, n))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [n for _, n in scored[:k]]

    def get(self, rel_paths: list[str]) -> list[Note]:
        wanted = set(rel_paths)
        return [n for n in self.notes if n.rel in wanted]


def notes_to_context(notes: list[Note], max_chars: int = 3000) -> str:
    parts = []
    for n in notes:
        text = n.text.strip()
        if len(text) > max_chars:
            text = text[:max_chars] + "\n[...nota recortada...]"
        parts.append(f"### Nota: {n.rel}\n{text}")
    return "\n\n".join(parts)
