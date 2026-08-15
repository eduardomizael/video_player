"""Testes unitários para os componentes da interface gráfica (pacote gui)."""

import tkinter as tk
from types import SimpleNamespace
from unittest.mock import Mock

from gui import ChapterEditor, SettingsWindow
from gui.player_widget import PlayerWidget
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


def test_scroll_progresso_aplica_salto_longo_reverso() -> None:
    """Valida que a roda sobre a barra usa o salto longo no sentido correto."""
    player_widget = object.__new__(PlayerWidget)
    player_widget.large_jump = 20
    player_widget.jump = Mock()

    result = player_widget._on_progress_scroll(SimpleNamespace(num=5, delta=0))

    player_widget.jump.assert_called_once_with(-20)
    assert result == "break"


def test_atalhos_vazios_usam_valores_padrao() -> None:
    """Valida que configurações vazias não geram bindings inválidos no Tkinter."""
    editor = object.__new__(ChapterEditor)
    editor.config = {
        "keys": {
            "play_pause": "",
            "back_small": "",
            "fwd_small": "",
            "back_large": "",
            "fwd_large": "",
        }
    }
    editor.player_widget = Mock(small_jump=5, large_jump=20)
    root = Mock()
    editor.winfo_toplevel = Mock(return_value=root)

    editor._bind_keys()

    sequences = [call.args[0] for call in root.bind.call_args_list]
    assert sequences == ["<space>", "<Left>", "<Right>", "<Shift-Left>", "<Shift-Right>"]
