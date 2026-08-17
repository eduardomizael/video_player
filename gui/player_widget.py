"""Componente visual responsável pela reprodução de vídeo e controles com VLC."""

from __future__ import annotations

import os
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, ttk

import vlc

from config import save_config
from gui.rounded_button import RoundedButton
from logic import fmt_sec


class PlayerWidget(tk.Frame):
    """Widget do player de vídeo contendo tela VLC e barra de controles."""

    def __init__(
        self,
        master: tk.Widget,
        video_path: str,
        config: dict,
        on_drag_start: Callable[[], None],
        on_drag_end: Callable[[], None],
    ) -> None:
        """Inicializa o player VLC e monta a interface de controle."""

        super().__init__(master)
        self.app_config = config
        self.small_jump = config.get("small_jump", 5)
        self.large_jump = config.get("large_jump", 20)
        self.on_drag_start_cb = on_drag_start
        self.on_drag_end_cb = on_drag_end

        # Instância e media player do VLC
        self.vlc = vlc.Instance()
        self.player = self.vlc.media_player_new()
        self.player.set_media(self.vlc.media_new(video_path))
        self.player.audio_set_volume(config.get("volume", 100))

        # Canvas do vídeo com recuo nas bordas
        self.canvas = tk.Canvas(self, bg="black")
        self.canvas.pack(fill="both", expand=True, padx=6, pady=(4, 2))

        # Barra de controles estilo VLC Media Player
        vlc_bg = "#e8e8e8"

        controls = tk.Frame(self, bg=vlc_bg, bd=0, relief="flat")
        controls.pack(fill="x", side="bottom", padx=6, pady=(0, 4))

        top_bar = tk.Frame(controls, bg=vlc_bg)
        top_bar.pack(fill="x", padx=8, pady=(4, 2))

        bottom_bar = tk.Frame(controls, bg=vlc_bg)
        bottom_bar.pack(fill="x", padx=8, pady=(2, 6))

        self.cur_time_lbl = tk.Label(top_bar, text="00:00", bg=vlc_bg, fg="#111111", font=("Segoe UI", 9, "bold"))
        self.cur_time_lbl.pack(side="left", padx=(0, 4))

        self.total_time_lbl = tk.Label(top_bar, text="00:00", bg=vlc_bg, fg="#111111", font=("Segoe UI", 9, "bold"))
        self.total_time_lbl.pack(side="right", padx=(4, 0))

        self.scale = tk.Scale(
            top_bar,
            from_=0,
            to=1000,
            showvalue=0,
            orient="horizontal",
            bg=vlc_bg,
            troughcolor="#d0d0d0",
            activebackground="#ffffff",
            bd=0,
            highlightthickness=0,
            sliderlength=14,
            command=lambda v: self.seek(int(v)),
        )
        self.scale.pack(side="left", fill="x", expand=True)

        # Estilo dos botões arredondados no estilo VLC
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure(
            "VLC.TButton",
            font=("Segoe UI", 10, "bold"),
            background="#ffffff",
            foreground="#222222",
            bordercolor="#b5b5b5",
            lightcolor="#ffffff",
            darkcolor="#dcdcdc",
            borderwidth=1,
            focuscolor="none",
            padding=(6, 3),
        )
        style.map(
            "VLC.TButton",
            background=[("active", "#e0e0e0"), ("pressed", "#cecece")],
            foreground=[("active", "#000000")],
        )

        style.configure("TNotebook", borderwidth=0, highlightthickness=0)
        style.configure("Treeview", borderwidth=0, relief="flat")

        def create_vlc_btn(
            parent: tk.Widget, text: str, command: Callable[[], None], width: int = 45, height: int = 30
        ) -> RoundedButton:
            btn = RoundedButton(
                parent,
                text=text,
                command=command,
                width=width,
                height=height,
                radius=10,
                bg_color="#ffffff",
                hover_bg="#e4e4e4",
                pressed_bg="#cecece",
                border_color="#b8b8b8",
                font=("Segoe UI", 10, "bold"),
            )
            btn.pack(side="left", padx=3)
            return btn

        self.play_pause_btn = create_vlc_btn(bottom_bar, "▶", self.toggle_play_pause, width=42, height=30)
        self.stop_btn = create_vlc_btn(bottom_bar, "⏹", self.stop_video, width=36, height=30)

        tk.Label(bottom_bar, text=" ", bg=vlc_bg, width=1).pack(side="left")

        self.back_large_btn = create_vlc_btn(
            bottom_bar, f"«{self.large_jump}s", lambda: self.jump(-self.large_jump), width=56, height=30
        )
        self.back_small_btn = create_vlc_btn(
            bottom_bar, f"‹{self.small_jump}s", lambda: self.jump(-self.small_jump), width=52, height=30
        )
        self.fwd_small_btn = create_vlc_btn(
            bottom_bar, f"{self.small_jump}s›", lambda: self.jump(self.small_jump), width=52, height=30
        )
        self.fwd_large_btn = create_vlc_btn(
            bottom_bar, f"{self.large_jump}s»", lambda: self.jump(self.large_jump), width=56, height=30
        )

        tk.Label(bottom_bar, text=" ", bg=vlc_bg, width=1).pack(side="left")
        self.fullscreen_btn = create_vlc_btn(bottom_bar, "⛶", self.toggle_fullscreen, width=36, height=30)

        # Controle de Volume à direita
        vol_frame = tk.Frame(bottom_bar, bg=vlc_bg)
        vol_frame.pack(side="right", padx=(0, 4))

        self.volume_icon_lbl = tk.Label(vol_frame, text="🔊", bg=vlc_bg, font=("Segoe UI", 10))
        self.volume_icon_lbl.pack(side="left", padx=(0, 2))

        self.volume_scale = tk.Scale(
            vol_frame,
            from_=0,
            to=100,
            orient="horizontal",
            length=90,
            showvalue=0,
            bg=vlc_bg,
            troughcolor="#d0d0d0",
            activebackground="#ffffff",
            bd=0,
            highlightthickness=0,
            sliderlength=12,
            command=self._change_volume,
        )
        self.volume_scale.set(config.get("volume", 100))
        self.volume_scale.pack(side="left")
        self.volume_scale.bind("<ButtonRelease-1>", self._save_volume)
        self.volume_scale.bind("<FocusOut>", self._save_volume)

        self.volume_lbl = tk.Label(
            vol_frame, text=f"{self.volume_scale.get()}%", bg=vlc_bg, fg="#333333", font=("Segoe UI", 8, "bold")
        )
        self.volume_lbl.pack(side="left", padx=(2, 0))

        self.scale.bind("<ButtonPress-1>", self._drag_start)
        self.scale.bind("<ButtonRelease-1>", self._drag_end)
        self.scale.bind("<MouseWheel>", self._on_progress_scroll)
        self.scale.bind("<Button-4>", self._on_progress_scroll)
        self.scale.bind("<Button-5>", self._on_progress_scroll)

        self.embed_after: str | None = self.after(100, self._embed_and_play)

    def _on_progress_scroll(self, event: tk.Event) -> str:
        """Aplica saltos longos ao girar a roda sobre a barra de progresso."""
        if event.delta > 0 or getattr(event, "num", 0) == 4:
            self.jump(self.large_jump)
        elif event.delta < 0 or getattr(event, "num", 0) == 5:
            self.jump(-self.large_jump)
        return "break"

    def destroy(self) -> None:
        """Libera recursos do player e instância VLC."""
        self._cancel_embed_schedule()
        self.player.stop()
        self.player.release()
        self.vlc.release()
        super().destroy()

    def _cancel_embed_schedule(self) -> None:
        """Cancela a incorporação pendente do VLC antes de destruir o canvas."""

        if self.embed_after:
            self.after_cancel(self.embed_after)
            self.embed_after = None

    def update_config(self, config: dict) -> None:
        """Atualiza tempos de pulo e volume a partir das configurações."""
        self.app_config = config
        self.small_jump = config.get("small_jump", self.small_jump)
        self.large_jump = config.get("large_jump", self.large_jump)
        volume = config.get("volume", self.player.audio_get_volume())
        self.player.audio_set_volume(volume)
        self.volume_scale.set(volume)
        self.back_small_btn.config(text=f"‹{self.small_jump}s")
        self.back_large_btn.config(text=f"«{self.large_jump}s")
        self.fwd_small_btn.config(text=f"{self.small_jump}s›")
        self.fwd_large_btn.config(text=f"{self.large_jump}s»")

    def _embed_player(self) -> None:
        """Conecta a janela do VLC ao canvas do Tkinter."""
        wid = self.canvas.winfo_id()
        if os.name == "nt":
            self.player.set_hwnd(wid)
        else:
            self.player.set_xwindow(wid)

    def _embed_and_play(self) -> None:
        """Conecta a janela do VLC e inicia a reprodução."""
        self.embed_after = None
        self._embed_player()
        self.toggle_play_pause()

    def toggle_play_pause(self) -> None:
        """Alterna entre reproduzir e pausar o vídeo."""
        if self.player.is_playing():
            self.player.pause()
            self.play_pause_btn.config(text="▶")
        else:
            self.player.play()
            self.play_pause_btn.config(text="❚❚")

    def seek(self, scale_val: int) -> None:
        """Move o vídeo para a posição proporcional ao slider."""
        dur = self.player.get_length()
        if dur > 0:
            self.player.set_time(int(scale_val / 1000 * dur))

    def jump(self, secs: int) -> None:
        """Avança ou retrocede o vídeo em segundos."""
        current = max(0, self.player.get_time())
        self._set_bounded_time(current + secs * 1000)

    def _set_bounded_time(self, milliseconds: int) -> None:
        """Move o vídeo respeitando zero e a duração conhecida da mídia."""

        duration = self.player.get_length()
        maximum = duration if duration > 0 else milliseconds
        self.player.set_time(max(0, min(milliseconds, maximum)))

    def set_time_seconds(self, sec: int) -> None:
        """Move o vídeo para um segundo específico."""
        self._set_bounded_time(sec * 1000)

    def set_time_ms(self, ms: int) -> None:
        """Move o vídeo para um tempo específico em milissegundos."""
        self._set_bounded_time(ms)

    def get_current_time_seconds(self) -> int:
        """Retorna o tempo atual em segundos."""
        return max(0, self.player.get_time()) // 1000

    def get_current_time_ms(self) -> int:
        """Retorna o tempo atual em milissegundos."""
        return max(0, self.player.get_time())

    def set_subtitle_file(self, srt_path: str) -> None:
        """Carrega e força o recarregamento dinâmico da legenda .srt no VLC em tempo real."""
        path = Path(srt_path).resolve()
        if path.exists():
            result = self.player.add_slave(vlc.MediaSlaveType.subtitle, path.as_uri(), True)
            if result != 0:
                raise RuntimeError(f"O VLC não conseguiu carregar a legenda: {path}")

    def stop_video(self) -> None:
        """Interrompe a reprodução do vídeo e reseta a barra de tempo."""
        self.player.stop()
        self.scale.config(command="")
        self.scale.set(0)
        self.scale.config(command=lambda v: self.seek(int(v)))
        self.cur_time_lbl.config(text="00:00")
        self.play_pause_btn.config(text="▶")

    def toggle_fullscreen(self) -> None:
        """Alterna entre modo tela cheia e janela normal."""
        root = self.winfo_toplevel()
        is_fs = root.attributes("-fullscreen")
        root.attributes("-fullscreen", not is_fs)

    def _change_volume(self, val: str) -> None:
        """Ajusta o volume do player, atualiza o ícone e salva na configuração."""
        vol = int(float(val))
        self.player.audio_set_volume(vol)
        self.app_config["volume"] = vol
        self.volume_lbl.config(text=f"{vol}%")
        if hasattr(self, "volume_icon_lbl"):
            if vol == 0:
                self.volume_icon_lbl.config(text="🔇")
            elif vol < 50:
                self.volume_icon_lbl.config(text="🔉")
            else:
                self.volume_icon_lbl.config(text="🔊")

    def _save_volume(self, _: tk.Event | None = None) -> None:
        """Persiste o volume após o usuário concluir o ajuste."""

        try:
            save_config(self.app_config)
        except OSError as exc:
            messagebox.showerror("Volume não salvo", str(exc), parent=self.winfo_toplevel())

    def update_ui_loop_step(self) -> None:
        """Atualiza a posição do slider e os rótulos de tempo."""
        dur = self.player.get_length()
        pos = max(0, self.player.get_time())
        if dur > 0:
            self.scale.config(command="")
            self.scale.set(int(pos / dur * 1000))
            self.scale.config(command=lambda v: self.seek(int(v)))
            self.cur_time_lbl.config(text=fmt_sec(pos // 1000))
            self.total_time_lbl.config(text=fmt_sec(dur // 1000))

        if self.player.is_playing():
            self.play_pause_btn.config(text="❚❚")
        else:
            self.play_pause_btn.config(text="▶")

    def _drag_start(self, _: tk.Event) -> None:
        """Pausa o loop de atualização ao arrastar o slider."""
        self.on_drag_start_cb()

    def _drag_end(self, _: tk.Event) -> None:
        """Move o vídeo e retoma as atualizações ao soltar o slider."""
        val = self.scale.get()
        dur = self.player.get_length()
        if dur > 0:
            self.player.set_time(int(val / 1000 * dur))
        self.on_drag_end_cb()
