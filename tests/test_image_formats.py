"""Verifica formatos de imagem aceitos e rejeição por conteúdo nas importações."""

import base64
import io
from pathlib import Path

import pytest
from PIL import Image

from image_formats import open_supported_image
from web_backend import EditorSession


@pytest.mark.parametrize("image_format", ["JPEG", "GIF", "PNG", "WEBP"])
def test_formatos_permitidos_sao_lidos_e_salvos(tmp_path: Path, image_format: str) -> None:
    """Valida os quatro decodificadores e o salvamento compatível com os projetos existentes."""
    buffer = io.BytesIO()
    Image.new("RGB", (16, 12), "red").save(buffer, image_format)
    with open_supported_image(io.BytesIO(buffer.getvalue())) as image:
        assert image.format == image_format
        image.load()
        assert image.size == (16, 12)
    video = tmp_path / "amostra.mp4"
    video.write_bytes(b"video")
    session = EditorSession()
    session.open(str(video))
    source = "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()
    session.save("images", [{"id": "foto", "title": "Foto", "source": source}], session.revision)
    assert session.data["images"][0]["mime_type"] == "image/jpeg"
    assert session.data["images"][0]["width"] == 16


@pytest.mark.parametrize("image_format", ["BMP", "TIFF"])
def test_formato_nao_permitido_renomeado_continua_recusado(tmp_path: Path, image_format: str) -> None:
    """Não permite contornar a restrição pela extensão ou pelo MIME declarados."""
    renamed = tmp_path / "imagem.jpg"
    Image.new("RGB", (16, 12), "red").save(renamed, image_format)
    with pytest.raises(ValueError, match="formato não suportado"), open_supported_image(renamed):
        pytest.fail("O arquivo renomeado não deveria ser aceito")
    video = tmp_path / "amostra.mp4"
    video.write_bytes(b"video")
    session = EditorSession()
    original = session.open(str(video))
    source = "data:image/jpeg;base64," + base64.b64encode(renamed.read_bytes()).decode()
    with pytest.raises(ValueError, match="formato não suportado"):
        session.save("images", [{"id": "foto", "title": "Foto", "source": source}], session.revision)
    assert session.snapshot() == original
    assert not video.with_suffix(".chp").exists()
