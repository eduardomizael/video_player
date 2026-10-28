"""Verifica inclusão seletiva, persistência e reabertura da biblioteca de vídeos."""

from pathlib import Path

import pytest

import config
from config import default_config
from logic import ChapterManager, SubtitleManager
from video_history import VideoHistory
from web_app import WebApi
from web_backend import EditorSession


@pytest.fixture
def api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> WebApi:
    """Cria uma sessão com índice e preferências isolados dos dados do usuário."""
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.vdb")
    video = tmp_path / "vídeo.mp4"
    video.write_bytes(b"video")
    session = EditorSession()
    session.open(str(video))
    return WebApi(session, default_config())


def test_apenas_abrir_nao_cria_projeto_nem_historico(api: WebApi) -> None:
    """Mantém vídeos apenas visualizados fora do índice, sem criar CHP vazio."""
    snapshot = api.get_state()
    assert api.list_history() == []
    assert api._history.path == config.CONFIG_PATH
    assert not Path(snapshot["path"]).with_suffix(".chp").exists()


@pytest.mark.parametrize("section", ["casting", "subtitles"])
def test_salvar_recurso_registra_e_reabre_entre_sessoes(api: WebApi, section: str) -> None:
    """Inclui tanto recursos CHP quanto legendas SRT sem exigir o outro formato."""
    items = [{"name": "Pessoa"}] if section == "casting" else [{"start": 0, "end": 1000, "text": "Olá"}]
    saved = api.save_section(section, items, api._session.revision)
    history = VideoHistory(api._history.path)
    entry = history.entries()[0]
    assert entry["path"] == saved["path"] and entry["available"]
    if section == "subtitles":
        assert not Path(saved["path"]).with_suffix(".chp").exists()
    fresh = WebApi(EditorSession(), default_config())
    opened = fresh.open_history(entry["id"])
    assert opened["path"] == saved["path"]
    assert opened["subtitles"] == saved["subtitles"]
    assert opened["data"] == saved["data"]
    assert len(fresh.list_history()) == 1


def test_falha_ao_salvar_recurso_nao_inclui_video(api: WebApi) -> None:
    """Não registra tentativas de gravação rejeitadas pela validação."""
    with pytest.raises(ValueError):
        api.save_section("chapters", [{"start": -1, "end": 1, "title": "Inválido"}], api._session.revision)
    assert api.list_history() == []


def test_falha_do_indice_nao_oculta_recurso_salvo(api: WebApi, monkeypatch: pytest.MonkeyPatch) -> None:
    """Reporta o erro da biblioteca sem induzir o usuário a repetir uma gravação concluída."""

    def fail_remember(video: Path) -> bool:
        """Simula um índice sem permissão de escrita."""
        raise OSError("Sem permissão")

    monkeypatch.setattr(api._history, "remember", fail_remember)
    saved = api.save_section("casting", [{"name": "Pessoa"}], api._session.revision)
    assert "biblioteca não foi atualizada" in saved["history_warning"]
    assert ChapterManager(saved["path"]).load()["casting"][0]["name"] == "Pessoa"


def test_projeto_preexistente_entra_ao_abrir(api: WebApi) -> None:
    """Reconhece recursos anteriores mesmo sem uma gravação nesta execução."""
    SubtitleManager(str(api._session.path)).save([{"start": 0, "end": 1000, "text": "Anterior"}])
    api.get_state()
    assert len(api.list_history()) == 1


def test_importacao_recursiva_deduplica_e_preserva_nomes_iguais(api: WebApi, tmp_path: Path) -> None:
    """Descobre projetos antigos sem incluir arquivos sem recursos ou duplicar caminhos."""
    first = api._session.path
    ChapterManager(str(first)).save([], [])
    nested = tmp_path / "subpasta"
    nested.mkdir()
    second = nested / first.name
    second.write_bytes(b"video")
    SubtitleManager(str(second)).save([{"start": 0, "end": 1000, "text": "Legenda"}])
    (nested / "sem recursos.mp4").write_bytes(b"video")
    (nested / "sem video.chp").write_bytes(b"ignorado")
    assert api._history.import_folder(tmp_path) == 2
    assert api._history.import_folder(tmp_path) == 2
    assert len(api.list_history()) == 2
    assert {entry["path"] for entry in api.list_history()} == {str(first), str(second)}
    identifier = next(entry["id"] for entry in api.list_history() if entry["path"] == str(first))
    api.open_history(identifier)
    assert api.list_history()[0]["id"] == identifier


def test_indisponivel_permanece_e_abertura_invalida_preserva_sessao(api: WebApi) -> None:
    """Preserva o índice e a sessão quando o arquivo não existe ou o ID é desconhecido."""
    api.save_section("casting", [{"name": "Pessoa"}], api._session.revision)
    snapshot = api._session.snapshot()
    Path(snapshot["path"]).unlink()
    entry = api.list_history()[0]
    assert not entry["available"]
    with pytest.raises(FileNotFoundError, match="indisponível"):
        api.open_history(entry["id"])
    with pytest.raises(ValueError, match="biblioteca"):
        api.open_history("caminho arbitrário")
    assert api._session.snapshot() == snapshot
