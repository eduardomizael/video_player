"""Testes dos utilitários e da persistência segura de legendas SRT."""

from pathlib import Path

import pytest

from logic import DataLoadError, SubtitleManager, fmt_srt_time, parse_srt_time


def test_fmt_srt_time() -> None:
    """Testa a formatação de milissegundos para SRT."""

    assert fmt_srt_time(0) == "00:00:00,000"
    assert fmt_srt_time(1500) == "00:00:01,500"
    assert fmt_srt_time(3665450) == "01:01:05,450"
    assert fmt_srt_time(-500) == "00:00:00,000"


def test_parse_srt_time() -> None:
    """Testa formatos SRT válidos e milissegundos inválidos."""

    assert parse_srt_time("00:00:01,500") == 1500
    assert parse_srt_time("01:01:05,450") == 3665450
    assert parse_srt_time("01:05,500") == 65500
    assert parse_srt_time("10") == 10000
    with pytest.raises(ValueError):
        parse_srt_time("00:00:01,1234")


def test_subtitle_manager_load_save_preserva_quebras_de_linha(tmp_path: Path) -> None:
    """Testa ida e volta sem remover quebras internas do texto."""

    manager = SubtitleManager(str(tmp_path / "video.mp4"))
    subtitles = [{"start": 1000, "end": 2500, "text": "Primeira linha\nSegunda linha"}]
    manager.save(subtitles)
    assert manager.load() == subtitles


def test_subtitle_manager_preserva_backup(tmp_path: Path) -> None:
    """Mantém a versão anterior da legenda antes de substituí-la."""

    manager = SubtitleManager(str(tmp_path / "video.mp4"))
    manager.save([{"start": 0, "end": 1000, "text": "Anterior"}])
    manager.save([{"start": 1000, "end": 2000, "text": "Nova"}])
    assert "Anterior" in (tmp_path / "video.srt.bak").read_text(encoding="utf-8")


def test_subtitle_manager_rejeita_bloco_invalido_sem_sobrescrever(tmp_path: Path) -> None:
    """Garante que um bloco inválido não seja descartado silenciosamente."""

    srt_path = tmp_path / "video.srt"
    original = "1\n00:00:02,000 --> 00:00:01,000\nInválida\n"
    srt_path.write_text(original, encoding="utf-8")
    manager = SubtitleManager(str(tmp_path / "video.mp4"))

    with pytest.raises(DataLoadError):
        manager.load()
    assert srt_path.read_text(encoding="utf-8") == original
