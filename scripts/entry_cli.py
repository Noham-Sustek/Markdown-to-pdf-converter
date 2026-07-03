"""Point d'entrée PyInstaller : exécutable console mdpdf.exe."""
import sys

from mdpdf.cli import main

if __name__ == "__main__":
    sys.exit(main())
