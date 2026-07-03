"""Point d'entrée PyInstaller : exécutable fenêtré MDPDF-GUI.exe."""
import sys

from mdpdf.gui import main

if __name__ == "__main__":
    sys.exit(main())
