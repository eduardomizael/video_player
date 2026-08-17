"""Painel para edição da árvore de metadados do vídeo."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from gui.add_item_dialog import AddItemDialog, FormField
from gui.confirmation_dialog import ask_confirmation
from gui.rounded_button import RoundedButton


class MetadataPanel(tk.Frame):
    """Edita chaves e valores hierárquicos, mantendo valores apenas nas folhas."""

    def __init__(
        self,
        master: tk.Widget,
        metadata: list[dict],
        on_save: Callable[[], None],
        on_manage_images: Callable[[dict], None],
    ) -> None:
        """Inicializa a árvore visual de metadados."""

        super().__init__(master)
        self.metadata = metadata
        self.on_save = on_save
        self.on_manage_images = on_manage_images
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
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="Associar imagens...", command=self._manage_images)
        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Button-2>", self._show_context_menu)
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
        """Abre o formulário para adicionar uma chave no mesmo nível do item selecionado."""

        selection = self.tree.selection()
        parent_id = self.tree.parent(selection[0]) if selection else ""
        parent = self.item_map.get(parent_id)
        siblings = parent["children"] if parent else self.metadata

        def submit(values: dict[str, str]) -> str | None:
            key = values["key"].strip()
            if not key:
                return "A chave não pode ficar vazia."
            if any(node["key"] == key for node in siblings):
                return "Não pode haver chaves repetidas no mesmo nível."
            node = {"key": key, "value": values["value"].strip(), "children": []}
            siblings.append(node)
            self.refresh_tree(node)
            self.on_save()
            return None

        AddItemDialog(
            self,
            "Adicionar metadado",
            [FormField("key", "Chave", self._next_key(siblings)), FormField("value", "Valor", "")],
            submit,
        )

    def add_child(self) -> None:
        """Abre o formulário para criar filho e transferir o valor do pai."""

        selection = self.tree.selection()
        if not selection:
            return
        parent = self.item_map.get(selection[0])
        if parent is None:
            return
        siblings = parent["children"]

        def submit(values: dict[str, str]) -> str | None:
            key = values["key"].strip()
            if not key:
                return "A chave não pode ficar vazia."
            if any(node["key"] == key for node in siblings):
                return "Não pode haver chaves repetidas no mesmo nível."
            parent["value"] = ""
            child = {"key": key, "value": values["value"].strip(), "children": []}
            siblings.append(child)
            self.refresh_tree(child)
            self.on_save()
            return None

        AddItemDialog(
            self,
            "Adicionar metadado filho",
            [
                FormField("key", "Chave", self._next_key(siblings)),
                FormField("value", "Valor", parent["value"]),
            ],
            submit,
        )

    def remove_item(self) -> None:
        """Remove o item selecionado e seus descendentes após confirmação."""

        selection = self.tree.selection()
        if not selection:
            return
        item_id = selection[0]
        node = self.item_map.get(item_id)
        if node is None or not ask_confirmation(self, "Remover", f"Excluir '{node['key']}' e seus filhos?"):
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

    def _show_context_menu(self, event: tk.Event) -> None:
        """Exibe as ações disponíveis para o metadado clicado."""

        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        self.tree.selection_set(item_id)
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def _manage_images(self) -> None:
        """Abre a seleção de imagens para o metadado selecionado."""

        selection = self.tree.selection()
        if selection and (node := self.item_map.get(selection[0])):
            self.on_manage_images(node)
