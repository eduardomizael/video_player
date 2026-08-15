"""Testes da persistência SQLite ``.chp`` e das regras temporais."""

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


def test_chapter_manager_cria_arquivo_chp_e_preserva_hierarquia(tmp_path: Path) -> None:
    """Persiste os dados do vídeo no SQLite por vídeo, sem usar JSON."""

    manager = ChapterManager(str(tmp_path / "video.mp4"))
    chapters = [{"title": "Capítulo 1", "start": 0, "end": 60, "subs": []}]
    casting = [{"name": "Ator A", "images": []}]
    metadata = [{"key": "autor", "value": "Eduardo", "children": []}]

    manager.save(chapters, casting, metadata)

    assert (tmp_path / "video.chp").exists()
    loaded = manager.load()
    assert loaded["chapters"][0]["title"] == "Capítulo 1"
    assert loaded["casting"][0]["name"] == "Ator A"
    assert loaded["metadata"][0]["value"] == "Eduardo"
    assert loaded["images"] == []
    assert chapters[0]["id"] == loaded["chapters"][0]["id"]


def test_chapter_manager_rejeita_arquivo_chp_invalido_sem_alterar(tmp_path: Path) -> None:
    """Impede que um arquivo binário inválido seja tratado como uma base vazia."""

    chp_path = tmp_path / "video.chp"
    original = b"nao e um sqlite"
    chp_path.write_bytes(original)

    with pytest.raises(DataLoadError):
        ChapterManager(str(tmp_path / "video.mp4")).load()
    assert chp_path.read_bytes() == original


def test_chapter_manager_normaliza_fim_e_rejeita_inicio_antes_do_pai(tmp_path: Path) -> None:
    """Mantém as regras temporais existentes ao gravar no novo formato."""

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
    """Amplia pais até o maior fim de seus descendentes no carregamento."""

    chapters = [
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
    ]
    manager = ChapterManager(str(tmp_path / "video.mp4"))
    manager.save(chapters, [])

    parent = manager.load()["chapters"][0]
    assert parent["end"] == 40
    assert parent["subs"][0]["end"] == 40


def test_chapter_manager_persiste_metadados_e_imagens_reutilizaveis(tmp_path: Path) -> None:
    """Relaciona uma imagem BLOB ao mesmo tempo a metadado, capítulo e elenco."""

    chapters = [{"title": "Abertura", "start": 0, "end": 10, "subs": []}]
    casting = [{"name": "Ator A", "images": []}]
    metadata = [{"key": "autor", "value": "Eduardo", "children": []}]
    image = {
        "title": "Retrato",
        "description": "Imagem recortada.",
        "data": b"conteudo-jpeg",
        "mime_type": "image/jpeg",
        "width": 1080,
        "height": 1080,
    }
    manager = ChapterManager(str(tmp_path / "video.mp4"))
    manager.save(chapters, casting, metadata, [image])
    image_id = image["id"]
    chapters[0]["images"] = [image_id]
    casting[0]["images"] = [image_id]
    metadata[0]["images"] = [image_id]
    manager.save(chapters, casting, metadata, [image])

    loaded = manager.load()
    assert loaded["images"][0]["data"] == b"conteudo-jpeg"
    assert loaded["chapters"][0]["images"] == [image_id]
    assert loaded["casting"][0]["images"] == [image_id]
    assert loaded["metadata"][0]["images"] == [image_id]


def test_chapter_manager_rejeita_valor_em_metadado_com_filhos(tmp_path: Path) -> None:
    """Impede persistência de um valor em nó que deixou de ser folha."""

    metadata = [{"key": "autor", "value": "Eduardo", "children": [{"key": "nome", "value": "", "children": []}]}]

    with pytest.raises(ValueError, match="dados"):
        ChapterManager(str(tmp_path / "video.mp4")).save([], [], metadata)
