"""Testes de localização, validação e persistência da configuração."""

from pathlib import Path

import pytest

import config as config_module
from config import (
    ConfigLoadError,
    _deep_update,
    load_config,
    normalize_config,
    save_config,
)


def test_deep_update() -> None:
    """Testa a atualização recursiva de dicionários."""

    base = {"a": 1, "nested": {"x": 10, "y": 20}}
    updates = {"b": 2, "nested": {"y": 99, "z": 100}}
    _deep_update(base, updates)
    assert base == {"a": 1, "b": 2, "nested": {"x": 10, "y": 99, "z": 100}}


def test_load_save_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Testa salvamento atômico e carregamento do arquivo configurado."""

    config_path = tmp_path / "config.json"
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)
    config = load_config()
    assert config["update_ms"] == 500

    config["update_ms"] = 1000
    config["keys"]["play_pause"] = "<p>"
    save_config(config)

    loaded = load_config()
    assert loaded["update_ms"] == 1000
    assert loaded["keys"]["play_pause"] == "<p>"
    assert not list(tmp_path.glob("*.tmp"))


def test_normalize_config_restaura_tipos_e_limites() -> None:
    """Garante que valores semanticamente inválidos retornem aos padrões."""

    normalized = normalize_config({"update_ms": 0, "small_jump": "abc", "large_jump": -2, "volume": 200})
    assert normalized["update_ms"] == 500
    assert normalized["small_jump"] == 5
    assert normalized["large_jump"] == 20
    assert normalized["volume"] == 100


def test_load_config_corrompida_preserva_backup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Não permite restaurar padrões sem antes preservar a configuração ilegível."""

    config_path = tmp_path / "config.json"
    config_path.write_text('{"volume":', encoding="utf-8")
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)

    with pytest.raises(ConfigLoadError) as error:
        load_config()

    assert error.value.backup_path is not None
    assert error.value.backup_path.read_text(encoding="utf-8") == '{"volume":'
    assert config_path.read_text(encoding="utf-8") == '{"volume":'


def test_config_path_fica_ao_lado_do_modulo() -> None:
    """Confirma o local estável usado no modo de execução pelo código-fonte."""

    assert config_module.CONFIG_PATH.parent == config_module.Path(config_module.__file__).resolve().parent
    assert config_module.CONFIG_PATH.name == "config.json"


def test_application_dir_fica_ao_lado_do_executavel_quando_empacotado(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Garante que o executável use seu próprio diretório, e não a pasta corrente."""

    executable = tmp_path / "EditorDeCapitulos.exe"
    monkeypatch.setattr(config_module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(config_module.sys, "executable", str(executable))
    assert config_module._application_dir() == tmp_path


def test_load_config_rejeita_raiz_nao_objeto(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Preserva também JSON sintaticamente válido com estrutura raiz incompatível."""

    config_path = tmp_path / "config.json"
    config_path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)
    with pytest.raises(ConfigLoadError) as error:
        load_config()
    assert error.value.backup_path is not None
