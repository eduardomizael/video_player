"""Testes para verificações auxiliares do app.py."""

import tkinter as tk
from unittest.mock import Mock

from app import AboutDialog, check_vlc_installed, replace_editor, reveal_in_explorer


def test_check_vlc_installed_returns_bool() -> None:
    """Testa se a função check_vlc_installed retorna um valor booleano sem exceção."""
    result = check_vlc_installed()
    assert isinstance(result, bool)


def test_reveal_in_explorer_nonexistent_file() -> None:
    """Testa se reveal_in_explorer lida com arquivo inexistente sem lançar exceção."""
    reveal_in_explorer("non_existent_file.mp4")


def test_replace_editor_libera_anterior_antes_de_criar_novo() -> None:
    """Garante que o VLC anterior não coexistirá com o novo editor."""

    events: list[str] = []
    root = Mock()
    previous = Mock()
    previous.destroy.side_effect = lambda: events.append("destroy")
    root.update_idletasks.side_effect = lambda: events.append("flush")
    created = Mock()

    def factory(received_root: tk.Tk, path: str, config: dict) -> tk.Widget:
        assert received_root is root
        assert path == "outro.mp4"
        assert config == {"volume": 80}
        events.append("create")
        return created

    result = replace_editor(root, previous, "outro.mp4", {"volume": 80}, factory)

    assert result is created
    assert events == ["destroy", "flush", "create"]


def test_about_dialog_creation(tk_root: tk.Tk) -> None:
    """Testa se a janela modal AboutDialog pode ser criada e destruída sem erros."""
    dialog = AboutDialog(tk_root)
    assert dialog.winfo_exists()
    dialog.destroy()
