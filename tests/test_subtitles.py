"""Testes unitários para o gerenciador e utilitários de legendas .srt (logic.py)."""

import os
import tempfile
import pytest

from logic import SubtitleManager, fmt_srt_time, parse_srt_time


def test_fmt_srt_time() -> None:
    """Testa a conversão de milissegundos para string no formato SRT hh:mm:ss,mss."""
    assert fmt_srt_time(0) == "00:00:00,000"
    assert fmt_srt_time(1500) == "00:00:01,500"
    assert fmt_srt_time(3665450) == "01:01:05,450"
    assert fmt_srt_time(-500) == "00:00:00,000"


def test_parse_srt_time() -> None:
    """Testa a conversão de strings de tempo estendido em milissegundos."""
    assert parse_srt_time("00:00:01,500") == 1500
    assert parse_srt_time("01:01:05,450") == 3665450
    assert parse_srt_time("01:05,500") == 65500
    assert parse_srt_time("10") == 10000

    with pytest.raises(ValueError):
        parse_srt_time("invalid:time,val")


def test_subtitle_manager_load_save() -> None:
    """Testa o carregamento e salvamento de arquivos de legenda .srt."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "movie.mp4")
        srt_path = os.path.join(tmpdir, "movie.srt")

        sub_manager = SubtitleManager(video_path)
        assert sub_manager.srt_path == srt_path

        # Sem arquivo existente deve retornar lista vazia
        assert sub_manager.load() == []

        # Salva legendas de teste
        subs = [
            {"start": 1000, "end": 4000, "text": "Primeira legenda de teste"},
            {"start": 5000, "end": 9500, "text": "Segunda legenda de teste"},
        ]
        sub_manager.save(subs)

        assert os.path.exists(srt_path)

        # Recarrega e valida o conteúdo do .srt
        loaded_subs = sub_manager.load()
        assert len(loaded_subs) == 2
        assert loaded_subs[0]["start"] == 1000
        assert loaded_subs[0]["end"] == 4000
        assert loaded_subs[0]["text"] == "Primeira legenda de teste"
        assert loaded_subs[1]["start"] == 5000
        assert loaded_subs[1]["end"] == 9500
        assert loaded_subs[1]["text"] == "Segunda legenda de teste"
