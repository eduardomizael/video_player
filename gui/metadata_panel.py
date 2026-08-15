"""Painel para edição da árvore de metadados do vídeo."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from gui.rounded_button import RoundedButton


class MetadataPanel(tk.Frame):
    """Edita chaves e valores hierárquicos, mantendo valores apenas nas folhas."""

    def __init__(self, master: tk.Widget, metadata: list[dict], on_save: Callable[[], None]) -> None:
        """Inicializa a árvore visual de metadados."""

        super().__init__(master)
        self.metadata = metadata
        self.on_save = on_save
        self.item_map: dict[str, dict] = {}

        buttons = tk.Frame(self)
        buttons.pack(side="top", fill="x", pady=(6, 4), padx=6)
        RoundedButton(buttons, text="+ adicionar", command=self.add_item, width=82, height=30, radius=10).pack(
            side="left", padx=2
        )
        RoundedButton(buttons, text="+ filho", command=self.add_child, width=58, height=30, radius=10).pack(
            side="left", padx=2
        )
        RoundedButton(buttons, text="– remover", command=self.remove_item, width=76, height=30, radius=10).pack(
            side="left", padx=2
        )

        tree_frame = tk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=4, pady=(2, 4))
        self.tree = ttk.Treeview(tree_frame, columns=("value",), show="tree headings", selectmode="browse", height=15)
        self.tree.heading("#0", text="Chave", anchor="w")
        self.tree.heading("value", text="Valor", anchor="w")
        self.tree.column("#0", width=130, anchor="w")
        self.tree.column("value", width=150, anchor="w")
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self._inline_edit)
        self.refresh_tree()

    def refresh_tree(self, selected: dict | None = None) -> None:
        """Reconstrói a árvore e preserva a seleção quando possível."""

        self.tree.delete(*self.tree.get_children())
        self.item_map = {}
        selected_id = ""

        def add_nodes(parent_id: str, nodes: list[dict]) -> None:
            nonlocal selected_id
            for node in nodes:
                value = "" if node["children"] else node["value"]
                item_id = self.tree.insert(parent_id, "end", text=node["key"], values=(value,), open=True)
                self.item_map[item_id] = node
                if node is selected:
                    selected_id = item_id
                add_nodes(item_id, node["children"])

        add_nodes("", self.metadata)
        if selected_id:
            self.tree.selection_set(selected_id)
            self.tree.focus(selected_id)
            self.tree.see(selected_id)

    def add_item(self) -> None:
        """Adiciona uma chave no mesmo nível do item selecionado."""

        selection = self.tree.selection()
        parent_id = self.tree.parent(selection[0]) if selection else ""
        parent = self.item_map.get(parent_id)
        siblings = parent["children"] if parent else self.metadata
        node = {"key": self._next_key(siblings), "value": "", "children": []}
        siblings.append(node)
        self.refresh_tree(node)
        self.on_save()

    def add_child(self) -> None:
        """Adiciona filho e transfere para ele o valor que havia no pai."""

        selection = self.tree.selection()
        if not selection:
            return
        parent = self.item_map.get(selection[0])
        if parent is None:
            return
        value = parent["value"]
        parent["value"] = ""
        child = {"key": self._next_key(parent["children"]), "value": value, "children": []}
        parent["children"].append(child)
        self.refresh_tree(child)
        self.on_save()

    def remove_item(self) -> None:
        """Remove o item selecionado e seus descendentes após confirmação."""

        selection = self.tree.selection()
        if not selection:
            return
        item_id = selection[0]
        node = self.item_map.get(item_id)
        if node is None or not messagebox.askyesno("Remover", f"Excluir '{node['key']}' e seus filhos?"):
            return
        parent_id = self.tree.parent(item_id)
        parent = self.item_map.get(parent_id)
        siblings = parent["children"] if parent else self.metadata
        siblings.remove(node)
        self.refresh_tree()
        self.on_save()

    @staticmethod
    def _next_key(siblings: list[dict]) -> str:
        """Gera uma chave padrão ainda não usada entre irmãos."""

        existing = {node["key"] for node in siblings}
        index = 1
        while f"chave_{index}" in existing:
            index += 1
        return f"chave_{index}"

    def _inline_edit(self, event: tk.Event) -> None:
        """Edita chave ou valor ao clicar duas vezes em uma célula da árvore."""

        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item_id:
            return
        node = self.item_map.get(item_id)
        if node is None:
            return
        if column == "#1" and node["children"]:
            messagebox.showinfo("Valor indisponível", "Apenas itens sem filhos podem possuir valor.")
            return
        bbox = self.tree.bbox(item_id, column)
        if not bbox:
            return
        x, y, width, height = bbox
        old_value = node["key"] if column == "#0" else node["value"]
        entry = tk.Entry(self.tree)
        entry.insert(0, old_value)
        entry.place(x=x, y=y, width=width, height=height)
        entry.focus_set()

        def commit(_: tk.Event | None = None) -> None:
            value = entry.get().strip()
            entry.destroy()
            if column == "#0":
                if not value:
                    messagebox.showerror("Chave inválida", "A chave não pode ficar vazia.")
                    return
                parent_id = self.tree.parent(item_id)
                parent = self.item_map.get(parent_id)
                siblings = parent["children"] if parent else self.metadata
                if any(sibling is not node and sibling["key"] == value for sibling in siblings):
                    messagebox.showerror("Chave duplicada", "Não pode haver chaves repetidas no mesmo nível.")
                    return
                node["key"] = value
            else:
                node["value"] = value
            self.refresh_tree(node)
            self.on_save()

        entry.bind("<Return>", commit)
        entry.bind("<Escape>", lambda *_: entry.destroy())
        entry.bind("<FocusOut>", lambda *_: entry.destroy())
