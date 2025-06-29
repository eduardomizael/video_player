import os
import tkinter as tk
from tkinter import messagebox, ttk
import vlc

from logic import ChapterManager, fmt_sec, parse_flexible_time

UPDATE_MS = 500  # refresh UI in ms


class ChapterEditor(tk.Frame):
    """Tkinter widget that embeds a VLC player and chapter editor."""

    def __init__(self, master, video_path: str):
        super().__init__(master)
        self.pack(fill="both", expand=True)

        self.manager = ChapterManager(video_path)
        self.chaps: list[dict] = self.manager.load()

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
        for txt, cmd in (("▶", self.player.play),
                         ("❚❚", self.player.pause),
                         ("■", self.player.stop)):
            tk.Button(controls, text=txt, command=cmd).pack(side="left")

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

        # self.drag = False
        # self.scale.bind("<ButtonPress-1>", lambda *_: setattr(self, "drag", True))
        # self.scale.bind("<ButtonRelease-1>", lambda *_: setattr(self, "drag", False))
        self.updater = None
        self.scale.bind("<ButtonPress-1>", self._drag_start)
        self.scale.bind("<ButtonRelease-1>", self._drag_end)

        # --- chapter panel ---
        side = tk.Frame(main, width=260, relief="groove", bd=1)
        side.pack(side="right", fill="y")
        tk.Label(side, text="Capítulos").pack()

        self.tree = ttk.Treeview(
            side,
            columns=("title", "start", "end"),
            show="headings",
            selectmode="browse",
            height=15,
        )
        self.tree.heading("title", text="Título", anchor="w")
        self.tree.heading("start", text="Início", anchor="e")
        self.tree.heading("end", text="Fim", anchor="e")
        self.tree.column("title", width=150, anchor="w")
        self.tree.column("start", width=80, anchor="e")
        self.tree.column("end", width=80, anchor="e")
        self.tree.pack(fill="both", expand=True, padx=4, pady=2)

        self.tree.bind("<<TreeviewSelect>>", self._jump_to_chapter)
        self.tree.bind("<Double-1>", self._inline_edit)

        btns = tk.Frame(side)
        btns.pack()
        tk.Button(btns, text="+ adicionar", command=self.add_chapter).pack(side="left", padx=2)
        tk.Button(btns, text="– remover", command=self.rm_chapter).pack(side="left", padx=2)

        self._refresh_tree()
        # self.after(UPDATE_MS, self._update_ui)
        self._start_update_loop()

    # ----------- video helpers ----------
    def _embed_player(self):
        wid = self.canvas.winfo_id()
        if os.name == "nt":
            self.player.set_hwnd(wid)
        else:
            self.player.set_xwindow(wid)

    def _seek(self, scale_val: int):
        dur = self.player.get_length()
        if dur > 0:
            self.player.set_time(int(scale_val / 1000 * dur))

    # ----------- chapters ----------
    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for c in self.chaps:
            self.tree.insert("", "end", values=(c["title"], fmt_sec(c["start"]), fmt_sec(c["end"])))

    def add_chapter(self):
        cur_sec = self.player.get_time() // 1000
        title = f"Capítulo {len(self.chaps) + 1}"
        end_sec = self.player.get_length() // 1000 or cur_sec + 10
        self.chaps.append({"title": title, "start": cur_sec, "end": end_sec})
        self.chaps.sort(key=lambda x: x["start"])
        self._refresh_tree()
        self.manager.save(self.chaps)

    def rm_chapter(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        if messagebox.askyesno("Remover", f"Excluir '{self.chaps[idx]['title']}'?"):
            self.chaps.pop(idx)
            self._refresh_tree()
            self.manager.save(self.chaps)

    def _jump_to_chapter(self, _):
        sel = self.tree.selection()
        if sel:
            sec = self.chaps[self.tree.index(sel[0])]["start"]
            self.player.set_time(sec * 1000)

    # ----------- inline edit ----------
    def _inline_edit(self, event):
        row_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not row_id or col == "#0":
            return
        col_idx = int(col[1:]) - 1
        bbox = self.tree.bbox(row_id, col)
        if not bbox:
            return
        x, y, w, h = bbox
        entry = tk.Entry(self.tree)
        entry.place(x=x, y=y, width=w, height=h)
        old_val = self.tree.set(row_id, col)
        entry.insert(0, old_val)
        entry.focus()

        def commit(e=None):
            new_val = entry.get().strip()
            entry.destroy()
            idx = self.tree.index(row_id)
            if col_idx == 0:
                if new_val:
                    self.chaps[idx]["title"] = new_val
            else:
                try:
                    sec = parse_flexible_time(new_val)
                except ValueError:
                    messagebox.showerror(
                        "Tempo",
                        "Formato hh:mm:ss, mm:ss ou somente dígitos",
                    )
                    return
                key = "start" if col_idx == 1 else "end"
                self.chaps[idx][key] = sec
            self._refresh_tree()
            self.manager.save(self.chaps)

        def format_time(_):
            if col_idx == 0:
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

    # ----------- UI loop ----------
    def _start_update_loop(self):
        self.updater = self.after(UPDATE_MS, self._update_ui)

    def _stop_update_loop(self):
        if self.updater:
            self.after_cancel(self.updater)
            self.updater = None

    # def _update_ui(self):
    #     dur = self.player.get_length()
    #     pos = self.player.get_time()
    #     if dur > 0 and not self.drag:
    #         self.scale.config(command='')
    #         self.scale.set(int(pos / dur * 1000))
    #         self.scale.config(command=lambda v: self._seek(int(v)))

    #     self.time_lbl.config(text=f"{fmt_sec(pos//1000)} / {fmt_sec(dur//1000)}")
    #     self.after(UPDATE_MS, self._update_ui)

    def _update_ui(self):
        dur = self.player.get_length()
        pos = self.player.get_time()
        if dur > 0:
            self.scale.set(int(pos / dur * 1000))
            self.time_lbl.config(text=f"{fmt_sec(pos//1000)} / {fmt_sec(dur//1000)}")
        self._start_update_loop()      # agenda o próximo

    # ------------- drag -------------
    def _drag_start(self, _):
        self._stop_update_loop()       # congela o loop

    def _drag_end(self, _):
        val = self.scale.get()
        dur = self.player.get_length()
        if dur > 0:
            self.player.set_time(int(val / 1000 * dur))
        self._start_update_loop()   