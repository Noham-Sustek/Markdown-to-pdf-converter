"""Chaîne de conversion complète : fichiers sources → PDF.

Modes :
  - fichier par fichier : chaque source produit son propre PDF ;
  - fusion (merge) : toutes les sources sont assemblées en un seul PDF,
    avec page de couverture optionnelle et sommaire global.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import document, pdf, render_asciidoc, render_markdown
from .diagrams import LogFn

MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdown", ".mkd"}
ASCIIDOC_SUFFIXES = {".adoc", ".asciidoc", ".asc"}
ALL_SUFFIXES = MARKDOWN_SUFFIXES | ASCIIDOC_SUFFIXES

# Marqueur d'emplacement du sommaire, sur une ligne seule. Accepté dans les deux
# formats : [TOC], [[TOC]], [[_TOC_]], {{toc}}, <!-- toc -->, et toc::[] (AsciiDoc).
_TOC_MARKER_RE = re.compile(
    r"^[ \t]*(?:"
    r"\[TOC\]|\[\[TOC\]\]|\[\[_TOC_\]\]|"
    r"\{\{\s*toc\s*\}\}|"
    r"<!--\s*toc\s*-->|"
    r"toc::\[\]"
    r")[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)


def _apply_toc_marker(text: str, is_asciidoc: bool) -> str:
    """Remplace un marqueur de sommaire par un bloc HTML repère qui survit au
    rendu (passthrough AsciiDoc / bloc HTML Markdown). document.assemble y
    insérera ensuite le sommaire."""
    if is_asciidoc:
        replacement = f"\n\n++++\n{document.TOC_PLACEHOLDER}\n++++\n\n"
    else:
        replacement = f"\n\n{document.TOC_PLACEHOLDER}\n\n"
    return _TOC_MARKER_RE.sub(replacement, text)


class ConversionError(RuntimeError):
    pass


@dataclass
class Options:
    merge: bool = False
    title: str | None = None
    toc: bool = True
    toc_depth: int = 3
    theme: Path | None = None
    logo: Path | None = None
    header_left: str | None = None
    header_right: str | None = None
    footer: str | None = None
    watermark: str | None = None
    lang: str = "fr"
    output: Path | None = None
    output_dir: Path | None = None
    log: LogFn = field(default=print)


def collect_sources(inputs: list[Path]) -> list[Path]:
    """Développe les dossiers (récursivement) en liste de fichiers convertibles."""
    sources: list[Path] = []
    for item in inputs:
        if item.is_dir():
            found = sorted(
                p for p in item.rglob("*")
                if p.is_file() and p.suffix.lower() in ALL_SUFFIXES
            )
            sources.extend(found)
        elif item.is_file():
            if item.suffix.lower() not in ALL_SUFFIXES:
                raise ConversionError(
                    f"Format non pris en charge : {item.name} "
                    f"(extensions acceptées : {', '.join(sorted(ALL_SUFFIXES))})"
                )
            sources.append(item)
        else:
            raise ConversionError(f"Fichier ou dossier introuvable : {item}")
    # Déduplication en conservant l'ordre.
    seen: set[Path] = set()
    unique = []
    for src in sources:
        resolved = src.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(src)
    if not unique:
        raise ConversionError("Aucun fichier .md ou .adoc trouvé dans les entrées.")
    return unique


def render_source(source: Path, log: LogFn) -> document.Section:
    text = source.read_text(encoding="utf-8-sig")
    is_asciidoc = source.suffix.lower() in ASCIIDOC_SUFFIXES
    text = _apply_toc_marker(text, is_asciidoc)
    if is_asciidoc:
        body, title = render_asciidoc.render(text, log)
    else:
        body, title = render_markdown.render(text, log)
    # Images locales → data URI, résolues par rapport au dossier du document.
    body = document.embed_local_images(body, source.parent, log)
    return document.Section(
        html=body,
        title=title or source.stem,
        source_name=source.name,
    )


def _finalize_sections(sections: list[document.Section]) -> None:
    """Ajoute les identifiants de titres (uniques sur tout le document final)."""
    used_ids: set[str] = set()
    for section in sections:
        section.html, section.toc_entries = document.add_heading_ids(
            section.html, used_ids
        )


def _read_theme(theme: Path | None) -> str | None:
    if theme is None:
        return None
    if not theme.is_file():
        raise ConversionError(f"Thème introuvable : {theme}")
    return theme.read_text(encoding="utf-8-sig")


def convert(inputs: list[Path], options: Options) -> list[Path]:
    """Convertit les entrées et retourne la liste des PDF produits."""
    log = options.log
    sources = collect_sources(inputs)
    theme_css = _read_theme(options.theme)

    if options.logo and not options.logo.is_file():
        raise ConversionError(f"Logo introuvable : {options.logo}")

    outputs: list[Path] = []

    if options.merge:
        log(f"Fusion de {len(sources)} document(s) en un PDF…")
        sections = []
        for src in sources:
            log(f"  • {src.name}")
            sections.append(render_source(src, log))
        _finalize_sections(sections)

        title = options.title or sections[0].title
        output = options.output or (
            (options.output_dir or sources[0].parent) / f"{_safe_name(title)}.pdf"
        )
        html = document.assemble(
            sections,
            title=title,
            toc=options.toc,
            toc_depth=options.toc_depth,
            theme_css=theme_css,
            logo=options.logo,
            cover=True,
            header_left=options.header_left,
            header_right=options.header_right,
            footer_text=options.footer,
            watermark=options.watermark,
            lang=options.lang,
        )
        log(f"Génération du PDF : {output}")
        pdf.html_to_pdf(html, output, log)
        outputs.append(output)
    else:
        used_outputs: set[Path] = set()
        for src in sources:
            log(f"Conversion : {src.name}")
            section = render_source(src, log)
            _finalize_sections([section])

            if options.output and len(sources) == 1:
                output = options.output
            else:
                out_dir = options.output_dir or src.parent
                output = out_dir / f"{src.stem}.pdf"
                # Évite qu'exemple.md et exemple.adoc s'écrasent mutuellement.
                counter = 2
                while output.resolve() in used_outputs:
                    output = out_dir / f"{src.stem}-{counter}.pdf"
                    counter += 1
            used_outputs.add(output.resolve())

            html = document.assemble(
                [section],
                title=options.title or section.title,
                toc=options.toc,
                toc_depth=options.toc_depth,
                theme_css=theme_css,
                logo=options.logo,
                cover=False,
                header_left=options.header_left,
                header_right=options.header_right,
                footer_text=options.footer,
                watermark=options.watermark,
                lang=options.lang,
            )
            log(f"  → {output}")
            pdf.html_to_pdf(html, output, log)
            outputs.append(output)

    log(f"Terminé : {len(outputs)} PDF généré(s).")
    return outputs


def _safe_name(title: str) -> str:
    keep = "".join(c if c.isalnum() or c in " ._-" else "_" for c in title).strip()
    return keep or "document"
