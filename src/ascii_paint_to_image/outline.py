from pathlib import Path
from typing import Literal

from ascii_paint_to_image.surface import VxAsciiSurface


Polarity = Literal["white-on-black", "black-on-white"]


def surface_to_outline_image(
    surface: VxAsciiSurface,
    cell_size: int = 16,
    polarity: Polarity = "black-on-white",
):
    if cell_size <= 0:
        raise ValueError("cell_size must be positive")
    if polarity not in ("white-on-black", "black-on-white"):
        raise ValueError("polarity must be white-on-black or black-on-white")

    from PIL import Image, ImageDraw

    width = surface.width * cell_size
    height = surface.height * cell_size
    background = 0 if polarity == "white-on-black" else 255
    image = Image.new("L", (width, height), background)
    draw = ImageDraw.Draw(image)

    for y in range(surface.height):
        for x in range(surface.width):
            coverage = surface.coverage_at(x, y)
            if coverage <= 0:
                continue
            ink = max(0, min(255, round(coverage * 255)))
            value = ink if polarity == "white-on-black" else 255 - ink
            draw.rectangle(
                (
                    x * cell_size,
                    y * cell_size,
                    (x + 1) * cell_size - 1,
                    (y + 1) * cell_size - 1,
                ),
                fill=value,
            )

    return image.convert("RGB")


def save_surface_outline(
    surface: VxAsciiSurface,
    path: Path,
    cell_size: int = 16,
    polarity: Polarity = "black-on-white",
) -> Path:
    image = surface_to_outline_image(
        surface=surface,
        cell_size=cell_size,
        polarity=polarity,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return path
