"""Gera PNG e ICO a partir dos retângulos do símbolo vetorial usado na interface."""

from pathlib import Path
from xml.etree import ElementTree

from PIL import Image, ImageDraw


def generate_icon() -> None:
    """Rasteriza o SVG local com suavização e grava os tamanhos usados pelo Windows."""
    directory = Path(__file__).resolve().parents[1] / "web_ui"
    source = ElementTree.parse(directory / "app-icon.svg").getroot()
    scale = 16
    image = Image.new("RGBA", (64 * scale, 64 * scale))
    draw = ImageDraw.Draw(image)
    for rectangle in source.findall("{http://www.w3.org/2000/svg}rect"):
        x, y = (float(rectangle.get(key, "0")) * scale for key in ("x", "y"))
        width, height = (float(rectangle.attrib[key]) * scale for key in ("width", "height"))
        radius = float(rectangle.get("rx", "0")) * scale
        draw.rounded_rectangle((x, y, x + width - 1, y + height - 1), radius=radius, fill=rectangle.attrib["fill"])
    image = image.resize((256, 256), Image.Resampling.LANCZOS)
    image.save(directory / "app-icon.png")
    image.save(directory / "app-icon.ico", sizes=[(size, size) for size in (16, 24, 32, 48, 64, 128, 256)])


if __name__ == "__main__":
    generate_icon()
