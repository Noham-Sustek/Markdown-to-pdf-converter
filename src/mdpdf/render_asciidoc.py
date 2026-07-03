"""AsciiDoc → HTML (asciidoc-py, diagrammes prétraités avant conversion)."""
from __future__ import annotations

import io
import re

from asciidoc.api import AsciiDocAPI

from . import diagrams
from .diagrams import LogFn

# Bloc diagramme AsciiDoc :  [mermaid] / [plantuml]  suivi d'un bloc ---- ou ....
_DIAGRAM_BLOCK_RE = re.compile(
    r"^\[(mermaid|plantuml|puml)(?:,[^\]\n]*)?\][ \t]*\n"
    r"(-{4,}|\.{4,})[ \t]*\n"
    r"(.*?)"
    r"\n\2[ \t]*$",
    re.MULTILINE | re.DOTALL,
)

_TITLE_RE = re.compile(r"^=\s+(.+?)\s*$", re.MULTILINE)


def _replace_diagrams(source: str, log: LogFn) -> str:
    def repl(match: re.Match[str]) -> str:
        kind, _delim, body = match.group(1), match.group(2), match.group(3)
        if kind == "mermaid":
            rendered = diagrams.mermaid_block(body)
        else:
            rendered = diagrams.plantuml_block(body, log)
        # Bloc passthrough AsciiDoc : le HTML est inséré tel quel.
        return f"++++\n{rendered}\n++++"

    return _DIAGRAM_BLOCK_RE.sub(repl, source)


def render(source: str, log: LogFn = print) -> tuple[str, str | None]:
    """Retourne (html, titre) ; le titre est celui du document (= Titre)."""
    source = _replace_diagrams(source, log)

    title_match = _TITLE_RE.search(source)
    title = title_match.group(1) if title_match else None

    api = AsciiDocAPI()
    api.options("--no-header-footer")
    api.attributes["source-highlighter"] = "pygments"
    # Pas de ressources externes : icônes désactivées, tout est inline.
    api.attributes["icons"] = None

    out = io.StringIO()
    api.execute(io.StringIO(source), out, backend="html5")
    body = out.getvalue()

    if title:
        body = f"<h1>{_escape(title)}</h1>\n{body}"
    return body, title


def _escape(text: str) -> str:
    import html

    return html.escape(text, quote=False)
