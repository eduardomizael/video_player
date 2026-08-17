"""Testes unitários para os componentes da interface gráfica (pacote gui)."""

import tkinter as tk
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from gui import ChapterEditor, SettingsWindow
from gui.add_item_dialog import AddItemDialog, FormField
from gui.chapter_panel import ChapterPanel
from gui.image_association_dialog import ImageAssociationDialog
from gui.metadata_panel import MetadataPanel
from gui.player_widget import PlayerWidget
from gui.settings_dialog import SettingsWindow as DirectSettingsWindow


def _confirm_add_dialog(_, __, fields, on_submit):
    """Confirma um formulário de inclusão com seus valores pré-preenchidos."""

    assert on_submit({field.name: field.value for field in fields}) is None


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


def test_cancelar_incorporacao_pendente_do_player() -> None:
    """Evita que um callback atrasado tente usar um canvas já destruído."""

    player_widget = object.__new__(PlayerWidget)
    player_widget.embed_after = "callback-1"
    player_widget.after_cancel = Mock()

    player_widget._cancel_embed_schedule()

    player_widget.after_cancel.assert_called_once_with("callback-1")
    assert player_widget.embed_after is None


def test_adicionar_subcapitulos_em_varios_niveis_expande_ancestrais(monkeypatch: pytest.MonkeyPatch) -> None:
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
    monkeypatch.setattr("gui.chapter_panel.AddItemDialog", _confirm_add_dialog)

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


def test_adicionar_capitulo_cria_irmao_do_selecionado(monkeypatch: pytest.MonkeyPatch) -> None:
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
    monkeypatch.setattr("gui.chapter_panel.AddItemDialog", _confirm_add_dialog)

    panel.add_chapter()

    assert len(root_chapter["subs"]) == 2
    assert root_chapter["subs"][1]["start"] == 18
    assert root_chapter["end"] == 28


def test_adicionar_filho_transfere_valor_do_metadado(monkeypatch: pytest.MonkeyPatch) -> None:
    """Move o valor do pai para o novo filho, que permanece uma folha."""

    node = {"key": "autor", "value": "Eduardo", "children": []}
    panel = object.__new__(MetadataPanel)
    panel.metadata = [node]
    panel.item_map = {"root": node}
    panel.tree = Mock()
    panel.tree.selection.return_value = ("root",)
    panel.refresh_tree = Mock()
    panel.on_save = Mock()
    monkeypatch.setattr("gui.metadata_panel.AddItemDialog", _confirm_add_dialog)

    panel.add_child()

    assert node["value"] == ""
    assert node["children"] == [{"key": "chave_1", "value": "Eduardo", "children": []}]
    panel.refresh_tree.assert_called_once_with(node["children"][0])
    panel.on_save.assert_called_once()


def test_dialogo_de_imagens_salva_apenas_as_marcadas(tk_root: tk.Tk) -> None:
    """Substitui os vínculos do registro pelas caixas confirmadas no diálogo."""

    first = {"id": "imagem-1"}
    second = {"id": "imagem-2"}
    dialog = object.__new__(ImageAssociationDialog)
    dialog.images = [first, second]
    dialog.record = {"images": ["imagem-1"]}
    dialog.selected = {
        "imagem-1": tk.BooleanVar(tk_root, value=False),
        "imagem-2": tk.BooleanVar(tk_root, value=True),
    }
    dialog.on_save = Mock()
    dialog.destroy = Mock()

    dialog.save()

    assert dialog.record["images"] == ["imagem-2"]
    dialog.on_save.assert_called_once()
    dialog.destroy.assert_called_once()


def test_formulario_de_inclusao_foca_e_seleciona_primeiro_campo(tk_root: tk.Tk) -> None:
    """Permite substituir imediatamente o valor sugerido ao abrir o formulário."""

    tk_root.deiconify()
    try:
        dialog = AddItemDialog(tk_root, "Teste", [FormField("name", "Nome", "Valor sugerido")], lambda _: None)
        tk_root.update()

        field = dialog.widgets["name"]
        assert dialog.focus_get() is field
        assert field.selection_present()
        dialog.destroy()
    finally:
        tk_root.withdraw()
