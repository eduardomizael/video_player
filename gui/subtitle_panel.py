"""Painel visual e lógico para gerenciamento de legendas (.srt) com tempo estendido."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from logic import fmt_srt_time, parse_srt_time


class SubtitlePanel(tk.Frame):
    """Painel de legendas com Treeview (tempo estendido), Scrollbar e menu de contexto."""

    def __init__(
        self,
        master: tk.Widget,
        subtitles: list[dict],
        on_save: callable,
        get_current_time_ms: callable,
        on_jump_to_ms: callable,
    ) -> None:
        """Inicializa o painel de legendas."""

        super().__init__(master)
        self.subtitles = subtitles
        self.on_save = on_save
        self.get_current_time_ms = get_current_time_ms
        self.on_jump_to_ms = on_jump_to_ms
        self.item_map: dict[str, dict] = {}

        sub_frame = tk.Frame(self)
        sub_frame.pack(fill="both", expand=True, padx=4, pady=2)

        self.tree = ttk.Treeview(
            sub_frame,
            columns=("start", "end", "text"),
            show="headings",
            selectmode="browse",
            height=15,
        )
        self.tree.heading("start", text="Início", anchor="e")
        self.tree.heading("end", text="Fim", anchor="e")
        self.tree.heading("text", text="Texto da Legenda", anchor="w")

        self.tree.column("start", width=100, anchor="e")
        self.tree.column("end", width=100, anchor="e")
        self.tree.column("text", width=220, anchor="w")

        self.sub_scroll = ttk.Scrollbar(sub_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.sub_scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        self.sub_scroll.pack(side="right", fill="y")

        # Menu de contexto (clique direito)
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="Definir início na posição atual", command=self._set_start_from_current)
        self.context_menu.add_command(label="Definir fim na posição atual", command=self._set_end_from_current)

        self.tree.bind("<ButtonRelease-1>", self._on_tree_left_click)
        self.tree.bind("<KeyRelease-Up>", self._jump_to_subtitle)
        self.tree.bind("<KeyRelease-Down>", self._jump_to_subtitle)
        self.tree.bind("<Double-1>", self._inline_edit)
        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Button-2>", self._show_context_menu)

        btns = tk.Frame(self)
        btns.pack()
        tk.Button(btns, text="+ adicionar", command=self.add_subtitle).pack(side="left", padx=2)
        tk.Button(btns, text="– remover", command=self.rm_subtitle).pack(side="left", padx=2)

        self.refresh_sub_tree()

    def refresh_sub_tree(self) -> None:
        """Atualiza a árvore com a lista de legendas."""
        self.tree.delete(*self.tree.get_children())
        self.item_map = {}

        for sub in self.subtitles:
            item_id = self.tree.insert(
                "",
                "end",
                values=(
                    fmt_srt_time(sub["start"]),
                    fmt_srt_time(sub["end"]),
                    sub.get("text", ""),
                ),
            )
            self.item_map[item_id] = sub

    def add_subtitle(self) -> None:
        """Cria uma nova entrada de legenda na posição atual de reprodução."""
        cur_ms = self.get_current_time_ms()
        end_ms = cur_ms + 3000
        text = f"Legenda {len(self.subtitles) + 1}"
        new_sub = {"start": cur_ms, "end": end_ms, "text": text}
        self.subtitles.append(new_sub)
        self.subtitles.sort(key=lambda x: x["start"])
        self.refresh_sub_tree()
        self.on_save()

    def rm_subtitle(self) -> None:
        """Remove a legenda selecionada após confirmação."""
        sel = self.tree.selection()
        if not sel:
            return
        item = sel[0]
        node = self.item_map.get(item)
        if node is None:
            return
        if messagebox.askyesno("Remover Legenda", f"Excluir legenda '{node.get('text', '')}'?"):
            self.subtitles.remove(node)
            self.refresh_sub_tree()
            self.on_save()

    def _on_tree_left_click(self, event: tk.Event) -> None:
        """Leva a reprodução para o início da legenda clicada com o botão esquerdo."""
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        node = self.item_map.get(row_id)
        if node:
            self.on_jump_to_ms(node["start"])

    def _jump_to_subtitle(self, _) -> None:
        """Leva a reprodução para o início da legenda selecionada por teclado."""
        sel = self.tree.selection()
        if sel:
            node = self.item_map.get(sel[0])
            if node:
                self.on_jump_to_ms(node["start"])

    def _show_context_menu(self, event: tk.Event) -> None:
        """Exibe o menu de contexto ao clicar com o botão direito em uma legenda."""
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        self.tree.selection_set(row_id)
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def _set_start_from_current(self) -> None:
        """Define o tempo de início da legenda para a posição atual do vídeo."""
        sel = self.tree.selection()
        if not sel:
            return
        node = self.item_map.get(sel[0])
        if not node:
            return
        cur_ms = self.get_current_time_ms()
        node["start"] = cur_ms
        self.subtitles.sort(key=lambda x: x["start"])
        self.refresh_sub_tree()
        self.on_save()

    def _set_end_from_current(self) -> None:
        """Define o tempo de fim da legenda para a posição atual do vídeo."""
        sel = self.tree.selection()
        if not sel:
            return
        node = self.item_map.get(sel[0])
        if not node:
            return
        cur_ms = self.get_current_time_ms()
        node["end"] = cur_ms
        self.refresh_sub_tree()
        self.on_save()

    def _inline_edit(self, event: tk.Event) -> None:
        """Permite editar tempos (com milissegundos) ou texto da legenda diretamente na árvore."""
        row_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not row_id:
            return
        bbox = self.tree.bbox(row_id, col)
        if not bbox:
            return
        x, y, w, h = bbox
        entry = tk.Entry(self.tree, justify="right" if col in ("#1", "#2") else "left")
        entry.place(x=x, y=y, width=w, height=h)
        old_val = self.tree.set(row_id, col)
        entry.insert(0, old_val)
        entry.focus()

        def commit(e: tk.Event | None = None) -> None:
            new_val = entry.get().strip()
            entry.destroy()
            node = self.item_map.get(row_id)
            if not node:
                return

            if col == "#3":
                node["text"] = new_val
            else:
                try:
                    ms = parse_srt_time(new_val)
                    key = "start" if col == "#1" else "end"
                    node[key] = ms
                    self.subtitles.sort(key=lambda x: x["start"])
                except ValueError:
                    messagebox.showerror("Tempo Inválido", "Formato inválido. Use hh:mm:ss,mss ou mm:ss,mss.")
                    return

            self.refresh_sub_tree()
            self.on_save()

        entry.bind("<Return>", commit)
        entry.bind("<Escape>", lambda *_: entry.destroy())
        entry.bind("<FocusOut>", lambda *_: entry.destroy())
