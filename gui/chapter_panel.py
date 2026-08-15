"""Painel visual e lógico para gerenciamento da árvore de capítulos."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from gui.rounded_button import RoundedButton
from logic import fmt_sec, parse_flexible_time


class ChapterPanel(tk.Frame):
    """Painel de capítulos com Treeview, Scrollbar, edição inline e menu de contexto."""

    def __init__(
        self,
        master: tk.Widget,
        chaps: list[dict],
        on_save: callable,
        get_current_time: callable,
        on_jump_to_sec: callable,
    ) -> None:
        """Inicializa o painel de capítulos."""

        super().__init__(master)
        self.chaps = chaps
        self.on_save = on_save
        self.get_current_time = get_current_time
        self.on_jump_to_sec = on_jump_to_sec
        self.item_map: dict[str, dict] = {}

        btns = tk.Frame(self)
        btns.pack(side="top", fill="x", pady=(6, 4), padx=6)
        RoundedButton(btns, text="+ adicionar", command=self.add_chapter, width=82, height=30, radius=10).pack(
            side="left", padx=2
        )
        RoundedButton(btns, text="+ sub", command=self.add_subchapter, width=54, height=30, radius=10).pack(
            side="left", padx=2
        )
        RoundedButton(btns, text="– remover", command=self.rm_chapter, width=76, height=30, radius=10).pack(
            side="left", padx=2
        )

        chap_frame = tk.Frame(self, bd=0, relief="flat")
        chap_frame.pack(fill="both", expand=True, padx=4, pady=(2, 4))

        self.tree = ttk.Treeview(
            chap_frame,
            columns=("start", "end"),
            show="tree headings",
            selectmode="browse",
            height=15,
        )
        self.tree.heading("#0", text="Título", anchor="w")
        self.tree.heading("start", text="Início", anchor="e")
        self.tree.heading("end", text="Fim", anchor="e")
        self.tree.column("#0", width=150, anchor="w")
        self.tree.column("start", width=80, anchor="e")
        self.tree.column("end", width=80, anchor="e")

        self.chap_scroll = ttk.Scrollbar(chap_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.chap_scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        self.chap_scroll.pack(side="right", fill="y")

        # Menu de contexto (clique direito)
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="Definir início na posição atual", command=self._set_start_from_current)
        self.context_menu.add_command(label="Definir fim na posição atual", command=self._set_end_from_current)

        self.tree.bind("<ButtonRelease-1>", self._on_tree_left_click)
        self.tree.bind("<KeyRelease-Up>", self._jump_to_chapter)
        self.tree.bind("<KeyRelease-Down>", self._jump_to_chapter)
        self.tree.bind("<Double-1>", self._inline_edit)
        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Button-2>", self._show_context_menu)

        self.refresh_chap_tree()

    def refresh_chap_tree(self, select_chap: dict | None = None) -> None:
        """Atualiza a árvore com a lista de capítulos e foca o item selecionado."""
        self.tree.delete(*self.tree.get_children())
        self.item_map = {}
        found_id = None

        def add_items(parent: str, items: list[dict]) -> None:
            nonlocal found_id
            for chap in items:
                item_id = self.tree.insert(
                    parent,
                    "end",
                    text=chap["title"],
                    values=(fmt_sec(chap["start"]), fmt_sec(chap["end"])),
                    open=True,
                )
                self.item_map[item_id] = chap
                if chap is select_chap:
                    found_id = item_id
                add_items(item_id, chap.get("subs", []))

        add_items("", self.chaps)

        if found_id:
            self.tree.selection_set(found_id)
            self.tree.focus(found_id)
            self.tree.see(found_id)

    def add_chapter(self) -> None:
        """Cria um novo capítulo na posição atual de reprodução."""
        cur_sec = self.get_current_time()
        title = f"Capítulo {len(self.chaps) + 1}"
        end_sec = cur_sec + 10
        new_chap = {"title": title, "start": cur_sec, "end": end_sec, "subs": []}
        self.chaps.append(new_chap)
        self.chaps.sort(key=lambda x: x["start"])
        self.refresh_chap_tree(select_chap=new_chap)
        self.on_save()

    def add_subchapter(self) -> None:
        """Adiciona um subcapítulo ao item selecionado."""
        sel = self.tree.selection()
        if not sel:
            return
        item = sel[0]
        target = self.item_map.get(item)
        if target is None:
            return
        parent = target
        if item not in self.tree.get_children(""):
            parent_id = self.tree.parent(item)
            parent = self.item_map.get(parent_id, target)
        subs = parent.setdefault("subs", [])
        title = f"Sub {len(subs) + 1}"
        cur_sec = self.get_current_time()
        new_sub = {"title": title, "start": cur_sec, "end": parent["end"]}
        subs.append(new_sub)
        self.refresh_chap_tree(select_chap=new_sub)
        self.on_save()

    def rm_chapter(self) -> None:
        """Remove o capítulo selecionado após confirmação."""
        sel = self.tree.selection()
        if not sel:
            return
        item = sel[0]
        node = self.item_map.get(item)
        if node is None:
            return
        parent_id = self.tree.parent(item)
        if not parent_id:
            if messagebox.askyesno("Remover", f"Excluir '{node['title']}'?"):
                self.chaps.remove(node)
        else:
            parent_node = self.item_map.get(parent_id)
            if parent_node and messagebox.askyesno("Remover", f"Excluir '{node['title']}'?"):
                parent_node.get("subs", []).remove(node)
        self.refresh_chap_tree()
        self.on_save()

    def _on_tree_left_click(self, event: tk.Event) -> None:
        """Leva a reprodução para o início do capítulo clicado com o botão esquerdo."""
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        node = self.item_map.get(row_id)
        if node:
            self.on_jump_to_sec(node["start"])

    def _jump_to_chapter(self, _) -> None:
        """Leva a reprodução para o início do capítulo selecionado por teclado."""
        sel = self.tree.selection()
        if sel:
            node = self.item_map.get(sel[0])
            if node:
                self.on_jump_to_sec(node["start"])

    def _show_context_menu(self, event: tk.Event) -> None:
        """Exibe o menu de contexto ao clicar com o botão direito em um capítulo."""
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        self.tree.selection_set(row_id)
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def _set_start_from_current(self) -> None:
        """Define o tempo de início do capítulo selecionado para a posição atual do vídeo."""
        sel = self.tree.selection()
        if not sel:
            return
        node = self.item_map.get(sel[0])
        if not node:
            return
        cur_sec = self.get_current_time()
        node["start"] = cur_sec
        self.chaps.sort(key=lambda x: x["start"])
        for chap in self.chaps:
            if chap.get("subs"):
                chap["subs"].sort(key=lambda x: x["start"])
        self.refresh_chap_tree()
        self.on_save()

    def _set_end_from_current(self) -> None:
        """Define o tempo de fim do capítulo selecionado para a posição atual do vídeo."""
        sel = self.tree.selection()
        if not sel:
            return
        node = self.item_map.get(sel[0])
        if not node:
            return
        cur_sec = self.get_current_time()
        node["end"] = cur_sec
        self.refresh_chap_tree()
        self.on_save()

    def _inline_edit(self, event: tk.Event) -> None:
        """Permite editar título ou tempos diretamente na árvore."""
        row_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not row_id:
            return
        bbox = self.tree.bbox(row_id, col)
        if not bbox:
            return
        x, y, w, h = bbox
        entry = tk.Entry(self.tree, justify="right" if col != "#0" else "left")
        entry.place(x=x, y=y, width=w, height=h)
        if col == "#0":
            old_val = self.tree.item(row_id, "text")
        else:
            old_val = self.tree.set(row_id, col)
        entry.insert(0, old_val)
        entry.focus()

        def commit(e: tk.Event | None = None) -> None:
            new_val = entry.get().strip()
            entry.destroy()
            node = self.item_map.get(row_id)
            if not node:
                return

            if col == "#0":
                if not new_val:
                    return
                node["title"] = new_val
            else:
                try:
                    sec = parse_flexible_time(new_val)
                    key = "start" if col == "#1" else "end"
                    node[key] = sec
                    self.chaps.sort(key=lambda x: x["start"])
                    for chap in self.chaps:
                        if chap.get("subs"):
                            chap["subs"].sort(key=lambda x: x["start"])
                except ValueError:
                    messagebox.showerror(
                        "Tempo Inválido", "O formato do tempo deve ser hh:mm:ss, mm:ss ou apenas segundos."
                    )
                    return

            self.refresh_chap_tree()
            self.on_save()

        def format_time(_: tk.Event) -> None:
            if col == "#0":
                return
            digits = "".join(ch for ch in entry.get() if ch.isdigit())[-6:]
            if len(digits) > 4:
                val = f"{digits[:-4]}:{digits[-4:-2]}:{digits[-2:]}"
            elif len(digits) > 2:
                val = f"{digits[:-2]}:{digits[-2:]}"
            else:
                val = digits
            entry.delete(0, tk.END)
            entry.insert(0, val)
            entry.icursor(tk.END)

        entry.bind("<Return>", commit)
        entry.bind("<Escape>", lambda *_: entry.destroy())
        entry.bind("<FocusOut>", lambda *_: entry.destroy())
        entry.bind("<KeyRelease>", format_time)
