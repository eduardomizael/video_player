"""Testes unitários para o módulo config.py (carregamento, salvamento e mesclagem de configurações)."""

import os
import tempfile

from config import DEFAULT_CONFIG, _deep_update, load_config, save_config


def test_deep_update() -> None:
    """Testa a atualização recursiva de dicionários."""
    base = {"a": 1, "nested": {"x": 10, "y": 20}}
    updates = {"b": 2, "nested": {"y": 99, "z": 100}}

    _deep_update(base, updates)
    assert base == {"a": 1, "b": 2, "nested": {"x": 10, "y": 99, "z": 100}}


def test_load_save_config(monkeypatch) -> None:
    """Testa salvar e carregar as configurações em arquivo temporário."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_config_file = os.path.join(tmpdir, "test_config.json")
        monkeypatch.setattr("config.CONFIG_PATH", test_config_file)

        # Sem arquivo, deve carregar as configurações padrão
        cfg = load_config()
        assert cfg["update_ms"] == DEFAULT_CONFIG["update_ms"]
        assert cfg["small_jump"] == DEFAULT_CONFIG["small_jump"]

        # Modifica e salva
        cfg["small_jump"] = 10
        save_config(cfg)

        assert os.path.exists(test_config_file)

        # Recarrega e valida se foi atualizado
        reloaded = load_config()
        assert reloaded["small_jump"] == 10
