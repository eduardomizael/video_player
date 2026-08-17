"""Diálogo de confirmação centralizado sobre a janela principal."""

from __future__ import annotations

import tkinter as tk


def ask_confirmation(parent: tk.Widget, title: str, message: str) -> bool:
    """Exibe uma confirmação modal posicionada no centro da janela informada."""

    owner = parent.winfo_toplevel()
    dialog = tk.Toplevel(owner)
    dialog.title(title)
    dialog.transient(owner)
    dialog.resizable(False, False)
    dialog.result = False

    content = tk.Frame(dialog, padx=20, pady=16)
    content.pack(fill="both", expand=True)
    tk.Label(content, text=message, justify="left", wraplength=360).pack(fill="x")
    buttons = tk.Frame(content, pady=12)
    buttons.pack(fill="x")

    def confirm() -> None:
        """Confirma a operação e fecha o diálogo."""

        dialog.result = True
        dialog.destroy()

    tk.Button(buttons, text="Cancelar", command=dialog.destroy, width=10).pack(side="right")
    tk.Button(buttons, text="Confirmar", command=confirm, width=10).pack(side="right", padx=(0, 6))
    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    dialog.update_idletasks()
    x = owner.winfo_x() + (owner.winfo_width() - dialog.winfo_width()) // 2
    y = owner.winfo_y() + (owner.winfo_height() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
    dialog.grab_set()
    dialog.wait_window()
    return dialog.result
