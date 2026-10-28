"""Verifica compatibilidade da sessão web e entrega segura de mídia com busca."""

import base64
import io
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from PIL import Image

import config as config_module
from config import default_config, load_config, save_config
from logic import ChapterManager, SubtitleManager
from web_app import WebApi
from web_backend import EditorSession, MediaServer


def test_configuracoes_web_persistem_saltos_e_preservam_preferencias(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Reabre os saltos gravados e mantém preferências alteradas depois da inicialização."""
    monkeypatch.setattr(config_module, "CONFIG_PATH", tmp_path / "config.vdb")
    api = WebApi(EditorSession(), default_config())
    existing = default_config()
    existing.update(volume=42, always_on_top=True)
    existing["keys"]["play_pause"] = "<p>"
    save_config(existing)
    saved = api.save_settings(7, 30, 2, 12)
    assert saved == load_config() == api.get_state()["settings"]
    assert saved["small_jump"] == 7 and saved["large_jump"] == 30
    assert saved["video_scroll_jump"] == 2 and saved["track_scroll_jump"] == 12
    assert saved["volume"] == 42 and saved["always_on_top"] is True
    assert saved["keys"]["play_pause"] == "<p>"


@pytest.mark.parametrize("value", [0, -1, 3601, 1.5, True, "5", None])
def test_configuracoes_web_rejeitam_saltos_invalidos(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, value: object
) -> None:
    """Recusa entradas inválidas sem criar arquivo ou mudar o estado ativo."""
    path = tmp_path / "config.vdb"
    monkeypatch.setattr(config_module, "CONFIG_PATH", path)
    api = WebApi(EditorSession(), default_config())
    for index in range(4):
        jumps = [5, 20, 5, 20]
        jumps[index] = value
        with pytest.raises(ValueError, match="inteiros"):
            api.save_settings(*jumps)
    assert not path.exists()
    assert api.get_state()["settings"] == default_config()


def test_configuracoes_web_falha_de_escrita_preserva_estado(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Mantém os intervalos ativos quando o disco recusa a gravação."""
    monkeypatch.setattr(config_module, "CONFIG_PATH", tmp_path / "config.vdb")
    api = WebApi(EditorSession(), default_config())

    def fail_save(config: dict) -> None:
        """Simula uma falha de permissão no arquivo de preferências."""
        raise OSError("Sem permissão")

    monkeypatch.setattr("web_app.save_config", fail_save)
    with pytest.raises(OSError, match="Sem permissão"):
        api.save_settings(7, 30, 2, 12)
    assert api.get_state()["settings"] == default_config()
    assert not api._saving


@pytest.fixture
def session(tmp_path: Path) -> EditorSession:
    """Abre um arquivo temporário sem tocar nos vídeos ou dados do usuário."""
    path = tmp_path / "vídeo com espaços.mp4"
    path.write_bytes(bytes(range(256)) * 64)
    session = EditorSession()
    session.open(str(path))
    return session


def test_web_e_classico_compartilham_hierarquia_e_srt(session: EditorSession) -> None:
    """Confirma tempos, expansão dos pais e leitura bidirecional pelos gerenciadores."""
    parent = {
        "id": "pai",
        "title": "Pai",
        "start": 0,
        "end": 2,
        "subs": [{"id": "filho", "title": "Filho", "start": 1, "end": 12, "subs": []}],
    }
    session.save("chapters", [parent], session.revision)
    manager = ChapterManager(str(session.path))
    assert manager.load()["chapters"][0]["end"] == 12
    session.save("subtitles", [{"start": 125, "end": 2125, "text": "Olá\nmundo"}], session.revision)
    assert SubtitleManager(str(session.path)).load() == session.subtitles
    data = manager.load()
    manager.save(data["chapters"], [{"name": "Atriz"}], data["metadata"], data["images"])
    session.open(str(session.path))
    assert session.snapshot()["data"]["casting"][0]["name"] == "Atriz"


def test_salvar_secao_preserva_imagens_e_associacoes(session: EditorSession) -> None:
    """Garante que o JSON da ponte não descarte BLOBs ou vínculos de outras seções."""
    image = Image.new("RGB", (10, 15), "red")
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    source = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
    session.save("images", [{"id": "foto", "title": "Foto", "source": source}], session.revision)
    session.save("casting", [{"name": "Pessoa", "images": ["foto"]}], session.revision)
    session.save("metadata", [{"key": "Local", "value": "Brasil"}], session.revision)
    loaded = ChapterManager(str(session.path)).load()
    assert loaded["images"][0]["data"].startswith(b"\xff\xd8")
    assert loaded["casting"][0]["images"] == ["foto"]
    assert "data" not in session.snapshot()["data"]["images"][0]
    session.save("images", [], session.revision)
    assert session.data["casting"][0]["images"] == []


def test_rejeita_gravacao_desatualizada_e_alteracao_externa(session: EditorSession) -> None:
    """Evita sobrescrever alterações de outra interface ou requisição atrasada."""
    with pytest.raises(ValueError, match="sessão mudou"):
        session.save("casting", [], session.revision - 1)
    Path(str(session.path.with_suffix(".srt"))).write_text("alteração externa", encoding="utf-8")
    with pytest.raises(ValueError, match="outro programa"):
        session.save("subtitles", [], session.revision)
    assert session.path.with_suffix(".srt").read_text(encoding="utf-8") == "alteração externa"


def test_erro_de_validacao_nao_altera_dados(session: EditorSession) -> None:
    """Mantém o estado da sessão quando a validação compartilhada rejeita a edição."""
    original = session.snapshot()
    with pytest.raises(ValueError):
        session.save("metadata", [{"key": "x", "value": "pai", "children": [{"key": "y"}]}], session.revision)
    assert session.snapshot() == original
    with pytest.raises(FileNotFoundError):
        session.open(str(session.path.parent / "ausente.mp4"))
    assert session.snapshot() == original


def test_gerenciador_libera_arquivo_apos_leitura_e_gravacao(session: EditorSession) -> None:
    """Verifica no Windows que o backend não mantém conexões SQLite abertas."""
    import gc

    manager = ChapterManager(str(session.path))
    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        manager.save([], [])
        manager.load()
        Path(manager.chp_path).unlink()
        assert not Path(manager.chp_path).exists()
    finally:
        if gc_was_enabled:
            gc.enable()


def test_streaming_intervalos_head_e_restricao_de_rotas(session: EditorSession) -> None:
    """Verifica os intervalos usados pelo player, sem disponibilizar outros arquivos."""
    server = MediaServer(session)
    url = server.start()
    media = session.snapshot()["media_url"]
    try:
        for interval, expected in [("bytes=5-12", bytes(range(5, 13))), ("bytes=-3", bytes([253, 254, 255]))]:
            with urlopen(Request(media, headers={"Range": interval}), timeout=3) as response:
                assert response.status == 206
                assert response.read() == expected
                assert response.headers["Accept-Ranges"] == "bytes"
        with urlopen(Request(media, method="HEAD"), timeout=3) as response:
            assert int(response.headers["Content-Length"]) == session.path.stat().st_size
            assert response.read() == b""
        with urlopen(url, timeout=3) as response:
            assert b'lang="pt-BR"' in response.read()
        for route in [url + "../config.json", url + "logic.py", url.replace(server.token, "incorreto")]:
            with pytest.raises(HTTPError) as error:
                urlopen(route, timeout=3)
            assert error.value.code == 404
        with pytest.raises(HTTPError) as error:
            urlopen(Request(media, headers={"Range": "bytes=999999-"}), timeout=3)
        assert error.value.code == 416
        session.open(str(session.path))
        with pytest.raises(HTTPError):
            urlopen(media, timeout=3)
    finally:
        server.close()
