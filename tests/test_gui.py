"""Testes unitários para os componentes da interface gráfica (pacote gui)."""

import tkinter as tk

from gui import ChapterEditor, SettingsWindow
from gui.settings_dialog import SettingsWindow as DirectSettingsWindow


def test_gui_package_exports() -> None:
    """Valida se o pacote gui expõe ChapterEditor e SettingsWindow corretamente."""
    assert ChapterEditor is not None
    assert SettingsWindow is not None
    assert SettingsWindow is DirectSettingsWindow


def test_settings_window_instantiation() -> None:
    """Testa a instanciação e o salvamento com fallback de valores na SettingsWindow."""
    root = tk.Tk()
    root.withdraw()

    saved = False

    def on_save() -> None:
        nonlocal saved
        saved = True

    config = {"update_ms": 500, "small_jump": 5, "large_jump": 20}
    win = SettingsWindow(root, config, on_save)

    # Simula entrada com valor inválido
    win.update_var.set("invalid")
    win.save()

    assert saved is True
    assert config["update_ms"] == 500  # Fallback seguro ativado

    root.destroy()
