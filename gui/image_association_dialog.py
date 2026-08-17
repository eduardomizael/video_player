"""Diálogo para selecionar imagens associadas a um registro do vídeo."""

from __future__ import annotations

import io
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from PIL import Image, ImageTk


class ImageAssociationDialog(tk.Toplevel):
    """Permite marcar imagens e visualizar a seleção antes de salvar os vínculos."""

    def __init__(self, master: tk.Widget, images: list[dict], record: dict, on_save: Callable[[], None]) -> None:
        """Cria o diálogo modal para o registro informado."""

        super().__init__(master)
        self.title("Associar imagens")
        self.transient(master.winfo_toplevel())
        self.resizable(False, False)
        self.geometry("780x500")
        self.images = images
        self.record = record
        self.on_save = on_save
        current_ids = set(record.get("images", []))
        self.selected = {image["id"]: tk.BooleanVar(value=image["id"] in current_ids) for image in images}
        self.preview: ImageTk.PhotoImage | None = None

        footer = tk.Frame(self, padx=10, pady=10)
        footer.pack(side="bottom", fill="x")
        tk.Button(footer, text="Cancelar", command=self.destroy).pack(side="right")
        tk.Button(footer, text="Salvar", command=self.save).pack(side="right", padx=(0, 6))

        content = tk.Frame(self, padx=10, pady=10)
        content.pack(fill="both", expand=True)
        list_frame = ttk.LabelFrame(content, text="Imagens disponíveis")
        preview_frame = ttk.LabelFrame(content, text="Visualização")
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        preview_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        content.columnconfigure(0, weight=1, minsize=320)
        content.columnconfigure(1, weight=1, minsize=420)
        content.rowconfigure(0, weight=1)

        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.list_body = tk.Frame(canvas)
        self.list_body.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.list_body, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        scrollbar.pack(side="right", fill="y", padx=(0, 6), pady=6)

        self.preview_label = tk.Label(preview_frame, text="Selecione uma imagem para visualizar.", anchor="center")
        self.preview_label.pack(fill="both", expand=True, padx=8, pady=8)
        self.description_var = tk.StringVar()
        tk.Label(preview_frame, textvariable=self.description_var, justify="left", anchor="w", wraplength=320).pack(
            fill="x", padx=8, pady=(0, 8)
        )

        if images:
            for image in images:
                self._add_image_option(image)
            self._show_image(images[0])
        else:
            tk.Label(self.list_body, text="Nenhuma imagem cadastrada.").pack(padx=10, pady=10)

        self.grab_set()
        self._center_over_parent()

    def _center_over_parent(self) -> None:
        """Centraliza o diálogo dentro da janela principal da aplicação."""

        self.update_idletasks()
        parent = self.master.winfo_toplevel()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"{self.winfo_width()}x{self.winfo_height()}+{max(0, x)}+{max(0, y)}")

    def _add_image_option(self, image: dict) -> None:
        """Inclui uma opção com caixa de seleção e clique para pré-visualizar."""

        row = tk.Frame(self.list_body, cursor="hand2")
        row.pack(fill="x", padx=4, pady=2)
        tk.Checkbutton(row, variable=self.selected[image["id"]], command=lambda: self._show_image(image)).pack(
            side="left"
        )
        title = image["title"] or "Sem título"
        label = tk.Label(
            row, text=f"{title}\n{image['width']} × {image['height']}", justify="left", anchor="w", cursor="hand2"
        )
        label.pack(side="left", fill="x", expand=True)
        row.bind("<Button-1>", lambda _: self._show_image(image))
        label.bind("<Button-1>", lambda _: self._show_image(image))

    def _show_image(self, image: dict) -> None:
        """Exibe a imagem clicada no painel lateral sem alterar seus vínculos."""

        try:
            with Image.open(io.BytesIO(image["data"])) as source:
                preview = source.copy()
            preview.thumbnail((360, 300), Image.Resampling.LANCZOS)
            self.preview = ImageTk.PhotoImage(preview)
            self.preview_label.configure(image=self.preview, text="")
            self.description_var.set(image["description"] or "Sem descrição.")
        except (OSError, ValueError):
            self.preview = None
            self.preview_label.configure(image="", text="Não foi possível visualizar esta imagem.")
            self.description_var.set("")

    def save(self) -> None:
        """Substitui os vínculos do registro pela seleção confirmada pelo usuário."""

        self.record["images"] = [image["id"] for image in self.images if self.selected[image["id"]].get()]
        self.on_save()
        self.destroy()
