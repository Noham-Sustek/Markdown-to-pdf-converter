# -*- mode: python ; coding: utf-8 -*-
"""Spec PyInstaller : construit le dossier portable dist/MDPDF avec un
exécutable unique mdpdf.exe.

Double-clic (aucun argument) → l'interface graphique s'ouvre (et la fenêtre
console est masquée) ; en ligne de commande, mdpdf.exe se comporte comme un
outil console classique. Un seul fichier à faire approuver par l'IT.

Le dossier vendor/ (Chromium, JRE, plantuml.jar) est copié à côté de
l'exécutable par le workflow de build, pas par PyInstaller.
"""
from PyInstaller.utils.hooks import collect_all

datas = [("src/mdpdf/assets", "mdpdf/assets")]
binaries = []
hiddenimports = []

# playwright embarque son driver Node ; asciidoc ses fichiers .conf.
for package in ("playwright", "asciidoc", "tkinterdnd2"):
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ["scripts/entry_cli.py"],
    pathex=["src"],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    noarchive=False,
)
pyz = PYZ(a.pure)

# console=True : indispensable pour l'usage en ligne de commande ; lors d'un
# double-clic, l'application masque elle-même la fenêtre console avant
# d'ouvrir l'interface (voir mdpdf.cli._maybe_hide_console).
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="mdpdf",
    console=True,
    upx=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="MDPDF",
    upx=False,
)
