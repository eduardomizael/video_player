"""Componente visual responsável pela reprodução de vídeo e controles com VLC."""

from __future__ import annotations

import os
import tkinter as tk
import vlc

from config import save_config
from logic import fmt_sec


class PlayerWidget(tk.Frame):
    """Widget do player de vídeo contendo tela VLC e barra de controles."""

    def __init__(
        self,
        master: tk.Widget,
        video_path: str,
        config: dict,
        on_drag_start: callable,
        on_drag_end: callable,
    ) -> None:
        """Inicializa o player VLC e monta a interface de controle."""

        super().__init__(master)
        self.config = config
        self.small_jump = config.get("small_jump", 5)
        self.large_jump = config.get("large_jump", 20)
        self.on_drag_start_cb = on_drag_start
        self.on_drag_end_cb = on_drag_end

        # Instância e media player do VLC
        self.vlc = vlc.Instance()
        self.player = self.vlc.media_player_new()
        self.player.set_media(self.vlc.media_new(video_path))
        self.player.audio_set_volume(config.get("volume", 100))

        # Canvas do vídeo
        self.canvas = tk.Canvas(self, bg="black")
        self.canvas.pack(fill="both", expand=True)

        # Barra de controles inferior
        controls = tk.Frame(self)
        controls.pack(fill="x")

        top_bar = tk.Frame(controls)
        top_bar.pack(fill="x")
        bottom_bar = tk.Frame(controls)
        bottom_bar.pack(fill="x")

        self.cur_time_lbl = tk.Label(top_bar, text="00:00")
        self.cur_time_lbl.pack(side="left")
        self.total_time_lbl = tk.Label(top_bar, text="00:00")
        self.total_time_lbl.pack(side="right")
        self.scale = tk.Scale(
            top_bar,
            from_=0,
            to=1000,
            showvalue=0,
            orient="horizontal",
            length=400,
            command=lambda v: self.seek(int(v)),
        )
        self.scale.pack(side="left", fill="x", expand=True, padx=5)

        def create_button(parent: tk.Widget, text: str, command: callable, **kwargs) -> tk.Button:
            btn = tk.Button(parent, text=text, command=command, **kwargs)
            btn.pack(side="left")
            return btn

        self.play_pause_btn = create_button(bottom_bar, "▶", self.toggle_play_pause, font=("Helvetica", 12, "bold"), width=4)
        self.play_pause_btn.pack(side="left", padx=5)

        self.back_large_btn = create_button(bottom_bar, f"«{self.large_jump}s", lambda: self.jump(-self.large_jump))
        self.back_small_btn = create_button(bottom_bar, f"‹{self.small_jump}s", lambda: self.jump(-self.small_jump))

        self.separator_lbl = tk.Label(bottom_bar, text=" | ")
        self.separator_lbl.pack(side="left")

        self.fwd_small_btn = create_button(bottom_bar, f"{self.small_jump}s›", lambda: self.jump(self.small_jump))
        self.fwd_large_btn = create_button(bottom_bar, f"{self.large_jump}s»", lambda: self.jump(self.large_jump))

        # Controle de Volume
        vol_frame = tk.Frame(bottom_bar)
        vol_frame.pack(side="right")
        self.volume_scale = tk.Scale(
            vol_frame,
            from_=0,
            to=100,
            orient="horizontal",
            length=100,
            showvalue=0,
            command=self._change_volume,
        )
        self.volume_scale.set(config.get("volume", 100))
        self.volume_scale.pack(side="left", padx=5)
        self.volume_lbl = tk.Label(vol_frame, text=f"{self.volume_scale.get()}%")
        self.volume_lbl.pack(side="left")

        self.scale.bind("<ButtonPress-1>", self._drag_start)
        self.scale.bind("<ButtonRelease-1>", self._drag_end)

        self.after(100, self._embed_and_play)

    def destroy(self) -> None:
        """Libera recursos do player e instância VLC."""
        self.player.stop()
        self.player.release()
        self.vlc.release()
        super().destroy()

    def update_config(self, config: dict) -> None:
        """Atualiza tempos de pulo e volume a partir das configurações."""
        self.config = config
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
        """Conecta o janela do VLC ao canvas do Tkinter."""
        wid = self.canvas.winfo_id()
        if os.name == "nt":
            self.player.set_hwnd(wid)
        else:
            self.player.set_xwindow(wid)

    def _embed_and_play(self) -> None:
        """Conecta a janela do VLC e inicia a reprodução."""
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
        cur = self.player.get_time()
        self.player.set_time(max(0, cur + secs * 1000))

    def set_time_seconds(self, sec: int) -> None:
        """Move o vídeo para um segundo específico."""
        self.player.set_time(sec * 1000)

    def set_time_ms(self, ms: int) -> None:
        """Move o vídeo para um tempo específico em milissegundos."""
        self.player.set_time(ms)

    def get_current_time_seconds(self) -> int:
        """Retorna o tempo atual em segundos."""
        return self.player.get_time() // 1000

    def get_current_time_ms(self) -> int:
        """Retorna o tempo atual em milissegundos."""
        return self.player.get_time()

    def set_subtitle_file(self, srt_path: str) -> None:
        """Carrega e força o recarregamento dinâmico da legenda .srt no VLC em tempo real."""
        if os.path.exists(srt_path):
            abs_path = os.path.abspath(srt_path)
            self.player.video_set_subtitle_file(abs_path)
            try:
                import pathlib
                uri = pathlib.Path(abs_path).as_uri()
                self.player.add_slave(vlc.MediaSlaveType.subtitle, uri, True)
            except Exception:
                pass

    def _change_volume(self, val: str) -> None:
        """Ajusta o volume do player e salva na configuração."""
        vol = int(float(val))
        self.player.audio_set_volume(vol)
        self.config["volume"] = vol
        self.volume_lbl.config(text=f"{vol}%")
        save_config(self.config)

    def update_ui_loop_step(self) -> None:
        """Atualiza a posição do slider e os rótulos de tempo."""
        dur = self.player.get_length()
        pos = self.player.get_time()
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
