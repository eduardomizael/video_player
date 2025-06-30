import os
import tkinter as tk
from tkinter import messagebox, ttk
import vlc

from logic import ChapterManager, fmt_sec, parse_flexible_time
from config import save_config


class SettingsWindow(tk.Toplevel):
    """Diálogo simples para editar e salvar as configurações."""

    def __init__(self, master: tk.Tk, config: dict, on_save: callable) -> None:
        """Cria a janela com a configuração atual."""

        super().__init__(master)
        self.title("Configurações")
        self.config = config
        self.on_save = on_save

        # Configurar janela modal e sempre no topo
        self.transient(master)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        tk.Label(self, text="Atualização (ms)").grid(row=0, column=0, sticky="e")
        self.update_var = tk.StringVar(value=str(config.get("update_ms", 500)))
        tk.Entry(self, textvariable=self.update_var, width=8).grid(row=0, column=1)

        tk.Label(self, text="Salto curto (s)").grid(row=1, column=0, sticky="e")
        self.small_var = tk.StringVar(value=str(config.get("small_jump", 5)))
        tk.Entry(self, textvariable=self.small_var, width=8).grid(row=1, column=1)

        tk.Label(self, text="Salto longo (s)").grid(row=2, column=0, sticky="e")
        self.large_var = tk.StringVar(value=str(config.get("large_jump", 20)))
        tk.Entry(self, textvariable=self.large_var, width=8).grid(row=2, column=1)

        self.key_vars: dict[str, tk.StringVar] = {}
        labels = [
            ("play_pause", "Play/Pause"),
            ("back_small", "Voltar curto"),
            ("fwd_small", "Avançar curto"),
            ("back_large", "Voltar longo"),
            ("fwd_large", "Avançar longo"),
        ]
        for i, (key, lbl) in enumerate(labels, start=3):
            tk.Label(self, text=lbl).grid(row=i, column=0, sticky="e")
            var = tk.StringVar(value=config.get("keys", {}).get(key, ""))
            ent = tk.Entry(self, textvariable=var, width=15)
            ent.grid(row=i, column=1)
            ent.bind("<Key>", lambda e, v=var: self._capture_key(e, v))
            self.key_vars[key] = var

        tk.Button(self, text="Salvar", command=self.save).grid(row=i + 1, column=0, columnspan=2, pady=5)

        self.resizable(False, False)
        self.grab_set()

        # Centralizar a janela em relação à janela principal
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = master.winfo_x() + (master.winfo_width() - width) // 2
        y = master.winfo_y() + (master.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _capture_key(self, event: tk.Event, var: tk.StringVar) -> str:
        """Captura a tecla pressionada e salva como string de atalho do Tk."""
        mods = []
        if event.state & 0x4:
            mods.append("Control")
        if event.state & 0x1:
            mods.append("Shift")
        if event.state & 0x8:
            mods.append("Alt")
        var.set("<" + "-".join(mods + [event.keysym]) + ">")
        return "break"

    def save(self) -> None:
        """Salva a configuração e avisa o chamador."""
        self.config["update_ms"] = int(self.update_var.get() or 500)
        self.config["small_jump"] = int(self.small_var.get() or 5)
        self.config["large_jump"] = int(self.large_var.get() or 20)
        keys = self.config.setdefault("keys", {})
        for k, var in self.key_vars.items():
            val = var.get().strip() or keys.get(k, "")
            keys[k] = val
        save_config(self.config)
        self.on_save()
        self.destroy()


class ChapterEditor(tk.Frame):
    """Widget Tkinter que incorpora o player VLC e o editor de capítulos."""

    def __init__(self, master: tk.Tk, video_path: str, config: dict) -> None:
        """Inicializa o editor para o vídeo informado."""

        super().__init__(master)
        self.pack(fill="both", expand=True)

        self.config = config
        self.update_ms = config.get("update_ms", 500)
        self.small_jump = config.get("small_jump", 5)
        self.large_jump = config.get("large_jump", 20)

        self.manager = ChapterManager(video_path)
        data = self.manager.load()
        self.chaps: list[dict] = data.get("chapters", [])
        self.casting: list[str] = data.get("casting", [])

        # VLC setup
        self.vlc = vlc.Instance()
        self.player = self.vlc.media_player_new()
        self.player.set_media(self.vlc.media_new(video_path))

        main = tk.Frame(self)
        main.pack(fill="both", expand=True)

        # --- video widget ---
        vid_box = tk.Frame(main)
        vid_box.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(vid_box, bg="black")
        self.canvas.pack(fill="both", expand=True)
        self.after(100, self._embed_player)

        controls = tk.Frame(vid_box)
        controls.pack(fill="x")

        self.back_large_btn = tk.Button(
            controls,
            text=f"«{self.large_jump}s",
            command=lambda: self._jump(-self.large_jump),
        )
        self.back_large_btn.pack(side="left")
        self.back_small_btn = tk.Button(
            controls,
            text=f"‹{self.small_jump}s",
            command=lambda: self._jump(-self.small_jump),
        )
        self.back_small_btn.pack(side="left")

        for txt, cmd in (("▶", self.player.play), ("❚❚", self.player.pause), ("■", self.player.stop)):
            tk.Button(controls, text=txt, command=cmd).pack(side="left")

        self.fwd_small_btn = tk.Button(
            controls,
            text=f"{self.small_jump}s›",
            command=lambda: self._jump(self.small_jump),
        )
        self.fwd_small_btn.pack(side="left")
        self.fwd_large_btn = tk.Button(
            controls,
            text=f"{self.large_jump}s»",
            command=lambda: self._jump(self.large_jump),
        )
        self.fwd_large_btn.pack(side="left")

        self.scale = tk.Scale(
            controls,
            from_=0,
            to=1000,
            showvalue=0,
            orient="horizontal",
            length=400,
            command=lambda v: self._seek(int(v)),
        )
        self.scale.pack(side="left", fill="x", expand=True, padx=5)
        self.time_lbl = tk.Label(controls, text="00:00 / 00:00")
        self.time_lbl.pack(side="right")

        self.updater = None
        self.scale.bind("<ButtonPress-1>", self._drag_start)
        self.scale.bind("<ButtonRelease-1>", self._drag_end)

        # --- chapter panel ---
        side = tk.Frame(main, width=260, relief="groove", bd=1)
        side.pack(side="right", fill="y")

        self.notebook = ttk.Notebook(side)
        self.notebook.pack(fill="both", expand=True)

        chap_tab = tk.Frame(self.notebook)
        self.notebook.add(chap_tab, text="Capítulos")

        self.tree = ttk.Treeview(
            chap_tab,
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
        self.tree.pack(fill="both", expand=True, padx=4, pady=2)

        self.tree.bind("<<TreeviewSelect>>", self._jump_to_chapter)
        self.tree.bind("<Double-1>", self._inline_edit)

        btns = tk.Frame(chap_tab)
        btns.pack()
        tk.Button(btns, text="+ adicionar", command=self.add_chapter).pack(side="left", padx=2)
        tk.Button(btns, text="+ sub", command=self.add_subchapter).pack(side="left", padx=2)
        tk.Button(btns, text="– remover", command=self.rm_chapter).pack(side="left", padx=2)

        cast_tab = tk.Frame(self.notebook)
        self.notebook.add(cast_tab, text="Casting")

        self.cast_tree = ttk.Treeview(
            cast_tab,
            columns=("name",),
            show="headings",
            selectmode="browse",
            height=15,
        )
        self.cast_tree.heading("name", text="Nome", anchor="w")
        self.cast_tree.column("name", width=200, anchor="w")
        self.cast_tree.pack(fill="both", expand=True, padx=4, pady=2)
        self.cast_tree.bind("<Double-1>", self._inline_edit_cast)

        cast_btns = tk.Frame(cast_tab)
        cast_btns.pack()
        tk.Button(cast_btns, text="+ adicionar", command=self.add_cast).pack(side="left", padx=2)
        tk.Button(cast_btns, text="– remover", command=self.rm_cast).pack(side="left", padx=2)

        self._refresh_chap_tree()
        self._refresh_cast_tree()
        self._start_update_loop()
        self._bind_keys()

    def destroy(self) -> None:
        """Interrompe a reprodução e libera recursos do VLC."""
        self._stop_update_loop()
        self.player.stop()
        self.player.release()
        self.vlc.release()
        super().destroy()

    def update_config(self, config: dict) -> None:
        """Aplica a configuração atualizada ao editor."""
        self.config = config
        self.update_ms = config.get("update_ms", self.update_ms)
        self.small_jump = config.get("small_jump", self.small_jump)
        self.large_jump = config.get("large_jump", self.large_jump)
        self.back_small_btn.config(text=f"‹{self.small_jump}s")
        self.back_large_btn.config(text=f"«{self.large_jump}s")
        self.fwd_small_btn.config(text=f"{self.small_jump}s›")
        self.fwd_large_btn.config(text=f"{self.large_jump}s»")
        self._bind_keys()

    # ----------- video helpers ----------
    def _embed_player(self) -> None:
        """Conecta o player VLC ao canvas do Tk."""

        wid = self.canvas.winfo_id()
        if os.name == "nt":
            self.player.set_hwnd(wid)
        else:
            self.player.set_xwindow(wid)

    def _seek(self, scale_val: int) -> None:
        """Move o vídeo conforme o valor do controle deslizante."""

        dur = self.player.get_length()
        if dur > 0:
            self.player.set_time(int(scale_val / 1000 * dur))

    def _jump(self, secs: int) -> None:
        """Avança ou retrocede o número de segundos indicado."""
        cur = self.player.get_time()
        self.player.set_time(max(0, cur + secs * 1000))

    # ----------- chapters ----------
    def _refresh_chap_tree(self) -> None:
        """Atualiza a árvore com a lista de capítulos."""

        self.tree.delete(*self.tree.get_children())
        self.item_map: dict[str, dict] = {}

        def add_items(parent: str, items: list[dict]) -> None:
            for chap in items:
                item_id = self.tree.insert(
                    parent,
                    "end",
                    text=chap["title"],
                    values=(fmt_sec(chap["start"]), fmt_sec(chap["end"])),
                    open=True,
                )
                self.item_map[item_id] = chap
                add_items(item_id, chap.get("subs", []))

        add_items("", self.chaps)

    def add_chapter(self) -> None:
        """Cria um novo capítulo na posição atual de reprodução."""

        cur_sec = self.player.get_time() // 1000
        title = f"Capítulo {len(self.chaps) + 1}"
        end_sec = self.player.get_length() // 1000 or cur_sec + 10
        self.chaps.append({"title": title, "start": cur_sec, "end": end_sec, "subs": []})
        self.chaps.sort(key=lambda x: x["start"])
        self._refresh_chap_tree()
        self.manager.save(self.chaps, self.casting)

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
        subs.append({"title": title, "start": parent["start"], "end": parent["end"]})
        self._refresh_chap_tree()
        self.manager.save(self.chaps, self.casting)

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
        self._refresh_chap_tree()
        self.manager.save(self.chaps, self.casting)

    def _jump_to_chapter(self, _) -> None:
        """Leva a reprodução para o início do capítulo escolhido."""

        sel = self.tree.selection()
        if sel:
            node = self.item_map.get(sel[0])
            if node:
                self.player.set_time(node["start"] * 1000)

    # ----------- inline edit ----------
    def _inline_edit(self, event: tk.Event) -> None:
        """Permite editar título ou tempos diretamente na árvore."""

        row_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not row_id:
            return
        # col_idx = 0 if col == "#0" else int(col[1:])
        bbox = self.tree.bbox(row_id, col)
        if not bbox:
            return
        x, y, w, h = bbox
        entry = tk.Entry(self.tree)
        entry.place(x=x, y=y, width=w, height=h)
        if col == "#0":
            old_val = self.tree.item(row_id, "text")
        else:
            old_val = self.tree.set(row_id, col)
        entry.insert(0, old_val)
        entry.focus()

        def commit(e: tk.Event | None = None) -> None:
            """Finaliza a edição e atualiza a lista de capítulos."""
            new_val = entry.get().strip()
            entry.destroy()
            node = self.item_map.get(row_id)
            if not node:
                return
            if col == '#0':
                if new_val:
                    node["title"] = new_val
            else:
                try:
                    sec = parse_flexible_time(new_val)
                except ValueError:
                    messagebox.showerror(
                        "Tempo",
                        "Formato hh:mm:ss, mm:ss ou somente dígitos",
                    )
                    return
                key = "start" if col == "#1" else "end"
                node[key] = sec
            self._refresh_chap_tree()
            self.manager.save(self.chaps, self.casting)

        def format_time(_: tk.Event) -> None:
            """Formata os dígitos digitados como tempo durante a edição."""
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

    # ----------- casting ----------
    def _refresh_cast_tree(self) -> None:
        """Atualiza a lista de casting."""

        self.cast_tree.delete(*self.cast_tree.get_children())
        for name in self.casting:
            self.cast_tree.insert("", "end", values=(name,))

    def add_cast(self) -> None:
        """Adiciona um novo nome à lista de casting."""

        self.casting.append("Novo nome")
        self._refresh_cast_tree()
        self.manager.save(self.chaps, self.casting)

    def rm_cast(self) -> None:
        """Remove o nome selecionado após confirmação."""

        sel = self.cast_tree.selection()
        if not sel:
            return
        idx = self.cast_tree.index(sel[0])
        if messagebox.askyesno("Remover", f"Excluir '{self.casting[idx]}'?"):
            self.casting.pop(idx)
            self._refresh_cast_tree()
            self.manager.save(self.chaps, self.casting)

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
            if new_val:
                self.casting[idx] = new_val
                self._refresh_cast_tree()
                self.manager.save(self.chaps, self.casting)

        entry.bind("<Return>", commit)
        entry.bind("<Escape>", lambda *_: entry.destroy())
        entry.bind("<FocusOut>", lambda *_: entry.destroy())

    # ----------- UI loop ----------
    def _start_update_loop(self) -> None:
        """Agenda a atualização periódica da interface."""

        self.updater = self.after(self.update_ms, self._update_ui)

    def _stop_update_loop(self) -> None:
        """Cancela a atualização periódica se estiver ativa."""

        if self.updater:
            self.after_cancel(self.updater)
            self.updater = None

    def _update_ui(self) -> None:
        """Atualiza posição do slider e o rótulo de tempo."""

        dur = self.player.get_length()
        pos = self.player.get_time()
        if dur > 0:
            # evita que a atualização do slider altere o tempo do vídeo
            self.scale.config(command="")
            self.scale.set(int(pos / dur * 1000))
            self.scale.config(command=lambda v: self._seek(int(v)))
            self.time_lbl.config(text=f"{fmt_sec(pos//1000)} / {fmt_sec(dur//1000)}")
        self._start_update_loop()  # agenda o próximo

    # ------------- drag -------------
    def _drag_start(self, _: tk.Event) -> None:
        """Pausa as atualizações enquanto o slider é arrastado."""

        self._stop_update_loop()  # congela o loop

    def _drag_end(self, _: tk.Event) -> None:
        """Vai para a nova posição e retoma as atualizações."""

        val = self.scale.get()
        dur = self.player.get_length()
        if dur > 0:
            self.player.set_time(int(val / 1000 * dur))
        self._start_update_loop()

    # ----------- key bindings ---------
    def _bind_keys(self) -> None:
        """Configura os atalhos de teclado definidos na configuração."""

        keys = self.config.get("keys", {})
        root = self.winfo_toplevel()

        root.bind(keys.get("play_pause", "<space>"), lambda _: self._play_pause())
        root.bind(keys.get("back_small", "<Left>"), lambda _: self._jump(-self.small_jump))
        root.bind(keys.get("fwd_small", "<Right>"), lambda _: self._jump(self.small_jump))
        root.bind(keys.get("back_large", "<Shift-Left>"), lambda _: self._jump(-self.large_jump))
        root.bind(keys.get("fwd_large", "<Shift-Right>"), lambda _: self._jump(self.large_jump))

    def _play_pause(self) -> None:
        """Alterna entre reproduzir e pausar."""

        if self.player.is_playing():
            self.player.pause()
        else:
            self.player.play()
