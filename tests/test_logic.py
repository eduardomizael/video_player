"""Testes dos tempos e da persistência de capítulos e casting."""

import json
from pathlib import Path

import pytest

from logic import (
    ChapterManager,
    DataLoadError,
    fmt_sec,
    parse_flexible_time,
    parse_time,
)


def test_fmt_sec() -> None:
    """Testa a conversão de segundos para texto."""

    assert fmt_sec(0) == "00:00"
    assert fmt_sec(65) == "01:05"
    assert fmt_sec(3665) == "01:01:05"
    assert fmt_sec(-10) == "00:00"


def test_parse_time() -> None:
    """Testa formatos exatos e rejeita componentes fora do intervalo."""

    assert parse_time("01:05") == 65
    assert parse_time("01:01:05") == 3665
    with pytest.raises(ValueError):
        parse_time("invalid")
    with pytest.raises(ValueError):
        parse_time("01:60")


def test_parse_flexible_time() -> None:
    """Testa entrada flexível sem aceitar caracteres ou tempos ambíguos."""

    assert parse_flexible_time("30") == 30
    assert parse_flexible_time("01:30") == 90
    assert parse_flexible_time("01:02:03") == 3723
    assert parse_flexible_time("10203") == 3723
    with pytest.raises(ValueError):
        parse_flexible_time("")
    with pytest.raises(ValueError):
        parse_flexible_time("abc12")
    with pytest.raises(ValueError):
        parse_flexible_time("0160")


def test_chapter_manager_load_save(tmp_path: Path) -> None:
    """Testa o ciclo completo e a criação de backup da versão anterior."""

    manager = ChapterManager(str(tmp_path / "video.mp4"))
    chapters = [{"title": "Capítulo 1", "start": 0, "end": 60, "subs": []}]
    casting = ["Ator A", "Ator B"]
    manager.save(chapters, casting)
    assert manager.load() == {"chapters": chapters, "casting": casting}

    manager.save(chapters, ["Ator C"])
    backup = tmp_path / "video.json.bak"
    assert json.loads(backup.read_text(encoding="utf-8"))["casting"] == casting


def test_chapter_manager_rejeita_json_corrompido_sem_alterar_arquivo(tmp_path: Path) -> None:
    """Impede que um JSON corrompido seja tratado como dados vazios."""

    json_path = tmp_path / "video.json"
    original = "JSON INVALIDO {{{"
    json_path.write_text(original, encoding="utf-8")

    with pytest.raises(DataLoadError):
        ChapterManager(str(tmp_path / "video.mp4")).load()
    assert json_path.read_text(encoding="utf-8") == original


def test_chapter_manager_normaliza_fim_provisorio_e_rejeita_inicio_fora_do_pai(tmp_path: Path) -> None:
    """Migra fins provisórios, mantendo a regra de início contido pelo pai."""

    manager = ChapterManager(str(tmp_path / "video.mp4"))
    manager.save([{"title": "Provisório", "start": 20, "end": 10, "subs": []}], [])
    assert manager.load()["chapters"][0]["end"] == 20

    invalid_sub = {
        "title": "Pai",
        "start": 10,
        "end": 20,
        "subs": [{"title": "Filho", "start": 5, "end": 15, "subs": []}],
    }
    with pytest.raises(ValueError):
        manager.save([invalid_sub], [])


def test_chapter_manager_expande_fim_dos_ancestrais(tmp_path: Path) -> None:
    """Normaliza fins provisórios sem rejeitar filhos que terminam depois do pai."""

    json_path = tmp_path / "video.json"
    json_path.write_text(
        json.dumps(
            {
                "chapters": [
                    {
                        "title": "Pai",
                        "start": 0,
                        "end": 10,
                        "subs": [
                            {
                                "title": "Filho",
                                "start": 5,
                                "end": 20,
                                "subs": [{"title": "Neto", "start": 15, "end": 40, "subs": []}],
                            }
                        ],
                    }
                ],
                "casting": [],
            }
        ),
        encoding="utf-8",
    )

    loaded = ChapterManager(str(tmp_path / "video.mp4")).load()

    parent = loaded["chapters"][0]
    child = parent["subs"][0]
    assert child["end"] == 40
    assert parent["end"] == 40
