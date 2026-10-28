"""Verifica migração, preservação e transações do banco único da aplicação."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

import config
from app_storage import StorageError, open_storage
from config import ConfigLoadError, load_config, save_config
from video_history import VideoHistory


def create_legacy_history(path: Path) -> None:
    """Cria um índice antigo com um vídeo indisponível para conferir a preservação."""
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("CREATE TABLE videos (key TEXT PRIMARY KEY, path TEXT NOT NULL, accessed TEXT NOT NULL)")
        connection.execute("INSERT INTO videos VALUES ('video', 'ausente.mp4', '2026-10-20T12:00:00+00:00')")


def test_migracao_preserva_fontes_e_importa_uma_unica_vez(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Importa preferências e caminhos antigos sem depender da existência dos vídeos."""
    target = tmp_path / "config.vdb"
    monkeypatch.setattr(config, "CONFIG_PATH", target)
    legacy = tmp_path / "config.json"
    legacy.write_text(json.dumps({"volume": 42, "small_jump": 9, "keys": {"play_pause": "<p>"}}), encoding="utf-8")
    old_history = tmp_path / "video_history.sqlite3"
    create_legacy_history(old_history)
    original_json, original_history = legacy.read_bytes(), old_history.read_bytes()

    loaded = load_config()
    history = VideoHistory()
    assert history.path == target
    assert target.read_bytes().startswith(b"SQLite format 3\x00")
    assert loaded["volume"] == 42 and loaded["small_jump"] == 9
    assert loaded["keys"]["play_pause"] == "<p>"
    assert history.entries()[0]["id"] == "video"
    assert not history.entries()[0]["available"]
    assert legacy.read_bytes() == original_json and old_history.read_bytes() == original_history

    loaded["volume"] = 65
    save_config(loaded)
    legacy.write_text('{"volume": 1}', encoding="utf-8")
    assert load_config()["volume"] == 65
    assert len(history.entries()) == 1


def test_migracao_falha_inteira_e_permite_nova_tentativa(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Um histórico corrompido impede também a importação parcial das preferências."""
    target = tmp_path / "config.vdb"
    monkeypatch.setattr(config, "CONFIG_PATH", target)
    legacy = tmp_path / "config.json"
    legacy.write_text('{"volume": 42}', encoding="utf-8")
    old_history = tmp_path / "video_history.sqlite3"
    old_history.write_bytes(b"banco ilegivel")
    with pytest.raises(ConfigLoadError) as error:
        load_config()
    assert error.value.path == old_history
    assert error.value.backup_path.read_bytes() == b"banco ilegivel"
    with closing(sqlite3.connect(target)) as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == []
    assert legacy.read_text(encoding="utf-8") == '{"volume": 42}'
    assert old_history.read_bytes() == b"banco ilegivel"
    old_history.unlink()
    create_legacy_history(old_history)
    assert load_config()["volume"] == 42
    assert len(VideoHistory().entries()) == 1


def test_configuracoes_e_biblioteca_nao_sobrescrevem_uma_a_outra(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Alterna gravações nas duas tabelas e confere a preservação entre conexões."""
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.vdb")
    preferences = load_config()
    preferences["video_scroll_jump"] = 12
    save_config(preferences)
    video = tmp_path / "amostra.mp4"
    video.write_bytes(b"video")
    video.with_suffix(".srt").write_text("legenda", encoding="utf-8")
    VideoHistory().remember(video)
    assert load_config()["video_scroll_jump"] == 12
    preferences["track_scroll_jump"] = 45
    save_config(preferences)
    assert len(VideoHistory().entries()) == 1
    assert load_config()["track_scroll_jump"] == 45


def test_banco_corrompido_nao_e_substituido_por_padroes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Preserva um VDB ilegível tanto ao carregar quanto ao tentar salvar padrões."""
    target = tmp_path / "config.vdb"
    target.write_bytes(b"arquivo danificado")
    monkeypatch.setattr(config, "CONFIG_PATH", target)
    with pytest.raises(ConfigLoadError) as error:
        load_config()
    assert error.value.backup_path.read_bytes() == target.read_bytes()
    with pytest.raises(StorageError):
        save_config(config.default_config())
    assert target.read_bytes() == b"arquivo danificado"


def test_versao_futura_nao_e_modificada(tmp_path: Path) -> None:
    """Recusa bancos de versões desconhecidas sem modificar suas tabelas."""
    target = tmp_path / "config.vdb"
    with closing(sqlite3.connect(target)) as connection, connection:
        connection.execute("CREATE TABLE app_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO app_metadata VALUES ('schema_version', '99')")
    before = target.read_bytes()
    with pytest.raises(StorageError, match="incompatível"), open_storage(target):
        pytest.fail("A versão futura não deveria abrir")
    assert target.read_bytes() == before


def test_erro_de_gravacao_desfaz_todas_as_preferencias(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Uma falha no meio da gravação não deixa configurações parcialmente atualizadas."""
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.vdb")
    original = load_config()
    save_config(original)
    with open_storage(config.CONFIG_PATH) as connection:
        connection.execute(
            "CREATE TRIGGER recusar_volume BEFORE UPDATE ON settings WHEN NEW.key='volume' "
            "BEGIN SELECT RAISE(ABORT, 'Falha simulada'); END"
        )
    edited = original | {"small_jump": 12, "volume": 42}
    with pytest.raises(StorageError, match="Falha simulada"):
        save_config(edited)
    assert load_config() == original


def test_json_invalido_no_banco_nao_permite_gravar_padroes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Evita que o fechamento após uma falha de leitura apague preferências recuperáveis."""
    target = tmp_path / "config.vdb"
    monkeypatch.setattr(config, "CONFIG_PATH", target)
    original = load_config() | {"volume": 42}
    save_config(original)
    with open_storage(target) as connection:
        connection.execute("UPDATE settings SET value='json invalido' WHERE key='keys'")
    before = target.read_bytes()
    with pytest.raises(ConfigLoadError):
        load_config()
    with pytest.raises(StorageError):
        save_config(config.default_config())
    assert target.read_bytes() == before
    with open_storage(target) as connection:
        assert connection.execute("SELECT value FROM settings WHERE key='volume'").fetchone()[0] == "42"
