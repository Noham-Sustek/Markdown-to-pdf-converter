# MDPDF — Convertisseur Markdown / AsciiDoc → PDF, 100% hors-ligne

Application **Windows portable** qui convertit vos documents Markdown (`.md`)
et AsciiDoc (`.adoc`) en PDF de qualité professionnelle, **sans jamais accéder
à Internet**. Conçue pour les environnements d'entreprise sensibles : toutes
les ressources (moteur de rendu Chromium, mermaid.js, plantuml.jar, runtime
Java) sont embarquées dans le dossier de l'application.

## Fonctionnalités

- **Markdown et AsciiDoc** : titres, tableaux, listes de tâches, notes de bas
  de page, admonitions AsciiDoc (`NOTE:`, `WARNING:`…)
- **Coloration syntaxique** du code (Python, SQL, Java, etc. — via Pygments)
- **Sommaire automatique** cliquable, avec numéros de page
- **Signets PDF** : arborescence des titres dans le volet de navigation du
  lecteur, et PDF tagué (accessible)
- **Images locales embarquées** : les images `![](schema.png)` sont incluses
  dans le PDF en base64 (aucun accès réseau, fichier autonome)
- **Filigrane** en diagonale paramétrable (« CONFIDENTIEL », « BROUILLON »…)
- **Diagrammes Mermaid** (flowcharts, séquences, Gantt…) rendus hors-ligne
- **Diagrammes PlantUML** (séquences, classes, composants…) rendus hors-ligne
  grâce au JRE embarqué et au moteur de layout Smetana (pas besoin de Graphviz)
- **Conversion en lot** : glissez un dossier, tous les `.md`/`.adoc` sont
  convertis (récursivement)
- **Fusion** : assemblez plusieurs documents en un seul PDF avec page de
  couverture, logo et sommaire global
- **Thèmes personnalisables** : charte graphique, en-têtes/pieds de page,
  polices et couleurs via un simple fichier CSS
- Format **A4 portrait** sobre par défaut, numéros de page, titre courant
  en en-tête

## Installation (Windows)

1. Téléchargez `MDPDF-windows-x64.zip` depuis la page
   [Releases](../../releases) du dépôt.
2. Décompressez l'archive où vous voulez (aucun droit administrateur requis).
3. C'est tout. L'application ne touche ni au registre, ni au réseau.

> **Sécurité** : l'application n'émet **aucune requête réseau** à l'exécution.
> Le zip est auto-suffisant : Chromium, mermaid.js, plantuml.jar et un JRE
> minimal sont inclus dans le dossier `vendor/`. Vous pouvez le vérifier avec
> votre pare-feu ou en coupant la connexion.

## Utilisation

### Interface graphique

**Double-cliquez sur `mdpdf.exe`** (sans argument) — l'interface s'ouvre et la
fenêtre console se masque automatiquement. En ligne de commande, `mdpdf gui`
fait la même chose.

1. Glissez-déposez vos fichiers ou dossiers dans la liste (ou utilisez les
   boutons « Ajouter »).
2. Choisissez vos options (fusion, sommaire, thème, logo, dossier de sortie).
3. Cliquez sur **Convertir en PDF**.

### Ligne de commande

```bat
:: Un fichier → un PDF (créé à côté de la source)
mdpdf rapport.md

:: Choisir le fichier de sortie
mdpdf rapport.md -o sortie\rapport.pdf

:: Tout un dossier (récursif), PDF regroupés dans un dossier
mdpdf docs\ --output-dir pdf\

:: Fusionner plusieurs documents en un manuel unique
mdpdf chap1.md chap2.adoc chap3.md --merge --title "Manuel utilisateur" -o manuel.pdf

:: Avec charte graphique et logo
mdpdf rapport.md --theme charte.css --logo logo.png

:: Avec filigrane « CONFIDENTIEL » sur chaque page
mdpdf rapport.md --watermark CONFIDENTIEL

:: Toutes les options
mdpdf --help
```

Principales options :

