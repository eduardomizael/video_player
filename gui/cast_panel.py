"""Painel visual e lógico para gerenciamento da lista de casting (elenco)."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from gui.rounded_button import RoundedButton


class CastPanel(tk.Frame):
    """Painel de elenco (casting) com Treeview, Scrollbar e edição inline."""

    def __init__(self, master: tk.Widget, casting: list[str], on_save: Callable[[], None]) -> None:
        """Inicializa o painel de casting."""

        super().__init__(master)
        self.casting = casting
        self.on_save = on_save

        cast_btns = tk.Frame(self)
        cast_btns.pack(side="top", fill="x", pady=(6, 4), padx=6)
        RoundedButton(cast_btns, text="+ adicionar", command=self.add_cast, width=82, height=30, radius=10).pack(
            side="left", padx=2
        )
        RoundedButton(cast_btns, text="– remover", command=self.rm_cast, width=76, height=30, radius=10).pack(
            side="left", padx=2
        )

        cast_frame = tk.Frame(self, bd=0, relief="flat")
        cast_frame.pack(fill="both", expand=True, padx=4, pady=(2, 4))

        self.cast_tree = ttk.Treeview(
            cast_frame,
            columns=("name",),
            show="headings",
            selectmode="browse",
            height=15,
        )
        self.cast_tree.heading("name", text="Nome", anchor="w")
        self.cast_tree.column("name", width=200, anchor="w")

        self.cast_scroll = ttk.Scrollbar(cast_frame, orient="vertical", command=self.cast_tree.yview)
        self.cast_tree.configure(yscrollcommand=self.cast_scroll.set)
        self.cast_tree.pack(side="left", fill="both", expand=True)
        self.cast_scroll.pack(side="right", fill="y")
        self.cast_tree.bind("<Double-1>", self._inline_edit_cast)

        self.refresh_cast_tree()

    def refresh_cast_tree(self, select_idx: int | None = None) -> None:
        """Atualiza a lista de casting e foca o item selecionado."""
        self.cast_tree.delete(*self.cast_tree.get_children())
        found_id = None
        for i, name in enumerate(self.casting):
            item_id = self.cast_tree.insert("", "end", values=(name,))
            if i == select_idx:
                found_id = item_id

        if found_id:
            self.cast_tree.selection_set(found_id)
            self.cast_tree.focus(found_id)
            self.cast_tree.see(found_id)

    def add_cast(self) -> None:
        """Adiciona um novo nome à lista de casting."""
        self.casting.append("Novo nome")
        new_idx = len(self.casting) - 1
        self.refresh_cast_tree(select_idx=new_idx)
        self.on_save()

    def rm_cast(self) -> None:
        """Remove o nome selecionado após confirmação."""
        sel = self.cast_tree.selection()
        if not sel:
            return
        idx = self.cast_tree.index(sel[0])
        if messagebox.askyesno("Remover", f"Excluir '{self.casting[idx]}'?"):
            self.casting.pop(idx)
            self.refresh_cast_tree()
            self.on_save()

    def _inline_edit_cast(self, event: tk.Event) -> None:
        """Permite editar um nome diretamente na lista de casting."""
        row_id = self.cast_tree.identify_row(event.y)
        col = self.cast_tree.identify_column(event.x)
        if not row_id or col == "#0":
            return
        bbox = self.cast_tree.bbox(row_id, col)
        if not bbox:
            return
        x, y, w, h = bbox
        entry = tk.Entry(self.cast_tree)
        entry.place(x=x, y=y, width=w, height=h)
        old_val = self.cast_tree.set(row_id, col)
        entry.insert(0, old_val)
        entry.focus()

        def commit(e: tk.Event | None = None) -> None:
            new_val = entry.get().strip()
            entry.destroy()
            idx = self.cast_tree.index(row_id)
            if not new_val:
                return
            self.casting[idx] = new_val
            self.refresh_cast_tree()
            self.on_save()

        entry.bind("<Return>", commit)
        entry.bind("<Escape>", lambda *_: entry.destroy())
        entry.bind("<FocusOut>", lambda *_: entry.destroy())
