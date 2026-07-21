"""Assemblage du document HTML final : identifiants, sommaire, thème, gabarit."""
from __future__ import annotations

import base64
import datetime
import html
import mimetypes
import re
import unicodedata
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from pygments.formatters import HtmlFormatter

from . import paths

_HEADING_RE = re.compile(r"<h([1-4])([^>]*)>(.*?)</h\1>", re.DOTALL | re.IGNORECASE)
_ID_ATTR_RE = re.compile(r'\bid\s*=\s*"([^"]*)"')
_TAG_RE = re.compile(r"<[^>]+>")
# Attribut src d'une balise <img> (guillemets simples ou doubles).
_IMG_SRC_RE = re.compile(r'(<img\b[^>]*?\bsrc\s*=\s*)(["\'])(.*?)\2', re.IGNORECASE | re.DOTALL)

LogFn = Callable[[str], None]


@dataclass
class TocEntry:
    level: int
    text: str
    anchor: str


@dataclass
class Section:
    """Un document source rendu en HTML, prêt à être assemblé."""

    html: str
    title: str
    source_name: str
    toc_entries: list[TocEntry] = field(default_factory=list)


def slugify(text: str, used: set[str]) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    # Un identifiant CSS ne peut pas commencer par un chiffre : paged.js passe
    # l'ancre à querySelector('#...') sans échappement pour calculer les numéros
    # de page du sommaire, ce qui lèverait « is not a valid selector » pour un
    # titre comme « 1. Introduction ». On préfixe alors le slug.
    if not slug:
        slug = "section"
    elif slug[0].isdigit():
        slug = f"section-{slug}"
    candidate = slug
    counter = 2
    while candidate in used:
        candidate = f"{slug}-{counter}"
        counter += 1
    used.add(candidate)
    return candidate


def add_heading_ids(body: str, used_ids: set[str]) -> tuple[str, list[TocEntry]]:
    """Ajoute un id aux titres h1-h4 et collecte les entrées du sommaire."""
    entries: list[TocEntry] = []

    def repl(match: re.Match[str]) -> str:
        level, attrs, inner = int(match.group(1)), match.group(2), match.group(3)
        text = _TAG_RE.sub("", inner)
        text = html.unescape(text).strip()
        id_match = _ID_ATTR_RE.search(attrs)
        if id_match and id_match.group(1):
            anchor = id_match.group(1)
            used_ids.add(anchor)
        else:
            anchor = slugify(text, used_ids)
            attrs = f'{attrs} id="{anchor}"'
        entries.append(TocEntry(level, text, anchor))
        return f"<h{level}{attrs}>{inner}</h{level}>"

    return _HEADING_RE.sub(repl, body), entries


def build_toc(entries: list[TocEntry], max_level: int = 3, heading: str = "Sommaire") -> str:
    items = [e for e in entries if e.level <= max_level]
    if not items:
        return ""
    parts = [f'<nav class="toc"><h1 class="toc-title">{html.escape(heading)}</h1>']
    current = 0
    for entry in items:
        while current < entry.level:
            parts.append("<ol>")
            current += 1
        while current > entry.level:
            parts.append("</ol>")
            current -= 1
        parts.append(
            f'<li><a href="#{entry.anchor}">{html.escape(entry.text)}</a></li>'
        )
    parts.append("</ol>" * current)
    parts.append("</nav>")
    return "\n".join(parts)


def image_data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def embed_local_images(body: str, base_dir: Path, log: LogFn = print) -> str:
    """Remplace les images locales des balises <img> par des data URI base64.

    Les chemins relatifs sont résolus par rapport au dossier du document source.
    Les images déjà en data: sont laissées telles quelles ; les images distantes
    (http/https) ne sont PAS téléchargées (fonctionnement 100% hors-ligne) et
    sont signalées. Le PDF produit est ainsi entièrement autonome.
    """
    def repl(match: re.Match[str]) -> str:
        prefix, quote, src = match.group(1), match.group(2), match.group(3)
        value = src.strip()
        low = value.lower()
        if low.startswith("data:"):
            return match.group(0)
        if low.startswith(("http://", "https://", "ftp://", "//")):
            log(f"  ⚠ image distante non embarquée (hors-ligne) : {value}")
            return match.group(0)
        # Chemin de fichier local : on retire une éventuelle ancre / requête.
        raw = urllib.parse.unquote(value.split("#", 1)[0].split("?", 1)[0])
        path = Path(raw)
        if not path.is_absolute():
            path = base_dir / path
        try:
            uri = image_data_uri(path)
        except OSError:
            log(f"  ⚠ image introuvable, ignorée : {value}")
            return match.group(0)
        return f"{prefix}{quote}{uri}{quote}"

    return _IMG_SRC_RE.sub(repl, body)


