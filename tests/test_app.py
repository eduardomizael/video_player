"""Testes para verificações auxiliares do app.py."""

import tkinter as tk
from app import AboutDialog, check_vlc_installed, reveal_in_explorer


def test_check_vlc_installed_returns_bool() -> None:
    """Testa se a função check_vlc_installed retorna um valor booleano sem exceção."""
    result = check_vlc_installed()
    assert isinstance(result, bool)


def test_reveal_in_explorer_nonexistent_file() -> None:
    """Testa se reveal_in_explorer lida com arquivo inexistente sem lançar exceção."""
    reveal_in_explorer("non_existent_file.mp4")


def test_about_dialog_creation() -> None:
    """Testa se a janela modal AboutDialog pode ser criada e destruída sem erros."""
    root = tk.Tk()
    root.withdraw()
    dialog = AboutDialog(root)
    assert dialog.winfo_exists()
    dialog.destroy()
    root.destroy()