| Option | Effet |
|---|---|
| `-m, --merge` | fusionne toutes les sources en un PDF (couverture + sommaire global) |
| `-t, --title` | titre du document (couverture, métadonnées) |
| `--theme fichier.css` | CSS de personnalisation, appliqué après le thème par défaut |
| `--logo image.png` | logo sur la page de couverture (mode fusion) |
| `--header-left`, `--header-right`, `--footer` | textes d'en-tête/pied de page |
| `--watermark "TEXTE"` | filigrane en diagonale sur chaque page (ex : CONFIDENTIEL) |
| `--no-toc` / `--toc-depth N` | désactive ou règle la profondeur du sommaire |
| `-d, --output-dir` | dossier de destination des PDF |

### Diagrammes

Dans un fichier **Markdown** :

    ```mermaid
    flowchart LR
        A --> B
    ```

    ```plantuml
    @startuml
    Alice -> Bob : bonjour
    @enduml
    ```

Dans un fichier **AsciiDoc** :

    [mermaid]
    ----
    flowchart LR
        A --> B
    ----

    [plantuml]
    ----
    Alice -> Bob : bonjour
    ----

### Sauts de page manuels

Pour forcer un saut de page dans un document :

- **Markdown** : insérez `<div class="page-break"></div>` (ou un HTML brut
  `<div style="page-break-after: always"></div>`) à l'endroit voulu.
- **AsciiDoc** : utilisez le saut de page natif `<<<` sur une ligne seule.

> Note : le convertisseur n'utilise pas Pandoc ; la syntaxe LaTeX de Pandoc
> (`\newpage`, `\pagebreak`) n'est donc pas interprétée — utilisez les formes
> ci-dessus.

### Personnaliser l'apparence

Créez un fichier CSS et passez-le avec `--theme` (ou le champ « Thème CSS »
de l'interface). Il est chargé **après** le thème par défaut : ne redéfinissez
que ce que vous voulez changer. Voir
[`examples/charte-exemple.css`](examples/charte-exemple.css) pour un modèle
commenté (couleurs, police, en-tête « Confidentiel », etc.).

Le document est mis en page avec les règles CSS paginées (`@page`,
`target-counter`, `string-set`) interprétées par [Paged.js] — tout ce qui est
possible en CSS l'est dans vos thèmes.

## Architecture

```
fichier .md / .adoc
   │  markdown-it-py / asciidoc-py  (+ Pygments pour le code)
   ▼
HTML autonome  ──  blocs mermaid → mermaid.js (embarqué)
   │               blocs plantuml → plantuml.jar + JRE (embarqués)
   ▼
Chromium embarqué (Playwright) + Paged.js : pagination, sommaire, en-têtes
   ▼
PDF final (A4, liens cliquables)
```

Contenu du dossier portable :

```
MDPDF\
├── mdpdf.exe            ← interface graphique (double-clic) + ligne de commande
├── _internal\           ← Python + bibliothèques (PyInstaller)
├── vendor\
│   ├── browsers\        ← Chromium hors-ligne
│   ├── jre\             ← runtime Java minimal (jlink)
│   └── plantuml\plantuml.jar
└── examples\
```

## Compiler soi-même

La release est produite automatiquement par le workflow GitHub Actions
[`build-windows.yml`](.github/workflows/build-windows.yml) (déclenché à chaque
tag `v*`, artefact disponible aussi sur chaque push). Pour compiler à la main
sur une machine Windows avec Python 3.10+ :

```bat
pip install -r requirements.txt pyinstaller
python scripts\fetch_assets.py
set PLAYWRIGHT_BROWSERS_PATH=%CD%\vendor\browsers
python -m playwright install chromium
:: JRE minimal (nécessite un JDK 21) :
jlink --add-modules java.base,java.desktop,java.datatransfer,java.logging,java.management,java.naming,java.sql,java.xml,jdk.unsupported --strip-debug --no-header-files --no-man-pages --compress zip-6 --output vendor\jre
pyinstaller --noconfirm mdpdf.spec
xcopy /E /I vendor dist\MDPDF\vendor
```

Le dossier `dist\MDPDF` est l'application portable complète.

### Lancer depuis les sources (développement)

```bash
pip install -r requirements.txt
python scripts/fetch_assets.py
python -m playwright install chromium
PYTHONPATH=src python -m mdpdf.cli examples/exemple.md
```

## Licence

MIT.

[Paged.js]: https://pagedjs.org/
