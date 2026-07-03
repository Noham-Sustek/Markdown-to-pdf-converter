#!/usr/bin/env python3
"""Télécharge les ressources embarquées dans l'application (exécuté au BUILD uniquement).

L'application finale est 100% hors-ligne : ces fichiers sont inclus dans le
paquet portable et plus aucun accès réseau n'a lieu à l'exécution.

  - mermaid.min.js    → rendu des diagrammes Mermaid (dans Chromium embarqué)
  - paged.polyfill.js → pagination CSS (numéros de page, sommaire, en-têtes)
  - plantuml.jar      → rendu des diagrammes PlantUML (via le JRE embarqué)

Les bibliothèques JS sont récupérées depuis le registre npm officiel
(tarballs signés des paquets publiés), PlantUML depuis ses releases GitHub.
"""
from __future__ import annotations

import io
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR_JS = ROOT / "src" / "mdpdf" / "assets" / "vendor"
VENDOR_PLANTUML = ROOT / "vendor" / "plantuml"

MERMAID_VERSION = "11.4.1"
PAGEDJS_VERSION = "0.4.3"
PLANTUML_VERSION = "1.2025.2"


def fetch(url: str) -> bytes:
    print(f"  {url}")
    with urllib.request.urlopen(url) as resp:
        return resp.read()


def extract_from_npm(package: str, version: str, member: str, dest: Path) -> None:
    """Extrait un fichier du tarball npm officiel d'un paquet."""
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  déjà présent : {dest.relative_to(ROOT)}")
        return
    url = f"https://registry.npmjs.org/{package}/-/{package}-{version}.tgz"
    data = fetch(url)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        fileobj = tar.extractfile(f"package/{member}")
        if fileobj is None:
            raise RuntimeError(f"{member} introuvable dans le tarball de {package}")
        content = fileobj.read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    print(f"  → {dest.relative_to(ROOT)} ({len(content) // 1024} Ko)")


def download_plantuml(dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  déjà présent : {dest.relative_to(ROOT)}")
        return
    urls = [
        "https://repo1.maven.org/maven2/net/sourceforge/plantuml/plantuml/"
        f"{PLANTUML_VERSION}/plantuml-{PLANTUML_VERSION}.jar",
        "https://github.com/plantuml/plantuml/releases/download/"
        f"v{PLANTUML_VERSION}/plantuml-{PLANTUML_VERSION}.jar",
    ]
    last_error: Exception | None = None
    for url in urls:
        try:
            data = fetch(url)
            break
        except Exception as exc:  # noqa: BLE001 - on tente le miroir suivant
            last_error = exc
            print(f"  échec ({exc}), miroir suivant…")
    else:
        raise RuntimeError(f"Impossible de télécharger plantuml.jar : {last_error}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    print(f"  → {dest.relative_to(ROOT)} ({len(data) // 1024} Ko)")


def main() -> int:
    print("Téléchargement des ressources embarquées…")
    extract_from_npm("mermaid", MERMAID_VERSION, "dist/mermaid.min.js", VENDOR_JS / "mermaid.min.js")
    extract_from_npm("pagedjs", PAGEDJS_VERSION, "dist/paged.polyfill.min.js", VENDOR_JS / "paged.polyfill.min.js")
    download_plantuml(VENDOR_PLANTUML / "plantuml.jar")
    print("Terminé.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
