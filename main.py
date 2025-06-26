import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import os, json, vlc

UPDATE_MS = 500                 # refresh UI (ms)


# ---------- helpers ----------
def fmt_sec(sec: int) -> str:           # segundos -> hh:mm:ss / mm:ss
    h, sec = divmod(max(0, sec), 3600)
    m, s = divmod(sec, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def parse_time(txt: str) -> int:        # "hh:mm:ss" / "mm:ss" -> segundos
    parts = [int(p) for p in txt.strip().split(':')]
    if len(parts) == 2:
        m, s = parts; h = 0
    elif len(parts) == 3:
        h, m, s = parts
    else:
        raise ValueError
    return h * 3600 + m * 60 + s


# ---------- player + capítulo ----------
class ChapterEditor(tk.Frame):
    def __init__(self, master, video_path):
        super().__init__(master); self.pack(fill="both", expand=True)
        self.video_path = video_path
        self.json_path = os.path.splitext(video_path)[0] + ".json"
        self.chaps: list[dict] = []        # {title,start,end}  (segundos)

        # VLC
        self.vlc = vlc.Instance()
        self.player = self.vlc.media_player_new()
        self.player.set_media(self.vlc.media_new(video_path))

        # layout = vídeo (esq) + painel (dir)
        main = tk.Frame(self); main.pack(fill="both", expand=True)

        # --- vídeo ---
        vid_box = tk.Frame(main); vid_box.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(vid_box, bg="black")
        self.canvas.pack(fill="both", expand=True)
        self.after(100, self._embed_player)

        controls = tk.Frame(vid_box); controls.pack(fill="x")
        for txt, cmd in (("▶", self.player.play),
                         ("❚❚", self.player.pause),
                         ("■", self.player.stop)):
            tk.Button(controls, text=txt, command=cmd).pack(side="left")

        self.scale = tk.Scale(controls, from_=0, to=1000, showvalue=0,
                              orient="horizontal", length=400,
                              command=lambda v: self._seek(int(v)))
        self.scale.pack(side="left", fill="x", expand=True, padx=5)
        self.time_lbl = tk.Label(controls, text="00:00 / 00:00")
        self.time_lbl.pack(side="right")

        self.drag = False
        self.scale.bind("<ButtonPress-1>", lambda *_: setattr(self, "drag", True))
        self.scale.bind("<ButtonRelease-1>", lambda *_: setattr(self, "drag", False))

        # --- painel de capítulos ---
        side = tk.Frame(main, width=260, relief="groove", bd=1)
        side.pack(side="right", fill="y")
        tk.Label(side, text="Capítulos").pack()

        self.tree = ttk.Treeview(
            side, columns=("title", "start", "end"),
            show="headings", selectmode="browse", height=15)
        self.tree.heading("title", text="Título", anchor="w")
        self.tree.heading("start", text="Início", anchor="e")
        self.tree.heading("end", text="Fim", anchor="e")
        self.tree.column("title", width=150, anchor="w")
        self.tree.column("start", width=80, anchor="e")
        self.tree.column("end", width=80, anchor="e")
        self.tree.pack(fill="both", expand=True, padx=4, pady=2)

        self.tree.bind("<<TreeviewSelect>>", self._jump_to_chapter)
        self.tree.bind("<Double-1>", self._inline_edit)

        btns = tk.Frame(side); btns.pack()
        tk.Button(btns, text="+ adicionar", command=self.add_chapter).pack(side="left", padx=2)
        tk.Button(btns, text="– remover", command=self.rm_chapter).pack(side="left", padx=2)

        self._load_json()
        self.after(UPDATE_MS, self._update_ui)

    # ----------- vídeo ----------
    def _embed_player(self):
        wid = self.canvas.winfo_id()
        (self.player.set_hwnd if os.name == "nt" else self.player.set_xwindow)(wid)

    def _seek(self, scale_val: int):
        if self.drag:   # só aplica depois de soltar
            return
        dur = self.player.get_length()
        if dur > 0:
            self.player.set_time(int(scale_val / 1000 * dur))

    # ----------- capítulos ----------
    def _load_json(self):
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    self.chaps = json.load(f)
            except Exception as e:
                messagebox.showwarning("Capítulos", f"Erro lendo {self.json_path}: {e}")
        self._refresh_tree()

    def _save_json(self):
        try:
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(self.chaps, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Capítulos", f"Erro ao salvar: {e}")

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
        self._refresh_tree();  self._save_json()

    def rm_chapter(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        if messagebox.askyesno("Remover", f"Excluir '{self.chaps[idx]['title']}'?"):
            self.chaps.pop(idx)
            self._refresh_tree();  self._save_json()

    def _jump_to_chapter(self, _):
        sel = self.tree.selection()
        if sel:
            sec = self.chaps[self.tree.index(sel[0])]["start"]
            self.player.set_time(sec * 1000)

    # ----------- inline edit ----------
    def _inline_edit(self, event):
        row_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)  # #1, #2, #3
        if not row_id or col == "#0":
            return
        col_idx = int(col[1:]) - 1
        bbox = self.tree.bbox(row_id, col)
        if not bbox:
            return
        x, y, w, h = bbox
        # entry sobre a célula
        entry = tk.Entry(self.tree)
        entry.place(x=x, y=y, width=w, height=h)
        old_val = self.tree.set(row_id, col)
        entry.insert(0, old_val)
        entry.focus()

        def commit(e=None):
            new_val = entry.get().strip()
            entry.destroy()
            idx = self.tree.index(row_id)
            if col_idx == 0:                      # título
                if new_val:
                    self.chaps[idx]["title"] = new_val
            else:                                # tempos
                try:
                    sec = parse_time(new_val)
                except ValueError:
                    messagebox.showerror("Tempo", "Formato hh:mm:ss ou mm:ss")
                    return
                key = "start" if col_idx == 1 else "end"
                self.chaps[idx][key] = sec
            self._refresh_tree();  self._save_json()

        entry.bind("<Return>", commit)
        entry.bind("<Escape>", lambda *_: entry.destroy())
        entry.bind("<FocusOut>", lambda *_: entry.destroy())

    # ----------- UI loop ----------
    def _update_ui(self):
        dur = self.player.get_length()
        pos = self.player.get_time()
        if dur > 0 and not self.drag:
            # 1) desliga
            self.scale.config(command='')
            # 2) move o slider sem disparar callback
            self.scale.set(int(pos / dur * 1000))
            # 3) liga de novo
            self.scale.config(command=lambda v: self._seek(int(v)))

        self.time_lbl.config(text=f"{fmt_sec(pos//1000)} / {fmt_sec(dur//1000)}")
        self.after(UPDATE_MS, self._update_ui)


# ---------- launcher ----------
def main():
    root = tk.Tk(); root.title("Editor de Capítulos")
    vid = filedialog.askopenfilename(filetypes=[("Vídeo MP4", "*.mp4")])
    if vid:
        ChapterEditor(root, vid)
        root.mainloop()


if __name__ == "__main__":
    main()
