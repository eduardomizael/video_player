"""Testes unitários para os componentes da interface gráfica (pacote gui)."""

import tkinter as tk
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from gui import ChapterEditor, SettingsWindow
from gui.chapter_panel import ChapterPanel
from gui.player_widget import PlayerWidget
from gui.settings_dialog import SettingsWindow as DirectSettingsWindow


def test_gui_package_exports() -> None:
    """Valida se o pacote gui expõe ChapterEditor e SettingsWindow corretamente."""
    assert ChapterEditor is not None
    assert SettingsWindow is not None
    assert SettingsWindow is DirectSettingsWindow


def test_settings_window_salva_valores_validos(monkeypatch: pytest.MonkeyPatch, tk_root: tk.Tk) -> None:
    """Testa a instanciação e o salvamento de valores válidos."""
    saved = False

    def on_save() -> None:
        nonlocal saved
        saved = True

    config = {"update_ms": 500, "small_jump": 5, "large_jump": 20}
    monkeypatch.setattr("gui.settings_dialog.save_config", Mock())
    win = SettingsWindow(tk_root, config, on_save)

    win.update_var.set("1000")
    win.save()

    assert saved is True
    assert config["update_ms"] == 1000


def test_settings_window_mantem_aberta_com_valor_invalido(monkeypatch: pytest.MonkeyPatch, tk_root: tk.Tk) -> None:
    """Impede o salvamento quando os limites numéricos não são respeitados."""

    config = {"update_ms": 500, "small_jump": 5, "large_jump": 20}
    on_save = Mock()
    showerror = Mock()
    monkeypatch.setattr("gui.settings_dialog.messagebox.showerror", showerror)
    monkeypatch.setattr("gui.settings_dialog.save_config", Mock())
    window = SettingsWindow(tk_root, config, on_save)
    window.update_var.set("0")

    window.save()

    on_save.assert_not_called()
    showerror.assert_called_once()
    assert window.winfo_exists()
    window.destroy()


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
    editor.app_config = {
        "keys": {
            "play_pause": "",
            "back_small": "",
            "fwd_small": "",
            "back_large": "",
            "fwd_large": "",
        }
    }
    editor.bound_shortcuts = []
    editor.player_widget = Mock(small_jump=5, large_jump=20)
    root = Mock()
    root.bind.side_effect = ["id1", "id2", "id3", "id4", "id5"]
    editor.winfo_toplevel = Mock(return_value=root)

    editor._bind_keys()

    sequences = [call.args[0] for call in root.bind.call_args_list]
    assert sequences == ["<space>", "<Left>", "<Right>", "<Shift-Left>", "<Shift-Right>"]


def test_reconfigurar_atalhos_remove_bindings_anteriores() -> None:
    """Garante que uma tecla antiga não continue ativa após a reconfiguração."""

    editor = object.__new__(ChapterEditor)
    editor.app_config = {"keys": {"play_pause": "<space>"}}
    editor.bound_shortcuts = [("<space>", "old_id")]
    editor.player_widget = Mock(small_jump=5, large_jump=20)
    root = Mock()
    root.bind.side_effect = ["id1", "id2", "id3", "id4", "id5"]
    editor.winfo_toplevel = Mock(return_value=root)

    editor._bind_keys()

    root.unbind.assert_called_once_with("<space>", "old_id")


def test_tempo_atual_do_player_nunca_e_negativo() -> None:
    """Normaliza o valor -1 retornado pelo VLC antes da mídia ficar pronta."""

    player_widget = object.__new__(PlayerWidget)
    player_widget.player = Mock()
    player_widget.player.get_time.return_value = -1

    assert player_widget.get_current_time_seconds() == 0
    assert player_widget.get_current_time_ms() == 0


def test_adicionar_subcapitulos_em_varios_niveis_expande_ancestrais() -> None:
    """Cria filhos diretos em qualquer nível e amplia todos os pais necessários."""

    root_chapter = {"title": "Pai", "start": 0, "end": 10, "subs": []}
    panel = object.__new__(ChapterPanel)
    panel.chaps = [root_chapter]
    panel.item_map = {"root": root_chapter}
    panel.tree = Mock()
    panel.tree.selection.return_value = ("root",)
    panel.tree.parent.side_effect = lambda item: {"root": "", "child": "root"}.get(item, "")
    panel.get_current_time = Mock(return_value=20)
    panel.refresh_chap_tree = Mock()
    panel.on_save = Mock()

    panel.add_subchapter()

    child = root_chapter["subs"][0]
    assert child["start"] == 20
    assert child["end"] == 30
    assert root_chapter["end"] == 30

    panel.item_map["child"] = child
    panel.tree.selection.return_value = ("child",)
    panel.get_current_time.return_value = 35
    panel.add_subchapter()

    grandchild = child["subs"][0]
    assert grandchild["start"] == 35
    assert grandchild["end"] == 45
    assert child["end"] == 45
    assert root_chapter["end"] == 45


def test_adicionar_capitulo_cria_irmao_do_selecionado() -> None:
    """Mantém o novo capítulo no mesmo nível hierárquico do item selecionado."""

    first_child = {"title": "Sub 1", "start": 5, "end": 15, "subs": []}
    root_chapter = {"title": "Pai", "start": 0, "end": 20, "subs": [first_child]}
    panel = object.__new__(ChapterPanel)
    panel.chaps = [root_chapter]
    panel.item_map = {"root": root_chapter, "child": first_child}
    panel.tree = Mock()
    panel.tree.selection.return_value = ("child",)
    panel.tree.parent.side_effect = lambda item: "root" if item == "child" else ""
    panel.get_current_time = Mock(return_value=18)
    panel.refresh_chap_tree = Mock()
    panel.on_save = Mock()

    panel.add_chapter()

    assert len(root_chapter["subs"]) == 2
    assert root_chapter["subs"][1]["start"] == 18
    assert root_chapter["end"] == 28
