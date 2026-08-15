"""Widget de botão personalizado com cantos arredondados suavizados para Tkinter."""

from __future__ import annotations

import tkinter as tk


class RoundedButton(tk.Canvas):
    """Botão em Canvas com cantos arredondados e efeitos visuais ao passar/clicar o mouse."""

    def __init__(
        self,
        master: tk.Widget,
        text: str,
        command: callable,
        width: int = 54,
        height: int = 28,
        radius: int = 10,
        bg_color: str = "#ffffff",
        fg_color: str = "#222222",
        hover_bg: str = "#e4e4e4",
        pressed_bg: str = "#d0d0d0",
        border_color: str = "#b8b8b8",
        font: tuple = ("Segoe UI", 9, "bold"),
        cursor: str = "hand2",
    ) -> None:
        """Inicializa o botão arredondado."""

        bg_parent = "#e8e8e8"
        if hasattr(master, "cget"):
            try:
                bg_parent = master.cget("bg")
            except Exception:
                pass

        super().__init__(
            master,
            width=width,
            height=height,
            bg=bg_parent,
            highlightthickness=0,
            bd=0,
            cursor=cursor,
        )
        self.command = command
        self.text = text
        self.radius = radius
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.hover_bg = hover_bg
        self.pressed_bg = pressed_bg
        self.border_color = border_color
        self.font = font

        self.btn_rect = None
        self.btn_text = None
        self._draw(self.bg_color)

        self.bind("<Enter>", lambda _: self._draw(self.hover_bg))
        self.bind("<Leave>", lambda _: self._draw(self.bg_color))
        self.bind("<ButtonPress-1>", lambda _: self._draw(self.pressed_bg))
        self.bind("<ButtonRelease-1>", self._on_release)

    def _draw(self, bg_col: str) -> None:
        """Desenha a forma arredondada e o texto centralizado."""
        self.delete("all")
        w = int(self.cget("width"))
        h = int(self.cget("height"))
        r = self.radius

        pts = [
            r, 2,
            w - r, 2,
            w - 2, 2,
            w - 2, r,
            w - 2, h - r,
            w - 2, h - 2,
            w - r, h - 2,
            r, h - 2,
            2, h - 2,
            2, h - r,
            2, r,
            2, 2,
        ]
        self.btn_rect = self.create_polygon(
            pts,
            smooth=True,
            fill=bg_col,
            outline=self.border_color,
            width=1,
        )
        self.btn_text = self.create_text(
            w / 2,
            h / 2,
            text=self.text,
            fill=self.fg_color,
            font=self.font,
        )

    def _on_release(self, event: tk.Event) -> None:
        """Executa o comando associado ao soltar o clique."""
        self._draw(self.hover_bg)
        if self.command:
            self.command()

    def config(self, **kwargs) -> None:
        """Permite atualizar o texto do botão mantendo compatibilidade com tk.Button."""
        if "text" in kwargs:
            self.text = kwargs["text"]
            if self.btn_text:
                self.itemconfig(self.btn_text, text=self.text)
