"""Testes para verificações auxiliares do app.py."""

from app import check_vlc_installed, reveal_in_explorer


def test_check_vlc_installed_returns_bool() -> None:
    """Testa se a função check_vlc_installed retorna um valor booleano sem exceção."""
    result = check_vlc_installed()
    assert isinstance(result, bool)


def test_reveal_in_explorer_nonexistent_file() -> None:
    """Testa se reveal_in_explorer lida com arquivo inexistente sem lançar exceção."""
    reveal_in_explorer("non_existent_file.mp4")

