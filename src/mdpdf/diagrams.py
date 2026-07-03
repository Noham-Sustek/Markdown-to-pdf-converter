"""Rendu des diagrammes.

- Mermaid : le bloc est transformé en <pre class="mermaid"> ; le rendu réel
  est effectué par mermaid.js (embarqué) dans le Chromium embarqué, hors-ligne.
- PlantUML : rendu en SVG via plantuml.jar et le JRE embarqué (processus local,
  aucun accès réseau : PLANTUML_SECURITY_PROFILE=SANDBOX).
"""
from __future__ import annotations

import html
import re
import subprocess
from typing import Callable

from . import paths

LogFn = Callable[[str], None]

_SVG_TAG_RE = re.compile(r"<svg\b", re.IGNORECASE)


def mermaid_block(source: str) -> str:
    return f'<pre class="mermaid">{html.escape(source)}</pre>'


def _fallback_block(source: str, message: str) -> str:
    return (
        f'<div class="diagram-error"><p>⚠ {html.escape(message)}</p>'
        f"<pre><code>{html.escape(source)}</code></pre></div>"
    )


def plantuml_block(source: str, log: LogFn = print) -> str:
    """Rend un diagramme PlantUML en SVG inline. Repli lisible en cas d'échec."""
    jar = paths.plantuml_jar()
    java = paths.find_java()
    if jar is None or java is None:
        missing = "plantuml.jar" if jar is None else "Java"
        log(f"  ⚠ PlantUML indisponible ({missing} introuvable) — bloc laissé en source")
        return _fallback_block(source, f"Diagramme PlantUML non rendu : {missing} introuvable.")

    text = source.strip()
    if "@start" not in text:
        text = f"@startuml\n{text}\n@enduml"

    try:
        proc = subprocess.run(
            [
                java,
                "-Djava.awt.headless=true",
                "-DPLANTUML_SECURITY_PROFILE=SANDBOX",
                "-jar",
                str(jar),
                # Layout Smetana (pur Java) : pas besoin de Graphviz, donc
                # les diagrammes de classes/composants marchent hors-ligne.
                "-Playout=smetana",
                "-tsvg",
                "-pipe",
                "-charset",
                "UTF-8",
            ],
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log(f"  ⚠ PlantUML : échec d'exécution ({exc})")
        return _fallback_block(source, "Diagramme PlantUML non rendu : échec d'exécution de Java.")

    svg = proc.stdout.decode("utf-8", errors="replace")
    match = _SVG_TAG_RE.search(svg)
    if match is None:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        log(f"  ⚠ PlantUML : pas de SVG produit ({stderr[:200]})")
        return _fallback_block(source, "Diagramme PlantUML non rendu : erreur de syntaxe ?")

    # PlantUML signale les erreurs de syntaxe par un SVG d'erreur + code retour ≠ 0 ;
    # on le garde tel quel : l'erreur est ainsi visible dans le PDF.
    svg = svg[match.start():]
    return f'<figure class="diagram plantuml">{svg}</figure>'
