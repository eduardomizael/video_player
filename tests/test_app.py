"""Testes para verificações auxiliares do app.py."""

from app import check_vlc_installed


def test_check_vlc_installed_returns_bool() -> None:
    """Testa se a função check_vlc_installed retorna um valor booleano sem exceção."""
    result = check_vlc_installed()
    assert isinstance(result, bool)
