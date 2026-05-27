import os
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ascii_paint_to_image.image_input import load_image_to_surface


class ImageInputTest(unittest.TestCase):
    def test_load_image_to_surface_converts_dark_pixels_to_ink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "source.png"
            image = Image.new("RGB", (2, 1))
            image.putpixel((0, 0), (0, 0, 0))
            image.putpixel((1, 0), (255, 255, 255))
            image.save(image_path)

            surface = load_image_to_surface(
                image_path,
                width=2,
                height=1,
                resolution=3,
            )

            self.assertGreater(surface.coverage_at(0, 0), 0.95)
            self.assertLess(surface.coverage_at(1, 0), 0.05)
            self.assertNotEqual(surface.char_at(0, 0), " ")
            self.assertEqual(surface.char_at(1, 0), " ")

    def test_load_image_to_surface_preserves_aspect_with_white_padding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "source.png"
            image = Image.new("RGB", (1, 1), (0, 0, 0))
            image.save(image_path)

            surface = load_image_to_surface(
                image_path,
                width=4,
                height=2,
                resolution=3,
            )

            active_cells = sum(
                1
                for y in range(surface.height)
                for x in range(surface.width)
                if surface.coverage_at(x, y) > 0.5
            )

            self.assertEqual(active_cells, 4)
            self.assertEqual(surface.char_at(0, 0), " ")
            self.assertEqual(surface.char_at(3, 1), " ")


if __name__ == "__main__":
    unittest.main()
