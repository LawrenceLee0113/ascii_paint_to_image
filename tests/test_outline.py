import os
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ascii_paint_to_image.outline import save_surface_outline
from ascii_paint_to_image.surface import VxAsciiSurface


class OutlineTest(unittest.TestCase):
    def test_save_surface_outline_writes_scaled_grayscale_image(self) -> None:
        surface = VxAsciiSurface(width=2, height=2, resolution=3)
        surface.fill_cell(1, 0, 1.0)
        surface.fill_cell(0, 1, 0.5)

        with tempfile.TemporaryDirectory() as tmp:
            path = save_surface_outline(
                surface=surface,
                path=Path(tmp) / "outline.png",
                cell_size=4,
                polarity="white-on-black",
            )

            self.assertTrue(path.exists())
            from PIL import Image

            image = Image.open(path)
            self.assertEqual(image.mode, "RGB")
            self.assertEqual(image.size, (8, 8))
            self.assertGreater(image.getpixel((5, 1))[0], image.getpixel((1, 1))[0])


if __name__ == "__main__":
    unittest.main()
