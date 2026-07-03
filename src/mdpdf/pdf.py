"""HTML → PDF via le Chromium embarqué (Playwright), entièrement hors-ligne."""
from __future__ import annotations

import os
from pathlib import Path

from . import paths
from .diagrams import LogFn

_RENDER_TIMEOUT_MS = 180_000


class PdfError(RuntimeError):
    pass


def html_to_pdf(html: str, output: Path, log: LogFn = print) -> None:
    browsers = paths.browsers_dir()
    if browsers is not None:
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers)

    # Import tardif : PLAYWRIGHT_BROWSERS_PATH doit être positionné avant.
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    output.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        launch_kwargs: dict = {"headless": True}
        executable = paths.chromium_executable()
        if executable:
            launch_kwargs["executable_path"] = executable
        try:
            browser = p.chromium.launch(**launch_kwargs)
        except PlaywrightError as exc:
            raise PdfError(
                "Impossible de lancer le Chromium embarqué. Vérifiez que le dossier "
                f"vendor/browsers est présent à côté de l'exécutable. Détail : {exc}"
            ) from exc

        try:
            page = browser.new_page()
            page.set_content(html, wait_until="load", timeout=_RENDER_TIMEOUT_MS)
            page.wait_for_function(
                "window.__renderDone === true", timeout=_RENDER_TIMEOUT_MS
            )
            errors = page.evaluate("window.__renderErrors || []")
            for err in errors:
                log(f"  ⚠ rendu : {err}")
            page.pdf(
                path=str(output),
                prefer_css_page_size=True,
                print_background=True,
            )
        finally:
            browser.close()
