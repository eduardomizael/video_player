"""Widget principal do editor integrando player, painéis de capítulos, legendas, casting e atalhos."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from gui.cast_panel import CastPanel
from gui.chapter_panel import ChapterPanel
from gui.player_widget import PlayerWidget
from gui.subtitle_panel import SubtitlePanel
from logic import ChapterManager, SubtitleManager


class ChapterEditor(tk.Frame):
    """Widget Tkinter principal que sintetiza player VLC, capítulos, legendas (.srt) e casting."""

    def __init__(self, master: tk.Tk, video_path: str, config: dict) -> None:
        """Inicializa o editor para o vídeo informado."""

        self.manager = ChapterManager(video_path)
        self.sub_manager = SubtitleManager(video_path)
        data = self.manager.load()
        subtitles = self.sub_manager.load()

        super().__init__(master)
        self.pack(fill="both", expand=True)

        self.app_config = config
        self.update_ms = config.get("update_ms", 500)
        self.chaps: list[dict] = data["chapters"]
        self.casting: list[str] = data["casting"]
        self.subtitles: list[dict] = subtitles
        self.bound_shortcuts: list[tuple[str, str]] = []

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
        side_panel = tk.Frame(main_container, width=280, relief="flat", bd=0)
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

        # Aba de Legendas
        sub_tab = tk.Frame(self.notebook)
        self.notebook.add(sub_tab, text="Legendas")
        self.sub_panel = SubtitlePanel(
            sub_tab,
            subtitles=self.subtitles,
            on_save=self.save_subtitles,
            get_current_time_ms=self.player_widget.get_current_time_ms,
            on_jump_to_ms=self.player_widget.set_time_ms,
        )
        self.sub_panel.pack(fill="both", expand=True)

        # Aba de Casting
        cast_tab = tk.Frame(self.notebook)
        self.notebook.add(cast_tab, text="Casting")
        self.cast_panel = CastPanel(
            cast_tab,
            casting=self.casting,
            on_save=self.save_data,
        )
        self.cast_panel.pack(fill="both", expand=True)

        self.updater: str | None = None
        self._start_update_loop()
        self._bind_keys()

        # Carrega a legenda no VLC se já existir arquivo .srt
        self.initial_subtitle_after: str | None = self.after(500, self._load_initial_subtitles)

    def _load_initial_subtitles(self) -> None:
        """Carrega a legenda no player VLC ao iniciar."""
        self.initial_subtitle_after = None
        if self.subtitles:
            try:
                self.player_widget.set_subtitle_file(self.sub_manager.srt_path)
            except RuntimeError as exc:
                messagebox.showwarning("Legenda não carregada", str(exc))

    def destroy(self) -> None:
        """Interrompe a reprodução e libera recursos do player."""
        self._stop_update_loop()
        self._unbind_keys()
        if self.initial_subtitle_after:
            self.after_cancel(self.initial_subtitle_after)
            self.initial_subtitle_after = None
        if hasattr(self, "player_widget"):
            self.player_widget.destroy()
        super().destroy()

    def save_data(self) -> None:
        """Persiste os capítulos e casting atuais no arquivo JSON."""
        try:
            self.manager.save(self.chaps, self.casting)
        except (OSError, TypeError, ValueError) as exc:
            messagebox.showerror("Dados não salvos", str(exc))

    def save_subtitles(self) -> None:
        """Persiste as legendas atuais no arquivo .srt e atualiza no VLC."""
        try:
            self.sub_manager.save(self.subtitles)
        except (OSError, TypeError, ValueError) as exc:
            messagebox.showerror("Legendas não salvas", str(exc))
            return
        try:
            self.player_widget.set_subtitle_file(self.sub_manager.srt_path)
        except RuntimeError as exc:
            messagebox.showwarning("Legenda salva, mas não recarregada", str(exc))

    def update_config(self, config: dict) -> None:
        """Aplica as configurações atualizadas aos submódulos."""
        self.app_config = config
        self.update_ms = config.get("update_ms", self.update_ms)
        self.player_widget.update_config(config)
        self._bind_keys()

    def _start_update_loop(self) -> None:
        """Agenda a atualização periódica da interface."""
        if self.updater is not None:
            return
        self.updater = self.after(self.update_ms, self._update_ui)

    def _stop_update_loop(self) -> None:
        """Cancela o loop de atualização se estiver ativo."""
        if self.updater:
            self.after_cancel(self.updater)
            self.updater = None

    def _update_ui(self) -> None:
        """Passo de atualização contínua da interface."""
        self.updater = None
        self.player_widget.update_ui_loop_step()
        self._start_update_loop()

    def _unbind_keys(self) -> None:
        """Remove apenas os atalhos globais registrados por este editor."""

        root = self.winfo_toplevel()
        for sequence, function_id in self.bound_shortcuts:
            root.unbind(sequence, function_id)
        self.bound_shortcuts.clear()

    def _bind_keys(self) -> None:
        """Configura os atalhos de teclado globais."""
        self._unbind_keys()
        keys = self.app_config.get("keys", {})
        root = self.winfo_toplevel()

        def safe_action(action: Callable[[], None]) -> Callable[[tk.Event], None]:
            def handler(_: tk.Event) -> None:
                focus_w = root.focus_get()
                if isinstance(focus_w, (tk.Entry, ttk.Entry)):
                    return
                action()

            return handler

        p_w = self.player_widget
        bindings = [
            (keys.get("play_pause") or "<space>", safe_action(p_w.toggle_play_pause)),
            (keys.get("back_small") or "<Left>", safe_action(lambda: p_w.jump(-p_w.small_jump))),
            (keys.get("fwd_small") or "<Right>", safe_action(lambda: p_w.jump(p_w.small_jump))),
            (keys.get("back_large") or "<Shift-Left>", safe_action(lambda: p_w.jump(-p_w.large_jump))),
            (keys.get("fwd_large") or "<Shift-Right>", safe_action(lambda: p_w.jump(p_w.large_jump))),
        ]
        for sequence, handler in bindings:
            function_id = root.bind(sequence, handler)
            if function_id:
                self.bound_shortcuts.append((sequence, function_id))
