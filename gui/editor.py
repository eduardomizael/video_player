"""Widget principal do editor integrando player, painéis de capítulos/casting e atalhos."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from logic import ChapterManager

from gui.cast_panel import CastPanel
from gui.chapter_panel import ChapterPanel
from gui.player_widget import PlayerWidget


class ChapterEditor(tk.Frame):
    """Widget Tkinter principal que sintetiza player VLC, capítulos e casting."""

    def __init__(self, master: tk.Tk, video_path: str, config: dict) -> None:
        """Inicializa o editor para o vídeo informado."""

        super().__init__(master)
        self.pack(fill="both", expand=True)

        self.config = config
        self.update_ms = config.get("update_ms", 500)

        # Gerenciador de persistência
        self.manager = ChapterManager(video_path)
        data = self.manager.load()
        self.chaps: list[dict] = data.get("chapters", [])
        self.casting: list[str] = data.get("casting", [])

        main_container = tk.Frame(self)
        main_container.pack(fill="both", expand=True)

        # Player Widget (esquerda)
        self.player_widget = PlayerWidget(
            main_container,
            video_path=video_path,
            config=config,
            on_drag_start=self._stop_update_loop,
            on_drag_end=self._start_update_loop,
        )
        self.player_widget.pack(side="left", fill="both", expand=True)

        # Painel lateral com abas (direita)
        side_panel = tk.Frame(main_container, width=260, relief="groove", bd=1)
        side_panel.pack(side="right", fill="y")

        self.notebook = ttk.Notebook(side_panel)
        self.notebook.pack(fill="both", expand=True)

        # Aba de Capítulos
        chap_tab = tk.Frame(self.notebook)
        self.notebook.add(chap_tab, text="Capítulos")
        self.chap_panel = ChapterPanel(
            chap_tab,
            chaps=self.chaps,
            on_save=self.save_data,
            get_current_time=self.player_widget.get_current_time_seconds,
            on_jump_to_sec=self.player_widget.set_time_seconds,
        )
        self.chap_panel.pack(fill="both", expand=True)

        # Aba de Casting
        cast_tab = tk.Frame(self.notebook)
        self.notebook.add(cast_tab, text="Casting")
        self.cast_panel = CastPanel(
            cast_tab,
            casting=self.casting,
            on_save=self.save_data,
        )
        self.cast_panel.pack(fill="both", expand=True)

        self.updater = None
        self._start_update_loop()
        self._bind_keys()

    def destroy(self) -> None:
        """Interrompe a reprodução e libera recursos do player."""
        self._stop_update_loop()
        if hasattr(self, "player_widget"):
            self.player_widget.destroy()
        super().destroy()

    def save_data(self) -> None:
        """Persiste os capítulos e casting atuais no arquivo JSON."""
        self.manager.save(self.chaps, self.casting)

    def update_config(self, config: dict) -> None:
        """Aplica as configurações atualizadas aos submódulos."""
        self.config = config
        self.update_ms = config.get("update_ms", self.update_ms)
        self.player_widget.update_config(config)
        self._bind_keys()

    def _start_update_loop(self) -> None:
        """Agenda a atualização periódica da interface."""
        self.updater = self.after(self.update_ms, self._update_ui)

    def _stop_update_loop(self) -> None:
        """Cancela o loop de atualização se estiver ativo."""
        if self.updater:
            self.after_cancel(self.updater)
            self.updater = None

    def _update_ui(self) -> None:
        """Passo de atualização contínua da interface."""
        self.player_widget.update_ui_loop_step()
        self._start_update_loop()

    def _bind_keys(self) -> None:
        """Configura os atalhos de teclado globais."""
        keys = self.config.get("keys", {})
        root = self.winfo_toplevel()

        def safe_action(action: callable) -> callable:
            def handler(_: tk.Event) -> None:
                focus_w = root.focus_get()
                if isinstance(focus_w, (tk.Entry, ttk.Entry)):
                    return
                action()

            return handler

        p_w = self.player_widget
        root.bind(keys.get("play_pause", "<space>"), safe_action(p_w.toggle_play_pause))
        root.bind(keys.get("back_small", "<Left>"), safe_action(lambda: p_w.jump(-p_w.small_jump)))
        root.bind(keys.get("fwd_small", "<Right>"), safe_action(lambda: p_w.jump(p_w.small_jump)))
        root.bind(keys.get("back_large", "<Shift-Left>"), safe_action(lambda: p_w.jump(-p_w.large_jump)))
        root.bind(keys.get("fwd_large", "<Shift-Right>"), safe_action(lambda: p_w.jump(p_w.large_jump)))
