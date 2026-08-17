"""Painel para incluir, descrever e relacionar imagens a registros do vídeo."""

from __future__ import annotations

import tkinter as tk
import uuid
from collections.abc import Callable
from tkinter import ttk

from gui.confirmation_dialog import ask_confirmation
from gui.image_cropper import ImageCropper
from gui.rounded_button import RoundedButton


class ImagePanel(tk.Frame):
    """Gerencia imagens armazenadas no arquivo ``.chp`` e seus vínculos."""

    def __init__(
        self,
        master: tk.Widget,
        images: list[dict],
        get_records: Callable[[], list[tuple[str, dict, str]]],
        on_save: Callable[[], None],
    ) -> None:
        """Inicializa a lista de imagens e os controles de associação."""

        super().__init__(master)
        self.images = images
        self.get_records = get_records
        self.on_save = on_save
        self.item_map: dict[str, dict] = {}

        buttons = tk.Frame(self)
        buttons.pack(fill="x", padx=6, pady=(6, 4))
        RoundedButton(buttons, text="+ imagem", command=self.add_image, width=82, height=30, radius=10).pack(
            side="left", padx=2
        )
        RoundedButton(buttons, text="– remover", command=self.remove_image, width=76, height=30, radius=10).pack(
            side="left", padx=2
        )

        body = tk.Frame(self)
        body.pack(fill="both", expand=True, padx=4)
        self.tree = ttk.Treeview(body, columns=("size", "format"), show="tree headings", selectmode="browse", height=11)
        self.tree.heading("#0", text="Título", anchor="w")
        self.tree.heading("size", text="Tamanho", anchor="e")
        self.tree.heading("format", text="Formato", anchor="w")
        self.tree.column("#0", width=150)
        self.tree.column("size", width=95, anchor="e")
        self.tree.column("format", width=70)
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", lambda _: self._update_details())

        self.description_var = tk.StringVar(value="Selecione uma imagem para ver sua descrição.")
        tk.Label(self, textvariable=self.description_var, anchor="w", justify="left", wraplength=270).pack(
            fill="x", padx=8, pady=(0, 6)
        )
        self.refresh()

    def refresh(self, selected: dict | None = None) -> None:
        """Atualiza a biblioteca visual de imagens."""

        self.tree.delete(*self.tree.get_children())
        self.item_map = {}
        selected_id = ""
        for image in self.images:
            item_id = self.tree.insert(
                "",
                "end",
                text=image["title"] or "Sem título",
                values=(f"{image['width']} × {image['height']}", image["mime_type"]),
            )
            self.item_map[item_id] = image
            if image is selected:
                selected_id = item_id
        if selected_id:
            self.tree.selection_set(selected_id)
            self.tree.focus(selected_id)
        self._update_details()

    def add_image(self) -> None:
        """Abre o recortador para criar uma imagem final de tamanho controlado."""

        ImageCropper(self, self._append_image)

    def _append_image(self, image: dict) -> None:
        """Inclui uma imagem recortada e a grava imediatamente no arquivo ``.chp``."""

        image["id"] = str(uuid.uuid4())
        self.images.append(image)
        self.on_save()
        self.refresh(image)

    def _selected_image(self) -> dict | None:
        """Obtém a imagem atualmente selecionada na árvore."""

        selection = self.tree.selection()
        return self.item_map.get(selection[0]) if selection else None

    def remove_image(self) -> None:
        """Exclui a imagem selecionada e todos os seus vínculos."""

        image = self._selected_image()
        if image is None or not ask_confirmation(self, "Remover imagem", "Excluir a imagem e todas as associações?"):
            return
        for _, record, _ in self.get_records():
            if image["id"] in record.get("images", []):
                record["images"].remove(image["id"])
        self.images.remove(image)
        self.on_save()
        self.refresh()

    def _update_details(self) -> None:
        """Exibe a descrição da imagem selecionada."""

        image = self._selected_image()
        if image is None:
            self.description_var.set("Selecione uma imagem para ver sua descrição.")
            return
        self.description_var.set(image["description"] or "Sem descrição.")
