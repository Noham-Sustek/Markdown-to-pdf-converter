"""Interface en ligne de commande de MDPDF."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .pipeline import ConversionError, Options, convert


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mdpdf",
        description=(
            "Convertisseur Markdown / AsciiDoc → PDF, 100%% hors-ligne. "
            "Accepte des fichiers (.md, .adoc…) ou des dossiers (traités récursivement)."
        ),
        epilog=(
            "Exemples :\n"
            "  mdpdf rapport.md\n"
            "  mdpdf rapport.md -o sortie/rapport.pdf\n"
            "  mdpdf docs/ --output-dir pdf/\n"
            "  mdpdf chap1.md chap2.adoc chap3.md --merge --title \"Manuel\" -o manuel.pdf\n"
            "  mdpdf rapport.md --theme charte.css --logo logo.png\n"
            "  mdpdf gui   (lance l'interface graphique)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("inputs", nargs="+", metavar="FICHIER|DOSSIER",
                        help="fichiers ou dossiers à convertir (ou « gui »)")
    parser.add_argument("-o", "--output", type=Path,
                        help="fichier PDF de sortie (fichier unique ou --merge)")
    parser.add_argument("-d", "--output-dir", type=Path,
                        help="dossier de sortie des PDF (par défaut : à côté des sources)")
    parser.add_argument("-m", "--merge", action="store_true",
                        help="fusionner toutes les sources en un seul PDF (avec couverture)")
    parser.add_argument("-t", "--title", help="titre du document (couverture, en-tête)")
    parser.add_argument("--theme", type=Path,
                        help="fichier CSS de personnalisation, appliqué après le thème par défaut")
    parser.add_argument("--logo", type=Path,
                        help="image (PNG/SVG/JPG) affichée sur la page de couverture en mode fusion")
    parser.add_argument("--header-left", help="texte d'en-tête gauche sur chaque page")
    parser.add_argument("--header-right", help="texte d'en-tête droit (remplace le titre courant)")
    parser.add_argument("--footer", help="texte de pied de page gauche sur chaque page")
    parser.add_argument("--watermark",
                        help="filigrane en diagonale sur chaque page (ex: CONFIDENTIEL)")
    parser.add_argument("--no-toc", action="store_true", help="ne pas générer de sommaire")
    parser.add_argument("--toc-depth", type=int, default=3, choices=range(1, 5),
                        help="profondeur du sommaire (1-4, défaut : 3)")
    parser.add_argument("--lang", default="fr", help="langue du document (défaut : fr)")
    parser.add_argument("-V", "--version", action="version", version=f"mdpdf {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    # Console Windows en cp1252 : ne pas planter sur « → » ou « ⚠ ».
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")

    argv = list(sys.argv[1:] if argv is None else argv)

    # Aucun argument (double-clic sur mdpdf.exe) ou « gui » → interface graphique.
    if not argv or argv[0].lower() == "gui":
        return _launch_gui()

    parser = build_parser()
    args = parser.parse_args(argv)

    options = Options(
        merge=args.merge,
        title=args.title,
        toc=not args.no_toc,
        toc_depth=args.toc_depth,
        theme=args.theme,
        logo=args.logo,
        header_left=args.header_left,
        header_right=args.header_right,
        footer=args.footer,
        watermark=args.watermark,
        lang=args.lang,
        output=args.output,
        output_dir=args.output_dir,
    )

    try:
        convert([Path(p) for p in args.inputs], options)
    except ConversionError as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrompu.", file=sys.stderr)
        return 130
    return 0


def _launch_gui() -> int:
    from . import gui

    _maybe_hide_console()
    return gui.main()


def _maybe_hide_console() -> None:
    """Masque la fenêtre console sous Windows uniquement si l'application la
    possède seule (cas du double-clic). Lancée depuis un terminal existant,
    la console est partagée avec ce terminal : on n'y touche pas."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        arr = (ctypes.c_uint * 1)()
        # GetConsoleProcessList renvoie le nombre de processus attachés à la
        # console ; 1 = nous sommes seuls (double-clic), >1 = terminal partagé.
        count = kernel32.GetConsoleProcessList(arr, 1)
        if count <= 1:
            hwnd = kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:
        pass  # ne jamais empêcher l'ouverture de l'interface pour ça


if __name__ == "__main__":
    sys.exit(main())