def _css_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def watermark_css(text: str | None) -> str:
    """Filigrane en diagonale répété sur chaque page (via paged.js)."""
    if not text or not text.strip():
        return ""
    value = _css_string(text.strip())
    # Le pseudo-élément est ajouté à chaque page produite par paged.js.
    return (
        ".pagedjs_pagebox { position: relative; }\n"
        ".pagedjs_pagebox::after {\n"
        f"  content: {value};\n"
        "  position: absolute;\n"
        "  top: 50%;\n"
        "  left: 50%;\n"
        "  transform: translate(-50%, -50%) rotate(-45deg);\n"
        "  transform-origin: center;\n"
        "  font-family: 'Segoe UI', Arial, sans-serif;\n"
        "  font-size: 68pt;\n"
        "  font-weight: 700;\n"
        "  letter-spacing: 0.08em;\n"
        "  color: rgba(200, 0, 0, 0.10);\n"
        "  white-space: nowrap;\n"
        "  pointer-events: none;\n"
        "  z-index: 9999;\n"
        "}"
    )


def page_options_css(
    header_left: str | None,
    header_right: str | None,
    footer_text: str | None,
) -> str:
    """CSS généré à partir des options --header-* / --footer de l'utilisateur."""
    rules = []
    if header_left:
        rules.append(f"@top-left {{ content: {_css_string(header_left)}; }}")
    if header_right:
        rules.append(f"@top-right {{ content: {_css_string(header_right)}; }}")
    if footer_text:
        rules.append(f"@bottom-left {{ content: {_css_string(footer_text)}; }}")
    if not rules:
        return ""
    return "@page {\n  " + "\n  ".join(rules) + "\n}"


def assemble(
    sections: list[Section],
    *,
    title: str,
    toc: bool = True,
    toc_depth: int = 3,
    theme_css: str | None = None,
    logo: Path | None = None,
    cover: bool = False,
    header_left: str | None = None,
    header_right: str | None = None,
    footer_text: str | None = None,
    watermark: str | None = None,
    lang: str = "fr",
) -> str:
    """Construit la page HTML complète, autonome (aucune ressource externe)."""
    default_css = paths.read_asset("themes/default.css")
    pygments_css = HtmlFormatter(style="default").get_style_defs(
        [".highlight", ".listingblock .content"]
    )
    mermaid_js = paths.read_asset("vendor/mermaid.min.js")
    paged_js = paths.read_asset("vendor/paged.polyfill.min.js")
    template = paths.read_asset("template.html")

    body_parts: list[str] = []

    if cover:
        logo_html = (
            f'<img class="cover-logo" src="{image_data_uri(logo)}" alt="logo">' if logo else ""
        )
        today = datetime.date.today().strftime("%d/%m/%Y")
        body_parts.append(
            '<section class="cover">'
            f"{logo_html}"
            f"<h1>{html.escape(title)}</h1>"
            f'<p class="cover-date">{today}</p>'
            "</section>"
        )

    all_entries: list[TocEntry] = []
    for section in sections:
        all_entries.extend(section.toc_entries)

    if toc:
        body_parts.append(build_toc(all_entries, toc_depth))

    for i, section in enumerate(sections):
        cls = "doc first-doc" if i == 0 else "doc"
        body_parts.append(f'<section class="{cls}">\n{section.html}\n</section>')

    replacements = {
        "__MDPDF_LANG__": html.escape(lang),
        "__MDPDF_TITLE__": html.escape(title),
        "__MDPDF_PYGMENTS_CSS__": pygments_css,
        "__MDPDF_DEFAULT_CSS__": default_css,
        "__MDPDF_OPTIONS_CSS__": page_options_css(header_left, header_right, footer_text),
        "__MDPDF_USER_CSS__": theme_css or "",
        "__MDPDF_WATERMARK_CSS__": watermark_css(watermark),
        "__MDPDF_BODY__": "\n".join(body_parts),
        "__MDPDF_MERMAID_JS__": mermaid_js,
        "__MDPDF_PAGED_JS__": paged_js,
    }
    page = template
    for token, value in replacements.items():
        page = page.replace(token, value)
    return page
