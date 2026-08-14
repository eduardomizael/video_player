"""Diálogo de configurações do aplicativo."""

from __future__ import annotations

import sys
import tkinter as tk

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
        if sys.platform.startswith("win"):
            if event.state & 0x20000:
                mods.append("Alt")
        else:
            if event.state & 0x8:
                mods.append("Alt")
        var.set("<" + "-".join(mods + [event.keysym]) + ">")
        return "break"

    def save(self) -> None:
        """Salva a configuração e avisa o chamador."""
        try:
            self.config["update_ms"] = int(self.update_var.get())
        except ValueError:
            self.config["update_ms"] = 500

        try:
            self.config["small_jump"] = int(self.small_var.get())
        except ValueError:
            self.config["small_jump"] = 5

        try:
            self.config["large_jump"] = int(self.large_var.get())
        except ValueError:
            self.config["large_jump"] = 20

        keys = self.config.setdefault("keys", {})
        for k, var in self.key_vars.items():
            val = var.get().strip() or keys.get(k, "")
            keys[k] = val
        save_config(self.config)
        self.on_save()
        self.destroy()
