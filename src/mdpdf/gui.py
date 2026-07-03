"""Interface graphique de MDPDF (Tkinter, glisser-déposer si tkinterdnd2 présent)."""
from __future__ import annotations

import queue
import re
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .pipeline import ALL_SUFFIXES, ConversionError, Options, convert

try:  # le glisser-déposer est optionnel : l'app fonctionne sans
    from tkinterdnd2 import DND_FILES, TkinterDnD

    _BaseTk = TkinterDnD.Tk
    _HAS_DND = True
except ImportError:  # pragma: no cover
    _BaseTk = tk.Tk
    _HAS_DND = False


class App(_BaseTk):  # type: ignore[misc,valid-type]
    def __init__(self) -> None:
        super().__init__()
        self.title(f"MDPDF {__version__} — Markdown / AsciiDoc → PDF (hors-ligne)")
        self.geometry("780x620")
        self.minsize(640, 520)

        self._log_queue: queue.Queue[str] = queue.Queue()
        self._worker: threading.Thread | None = None

        self._build_widgets()
        self.after(100, self._poll_log)

    # ---- construction de l'interface ------------------------------------
    def _build_widgets(self) -> None:
        pad = {"padx": 8, "pady": 4}

        files_frame = ttk.LabelFrame(self, text="Documents à convertir (.md, .adoc)")
        files_frame.pack(fill="both", expand=True, **pad)

        self.file_list = tk.Listbox(files_frame, selectmode="extended", height=8)
        self.file_list.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        scroll = ttk.Scrollbar(files_frame, command=self.file_list.yview)
        scroll.pack(side="left", fill="y", pady=8)
        self.file_list.configure(yscrollcommand=scroll.set)

        btns = ttk.Frame(files_frame)
        btns.pack(side="left", fill="y", padx=8, pady=8)
        ttk.Button(btns, text="Ajouter fichiers…", command=self._add_files).pack(fill="x", pady=2)
        ttk.Button(btns, text="Ajouter dossier…", command=self._add_folder).pack(fill="x", pady=2)
        ttk.Button(btns, text="Retirer", command=self._remove_selected).pack(fill="x", pady=2)
        ttk.Button(btns, text="Vider", command=lambda: self.file_list.delete(0, "end")).pack(fill="x", pady=2)
        ttk.Button(btns, text="Monter ↑", command=lambda: self._move(-1)).pack(fill="x", pady=(12, 2))
        ttk.Button(btns, text="Descendre ↓", command=lambda: self._move(1)).pack(fill="x", pady=2)

        if _HAS_DND:
            self.file_list.drop_target_register(DND_FILES)
            self.file_list.dnd_bind("<<Drop>>", self._on_drop)
            hint = "Astuce : glissez-déposez vos fichiers ou dossiers directement dans la liste."
        else:
            hint = ""
        if hint:
            ttk.Label(self, text=hint, foreground="#666666").pack(anchor="w", padx=12)

        opts = ttk.LabelFrame(self, text="Options")
        opts.pack(fill="x", **pad)
        opts.columnconfigure(1, weight=1)

        self.var_merge = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            opts,
            text="Fusionner tous les documents en un seul PDF (avec couverture et sommaire global)",
            variable=self.var_merge,
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 2))

        self.var_toc = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Générer le sommaire", variable=self.var_toc).grid(
            row=1, column=0, columnspan=3, sticky="w", padx=8, pady=2
        )

        ttk.Label(opts, text="Titre :").grid(row=2, column=0, sticky="w", padx=8)
        self.var_title = tk.StringVar()
        ttk.Entry(opts, textvariable=self.var_title).grid(row=2, column=1, columnspan=2, sticky="ew", padx=8, pady=2)

        ttk.Label(opts, text="Thème CSS :").grid(row=3, column=0, sticky="w", padx=8)
        self.var_theme = tk.StringVar()
        ttk.Entry(opts, textvariable=self.var_theme).grid(row=3, column=1, sticky="ew", padx=(8, 2), pady=2)
        ttk.Button(opts, text="…", width=3, command=self._pick_theme).grid(row=3, column=2, padx=(0, 8))

        ttk.Label(opts, text="Logo :").grid(row=4, column=0, sticky="w", padx=8)
        self.var_logo = tk.StringVar()
        ttk.Entry(opts, textvariable=self.var_logo).grid(row=4, column=1, sticky="ew", padx=(8, 2), pady=2)
        ttk.Button(opts, text="…", width=3, command=self._pick_logo).grid(row=4, column=2, padx=(0, 8))

        ttk.Label(opts, text="Dossier de sortie :").grid(row=5, column=0, sticky="w", padx=8)
        self.var_outdir = tk.StringVar()
        ttk.Entry(opts, textvariable=self.var_outdir).grid(row=5, column=1, sticky="ew", padx=(8, 2), pady=2)
        ttk.Button(opts, text="…", width=3, command=self._pick_outdir).grid(row=5, column=2, padx=(0, 8), pady=(0, 6))

        actions = ttk.Frame(self)
        actions.pack(fill="x", **pad)
        self.convert_btn = ttk.Button(actions, text="Convertir en PDF", command=self._start_convert)
        self.convert_btn.pack(side="right")
        self.progress = ttk.Progressbar(actions, mode="indeterminate")
        self.progress.pack(side="left", fill="x", expand=True, padx=(0, 12))

        log_frame = ttk.LabelFrame(self, text="Journal")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(log_frame, height=8, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)

    # ---- gestion des fichiers -------------------------------------------
    def _add_files(self) -> None:
        exts = " ".join(f"*{e}" for e in sorted(ALL_SUFFIXES))
        files = filedialog.askopenfilenames(
            title="Choisir les documents",
            filetypes=[("Markdown / AsciiDoc", exts), ("Tous les fichiers", "*.*")],
        )
        for f in files:
            self._append_path(f)

    def _add_folder(self) -> None:
        folder = filedialog.askdirectory(title="Choisir un dossier")
        if folder:
            self._append_path(folder)

    def _append_path(self, path: str) -> None:
        existing = set(self.file_list.get(0, "end"))
        if path not in existing:
            self.file_list.insert("end", path)

    def _remove_selected(self) -> None:
        for index in reversed(self.file_list.curselection()):
            self.file_list.delete(index)

    def _move(self, delta: int) -> None:
        selection = self.file_list.curselection()
        if len(selection) != 1:
            return
        i = selection[0]
        j = i + delta
        if 0 <= j < self.file_list.size():
            value = self.file_list.get(i)
            self.file_list.delete(i)
            self.file_list.insert(j, value)
            self.file_list.selection_set(j)

    def _on_drop(self, event) -> None:  # noqa: ANN001 - événement tkinterdnd2
        # Les chemins contenant des espaces arrivent entre accolades.
        for path in re.findall(r"\{([^}]*)\}|(\S+)", event.data):
            value = path[0] or path[1]
            candidate = Path(value)
            if candidate.is_dir() or (
                candidate.is_file() and candidate.suffix.lower() in ALL_SUFFIXES
            ):
                self._append_path(value)

    def _pick_theme(self) -> None:
        f = filedialog.askopenfilename(filetypes=[("Feuille de style CSS", "*.css")])
        if f:
            self.var_theme.set(f)

    def _pick_logo(self) -> None:
        f = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.svg *.gif"), ("Tous", "*.*")]
        )
        if f:
            self.var_logo.set(f)

    def _pick_outdir(self) -> None:
        d = filedialog.askdirectory(title="Dossier de sortie des PDF")
        if d:
            self.var_outdir.set(d)

    # ---- conversion -------------------------------------------------------
    def _start_convert(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        inputs = [Path(p) for p in self.file_list.get(0, "end")]
        if not inputs:
            messagebox.showwarning("MDPDF", "Ajoutez au moins un fichier ou un dossier.")
            return

        options = Options(
            merge=self.var_merge.get(),
            title=self.var_title.get().strip() or None,
            toc=self.var_toc.get(),
            theme=Path(self.var_theme.get()) if self.var_theme.get().strip() else None,
            logo=Path(self.var_logo.get()) if self.var_logo.get().strip() else None,
            output_dir=Path(self.var_outdir.get()) if self.var_outdir.get().strip() else None,
            log=self._log_queue.put,
        )

        self.convert_btn.state(["disabled"])
        self.progress.start(12)
        self._worker = threading.Thread(
            target=self._run_convert, args=(inputs, options), daemon=True
        )
        self._worker.start()

    def _run_convert(self, inputs: list[Path], options: Options) -> None:
        try:
            outputs = convert(inputs, options)
            self._log_queue.put(f"✔ Succès : {len(outputs)} PDF généré(s).")
        except ConversionError as exc:
            self._log_queue.put(f"✖ Erreur : {exc}")
        except Exception as exc:  # noqa: BLE001 - affiché dans le journal
            self._log_queue.put(f"✖ Erreur inattendue : {exc}")
        finally:
            self._log_queue.put("__DONE__")

    def _poll_log(self) -> None:
        try:
            while True:
                message = self._log_queue.get_nowait()
                if message == "__DONE__":
                    self.progress.stop()
                    self.convert_btn.state(["!disabled"])
                else:
                    self._append_log(message)
        except queue.Empty:
            pass
        self.after(100, self._poll_log)

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")


def main() -> int:
    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
