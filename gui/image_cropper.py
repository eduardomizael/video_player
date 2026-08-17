"""Janela para enquadrar e recortar imagens antes de armazená-las."""

from __future__ import annotations

import io
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageGrab, ImageTk

CROP_PRESETS = {
    "Quadrada (1080 × 1080)": (1080, 1080),
    "Card vertical (1080 × 1350)": (1080, 1350),
    "Heading horizontal (1920 × 1080)": (1920, 1080),
}


class ImageCropper(tk.Toplevel):
    """Permite mover e ampliar uma imagem sob uma moldura de proporção fixa."""

    def __init__(self, master: tk.Widget, on_crop: Callable[[dict], None]) -> None:
        """Cria a janela modal e aguarda uma imagem de arquivo ou da área de transferência."""

        super().__init__(master)
        self.title("Preparar imagem")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.on_crop = on_crop
        self.source: Image.Image | None = None
        self.preview: ImageTk.PhotoImage | None = None
        self.scale = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.drag_start: tuple[int, int] | None = None
        self.frame_box = (0.0, 0.0, 0.0, 0.0)

        top = tk.Frame(self, padx=10, pady=8)
        top.pack(fill="x")
        tk.Button(top, text="Abrir imagem", command=self.open_image).pack(side="left")
        tk.Button(top, text="Colar imagem", command=self.paste_image).pack(side="left", padx=(6, 12))
        tk.Label(top, text="Proporção:").pack(side="left")
        self.preset_var = tk.StringVar(value=next(iter(CROP_PRESETS)))
        preset = ttk.Combobox(top, textvariable=self.preset_var, values=list(CROP_PRESETS), state="readonly", width=31)
        preset.pack(side="left", padx=4)
        preset.bind("<<ComboboxSelected>>", lambda _: self.reset_view())

        self.canvas = tk.Canvas(self, width=700, height=500, bg="#252525", highlightthickness=0)
        self.canvas.pack(padx=10, pady=(0, 8))
        self.canvas.bind("<ButtonPress-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<MouseWheel>", self._zoom)
        self.canvas.bind("<Button-4>", self._zoom)
        self.canvas.bind("<Button-5>", self._zoom)

        details = tk.Frame(self, padx=10)
        details.pack(fill="x")
        tk.Label(details, text="Título:").grid(row=0, column=0, sticky="w")
        self.title_var = tk.StringVar()
        tk.Entry(details, textvariable=self.title_var, width=52).grid(row=0, column=1, sticky="ew", padx=(6, 0))
        tk.Label(details, text="Descrição:").grid(row=1, column=0, sticky="nw", pady=(6, 0))
        self.description = tk.Text(details, width=40, height=3)
        self.description.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=(6, 0))
        details.columnconfigure(1, weight=1)

        footer = tk.Frame(self, padx=10, pady=10)
        footer.pack(fill="x")
        tk.Label(footer, text="Arraste para posicionar; use a roda do mouse para ampliar.").pack(side="left")
        tk.Button(footer, text="Cancelar", command=self.destroy).pack(side="right")
        tk.Button(footer, text="Salvar recorte", command=self.save_crop).pack(side="right", padx=(0, 6))
        self.bind("<Control-v>", lambda _: self.paste_image())
        self.grab_set()
        self._draw()
        self._center_over_parent()

    def _center_over_parent(self) -> None:
        """Centraliza o recortador dentro da janela principal da aplicação."""

        self.update_idletasks()
        parent = self.master.winfo_toplevel()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"{self.winfo_width()}x{self.winfo_height()}+{max(0, x)}+{max(0, y)}")

    def open_image(self) -> None:
        """Abre uma imagem escolhida pelo usuário."""

        path = filedialog.askopenfilename(
            parent=self,
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"), ("Todos os arquivos", "*.*")],
        )
        if not path:
            return
        try:
            with Image.open(path) as image:
                self._set_source(image.copy(), Path(path).stem)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Imagem inválida", str(exc), parent=self)

    def paste_image(self) -> None:
        """Lê uma imagem ou um caminho de imagem presente na área de transferência."""

        try:
            clipboard = ImageGrab.grabclipboard()
        except OSError as exc:
            messagebox.showerror("Área de transferência indisponível", str(exc), parent=self)
            return
        if isinstance(clipboard, Image.Image):
            self._set_source(clipboard.copy(), "Imagem colada")
            return
        if isinstance(clipboard, list) and clipboard:
            try:
                with Image.open(clipboard[0]) as image:
                    self._set_source(image.copy(), Path(clipboard[0]).stem)
                return
            except (OSError, ValueError):
                pass
        messagebox.showinfo("Nenhuma imagem", "Copie uma imagem ou um arquivo de imagem antes de colar.", parent=self)

    def _set_source(self, image: Image.Image, default_title: str) -> None:
        """Define a imagem de origem e prepara um enquadramento que a cubra por inteiro."""

        self.source = image
        self.title_var.set(default_title)
        self.reset_view()

    def _crop_dimensions(self) -> tuple[int, int]:
        """Retorna a resolução de saída correspondente à opção atual."""

        return CROP_PRESETS[self.preset_var.get()]

    def _update_frame_box(self) -> None:
        """Centraliza no canvas a moldura que representa o recorte final."""

        output_width, output_height = self._crop_dimensions()
        ratio = output_width / output_height
        canvas_width = int(self.canvas["width"])
        canvas_height = int(self.canvas["height"])
        frame_width = min(canvas_width * 0.84, canvas_height * 0.84 * ratio)
        frame_height = frame_width / ratio
        if frame_height > canvas_height * 0.84:
            frame_height = canvas_height * 0.84
            frame_width = frame_height * ratio
        left = (canvas_width - frame_width) / 2
        top = (canvas_height - frame_height) / 2
        self.frame_box = (left, top, left + frame_width, top + frame_height)

    def reset_view(self) -> None:
        """Reinicia zoom e posição, cobrindo a área de recorte sem faixas vazias."""

        self._update_frame_box()
        if self.source is None:
            self._draw()
            return
        left, top, right, bottom = self.frame_box
        frame_width, frame_height = right - left, bottom - top
        self.scale = max(frame_width / self.source.width, frame_height / self.source.height)
        self.offset_x = (int(self.canvas["width"]) - self.source.width * self.scale) / 2
        self.offset_y = (int(self.canvas["height"]) - self.source.height * self.scale) / 2
        self._clamp_offset()
        self._draw()

    def _clamp_offset(self) -> None:
        """Impede que o enquadramento revele área vazia fora da imagem."""

        if self.source is None:
            return
        left, top, right, bottom = self.frame_box
        image_width = self.source.width * self.scale
        image_height = self.source.height * self.scale
        self.offset_x = min(left, max(right - image_width, self.offset_x))
        self.offset_y = min(top, max(bottom - image_height, self.offset_y))

    def _draw(self) -> None:
        """Redesenha imagem, escurecimento externo e moldura de recorte."""

        self.canvas.delete("all")
        self._update_frame_box()
        if self.source is not None:
            preview_size = (
                max(1, round(self.source.width * self.scale)),
                max(1, round(self.source.height * self.scale)),
            )
            rendered = self.source.resize(preview_size, Image.Resampling.LANCZOS)
            self.preview = ImageTk.PhotoImage(rendered)
            self.canvas.create_image(self.offset_x, self.offset_y, image=self.preview, anchor="nw")
        left, top, right, bottom = self.frame_box
        width, height = int(self.canvas["width"]), int(self.canvas["height"])
        for coords in (
            (0, 0, width, top),
            (0, bottom, width, height),
            (0, top, left, bottom),
            (right, top, width, bottom),
        ):
            self.canvas.create_rectangle(*coords, fill="#000000", stipple="gray50", outline="")
        self.canvas.create_rectangle(left, top, right, bottom, outline="#ffffff", width=2)

    def _start_drag(self, event: tk.Event) -> None:
        """Inicia o deslocamento manual da imagem."""

        self.drag_start = (event.x, event.y)

    def _drag(self, event: tk.Event) -> None:
        """Move a imagem mantendo-a sobre a moldura."""

        if self.source is None or self.drag_start is None:
            return
        self.offset_x += event.x - self.drag_start[0]
        self.offset_y += event.y - self.drag_start[1]
        self.drag_start = (event.x, event.y)
        self._clamp_offset()
        self._draw()

    def _zoom(self, event: tk.Event) -> str:
        """Amplia ou reduz a imagem em torno do centro da moldura."""

        if self.source is None:
            return "break"
        direction = 1 if getattr(event, "delta", 0) > 0 or getattr(event, "num", 0) == 4 else -1
        factor = 1.12 if direction > 0 else 1 / 1.12
        left, top, right, bottom = self.frame_box
        center_x, center_y = (left + right) / 2, (top + bottom) / 2
        old_scale = self.scale
        minimum = max((right - left) / self.source.width, (bottom - top) / self.source.height)
        self.scale = max(minimum, self.scale * factor)
        self.offset_x = center_x - (center_x - self.offset_x) * self.scale / old_scale
        self.offset_y = center_y - (center_y - self.offset_y) * self.scale / old_scale
        self._clamp_offset()
        self._draw()
        return "break"

    def save_crop(self) -> None:
        """Recorta e comprime a imagem final antes de entregá-la ao painel."""

        if self.source is None:
            messagebox.showerror("Imagem ausente", "Abra ou cole uma imagem antes de salvar.", parent=self)
            return
        left, top, right, bottom = self.frame_box
        crop_box = (
            round((left - self.offset_x) / self.scale),
            round((top - self.offset_y) / self.scale),
            round((right - self.offset_x) / self.scale),
            round((bottom - self.offset_y) / self.scale),
        )
        output_width, output_height = self._crop_dimensions()
        cropped = self.source.crop(crop_box).resize((output_width, output_height), Image.Resampling.LANCZOS)
        rgba = cropped.convert("RGBA")
        has_transparency = rgba.getchannel("A").getextrema()[0] < 255
        stream = io.BytesIO()
        if has_transparency:
            rgba.save(stream, format="PNG", optimize=True)
            mime_type = "image/png"
        else:
            cropped.convert("RGB").save(stream, format="JPEG", quality=88, optimize=True, progressive=True)
            mime_type = "image/jpeg"
        self.on_crop(
            {
                "title": self.title_var.get().strip(),
                "description": self.description.get("1.0", "end-1c").strip(),
                "data": stream.getvalue(),
                "mime_type": mime_type,
                "width": output_width,
                "height": output_height,
            }
        )
        self.destroy()
