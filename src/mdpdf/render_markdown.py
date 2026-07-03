"""Markdown → HTML (markdown-it-py + Pygments, diagrammes délégués à diagrams)."""
from __future__ import annotations

import html

from markdown_it import MarkdownIt
from mdit_py_plugins.deflist import deflist_plugin
from mdit_py_plugins.footnote import footnote_plugin
from mdit_py_plugins.front_matter import front_matter_plugin
from mdit_py_plugins.tasklists import tasklists_plugin
from pygments import highlight as pygments_highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

from . import diagrams
from .diagrams import LogFn


def _highlight_code(code: str, lang: str, _attrs: str, log: LogFn) -> str:
    lang = (lang or "").strip().lower()
    if lang == "mermaid":
        return diagrams.mermaid_block(code)
    if lang in ("plantuml", "puml"):
        return diagrams.plantuml_block(code, log)

    escaped = None
    if lang:
        try:
            lexer = get_lexer_by_name(lang)
            formatter = HtmlFormatter(nowrap=True)
            escaped = pygments_highlight(code, lexer, formatter)
        except ClassNotFound:
            pass
    if escaped is None:
        escaped = html.escape(code)
    lang_class = f' class="language-{html.escape(lang)}"' if lang else ""
    return f'<pre class="highlight"><code{lang_class}>{escaped}</code></pre>'


def make_parser(log: LogFn = print) -> MarkdownIt:
    md = (
        MarkdownIt(
            "commonmark",
            {"highlight": lambda code, lang, attrs: _highlight_code(code, lang, attrs, log)},
        )
        .enable("table")
        .enable("strikethrough")
        .use(front_matter_plugin)
        .use(footnote_plugin)
        .use(deflist_plugin)
        .use(tasklists_plugin)
    )
    return md


def render(source: str, log: LogFn = print) -> tuple[str, str | None]:
    """Retourne (html, titre) ; le titre est le premier titre de niveau 1."""
    md = make_parser(log)
    tokens = md.parse(source)

    title: str | None = None
    for i, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag == "h1":
            inline = tokens[i + 1]
            title = inline.content.strip() or None
            break

    return md.renderer.render(tokens, md.options, {}), title
