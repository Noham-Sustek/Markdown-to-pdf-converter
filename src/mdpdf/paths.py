"""Résolution des chemins : ressources embarquées, Chromium, JRE, PlantUML.

L'application fonctionne dans deux modes :
  - développement : les fichiers sont dans le dépôt (src/mdpdf/assets, vendor/)
  - portable (PyInstaller) : les assets sont dans _internal/, le dossier
    vendor/ (Chromium, JRE, plantuml.jar) est à côté de l'exécutable.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def assets_dir() -> Path:
    if is_frozen():
        return Path(sys._MEIPASS) / "mdpdf" / "assets"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent / "assets"


def app_dir() -> Path:
    """Racine du dossier portable (ou du dépôt en développement)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def vendor_dir() -> Path:
    return app_dir() / "vendor"


def browsers_dir() -> Path | None:
    """Dossier des navigateurs Playwright embarqués, s'il existe."""
    path = vendor_dir() / "browsers"
    return path if path.is_dir() else None


def chromium_executable() -> str | None:
    """Chemin explicite vers Chromium (variable MDPDF_CHROMIUM), sinon None.

    None signifie « laisser Playwright trouver le navigateur », soit dans
    vendor/browsers (via PLAYWRIGHT_BROWSERS_PATH), soit dans son cache.
    """
    exe = os.environ.get("MDPDF_CHROMIUM")
    return exe if exe else None


def find_java() -> str | None:
    """JRE embarqué en priorité, sinon le java du système."""
    java_name = "java.exe" if os.name == "nt" else "java"
    embedded = vendor_dir() / "jre" / "bin" / java_name
    if embedded.exists():
        return str(embedded)
    return shutil.which("java")


def plantuml_jar() -> Path | None:
    jar = vendor_dir() / "plantuml" / "plantuml.jar"
    return jar if jar.exists() else None


def read_asset(relative: str) -> str:
    return (assets_dir() / relative).read_text(encoding="utf-8")
