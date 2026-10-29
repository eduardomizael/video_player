"""Restringe a importação de imagens aos formatos suportados pela aplicação."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

from PIL import Image, UnidentifiedImageError

SUPPORTED_IMAGE_FORMATS = ("JPEG", "GIF", "PNG", "WEBP")
IMAGE_FORMAT_ERROR = "Imagem inválida ou formato não suportado. Use JPG/JPEG, GIF, PNG ou WebP."


@contextmanager
def open_supported_image(source: str | Path | BinaryIO) -> Iterator[Image.Image]:
    """Abre somente formatos permitidos, identificados pelo conteúdo do arquivo."""
    try:
        image = Image.open(source, formats=SUPPORTED_IMAGE_FORMATS)
    except UnidentifiedImageError as exc:
        raise ValueError(IMAGE_FORMAT_ERROR) from exc
    with image:
        yield image
