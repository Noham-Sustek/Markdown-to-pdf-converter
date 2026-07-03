# -*- mode: python ; coding: utf-8 -*-
"""Spec PyInstaller : construit le dossier portable dist/MDPDF avec
mdpdf.exe (console) et MDPDF-GUI.exe (fenêtré).

Le dossier vendor/ (Chromium, JRE, plantuml.jar) est copié à côté des
exécutables par le workflow de build, pas par PyInstaller.
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

a_cli = Analysis(
    ["scripts/entry_cli.py"],
    pathex=["src"],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    noarchive=False,
)
pyz_cli = PYZ(a_cli.pure)

a_gui = Analysis(
    ["scripts/entry_gui.py"],
    pathex=["src"],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    noarchive=False,
)
pyz_gui = PYZ(a_gui.pure)

exe_cli = EXE(
    pyz_cli,
    a_cli.scripts,
    [],
    exclude_binaries=True,
    name="mdpdf",
    console=True,
    upx=False,
)

exe_gui = EXE(
    pyz_gui,
    a_gui.scripts,
    [],
    exclude_binaries=True,
    name="MDPDF-GUI",
    console=False,
    upx=False,
)

coll = COLLECT(
    exe_cli,
    a_cli.binaries,
    a_cli.datas,
    exe_gui,
    a_gui.binaries,
    a_gui.datas,
    name="MDPDF",
    upx=False,
)
