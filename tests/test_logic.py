"""Testes unitários para o módulo logic.py (fmt_sec, parse_flexible_time e ChapterManager)."""

import json
import os
import tempfile
import pytest

from logic import ChapterManager, fmt_sec, parse_flexible_time, parse_time


def test_fmt_sec() -> None:
    """Testa a conversão de segundos para formato de string hh:mm:ss ou mm:ss."""
    assert fmt_sec(0) == "00:00"
    assert fmt_sec(65) == "01:05"
    assert fmt_sec(3665) == "01:01:05"
    assert fmt_sec(-10) == "00:00"  # Deve tratar números negativos com max(0, sec)


def test_parse_time() -> None:
    """Testa a conversão de formato de tempo exato mm:ss e hh:mm:ss em segundos."""
    assert parse_time("01:05") == 65
    assert parse_time("01:01:05") == 3665

    with pytest.raises(ValueError):
        parse_time("invalid")


def test_parse_flexible_time() -> None:
    """Testa a conversão flexível aceitando dígitos simples, mm:ss ou hh:mm:ss."""
    assert parse_flexible_time("30") == 30
    assert parse_flexible_time("01:30") == 90
    assert parse_flexible_time("01:02:03") == 3723
    assert parse_flexible_time("10203") == 3723

    with pytest.raises(ValueError):
        parse_flexible_time("")

    with pytest.raises(ValueError):
        parse_flexible_time("abc")


def test_chapter_manager_load_save() -> None:
    """Testa o salvamento e carregamento de capítulos e casting via ChapterManager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "test_video.mp4")
        json_path = os.path.join(tmpdir, "test_video.json")

        manager = ChapterManager(video_path)
        assert manager.json_path == json_path

        # Inicialmente sem arquivo deve retornar dicionário vazio
        data = manager.load()
        assert data == {"chapters": [], "casting": []}

        # Salva dados de teste
        chaps = [{"title": "Capítulo 1", "start": 0, "end": 60, "subs": []}]
        cast = ["Ator A", "Ator B"]
        manager.save(chaps, cast)

        assert os.path.exists(json_path)

        # Carrega dados salvos
        loaded_data = manager.load()
        assert loaded_data["chapters"] == chaps
        assert loaded_data["casting"] == cast


def test_chapter_manager_corrupted_json() -> None:
    """Testa a resiliência do ChapterManager ao carregar um arquivo JSON corrompido."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "corrupt_video.mp4")
        json_path = os.path.join(tmpdir, "corrupt_video.json")

        with open(json_path, "w", encoding="utf-8") as fh:
            fh.write("JSON INVALIDO {{{")

        manager = ChapterManager(video_path)
        data = manager.load()
        # Deve retornar dicionário padrão em caso de JSONDecodeError
        assert data == {"chapters": [], "casting": []}
