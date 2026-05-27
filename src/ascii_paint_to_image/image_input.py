from pathlib import Path

from PIL import Image, ImageOps

from ascii_paint_to_image.surface import DENSITY_RAMP, VxAsciiSurface


def load_image_to_surface(
    image_path: Path,
    width: int,
    height: int,
    resolution: int = 9,
    ascii_ramp: str = DENSITY_RAMP,
    gamma: float = 1.6,
) -> VxAsciiSurface:
    if width <= 0 or height <= 0:
        raise ValueError("image surface width and height must be positive")

    surface = VxAsciiSurface(
        width=width,
        height=height,
        resolution=resolution,
        ascii_ramp=ascii_ramp,
        gamma=gamma,
    )
    source = ImageOps.exif_transpose(Image.open(image_path)).convert("L")
    grayscale = ImageOps.contain(source, (width, height), method=Image.Resampling.LANCZOS)
    canvas = Image.new("L", (width, height), 255)
    offset_x = (width - grayscale.width) // 2
    offset_y = (height - grayscale.height) // 2
    canvas.paste(grayscale, (offset_x, offset_y))

    for y in range(height):
        for x in range(width):
            luminance = canvas.getpixel((x, y))
            surface.fill_cell(x, y, value=(255 - luminance) / 255)

    return surface
