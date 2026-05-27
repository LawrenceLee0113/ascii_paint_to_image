import os
import sys
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ascii_paint_to_image.surface import DENSITY_RAMP, VxAsciiSurface, ink_value_for_speed


class SurfaceTest(unittest.TestCase):
    def test_repeated_partial_ink_upgrades_character_density(self) -> None:
        surface = VxAsciiSurface(width=1, height=1, resolution=5, ascii_ramp=DENSITY_RAMP)

        surface.paint_global_subpixel(2, 2, radius=1, value=0.25, color=2)
        first = surface.char_at(0, 0)
        surface.paint_global_subpixel(2, 2, radius=1, value=0.75, color=2)
        second = surface.char_at(0, 0)

        self.assertGreater(DENSITY_RAMP.index(second), DENSITY_RAMP.index(first))

    def test_speed_controls_ink_value(self) -> None:
        self.assertEqual(ink_value_for_speed(speed=0, fast_speed=20, min_value=0.25), 1.0)
        self.assertEqual(ink_value_for_speed(speed=20, fast_speed=20, min_value=0.25), 0.25)

    def test_erase_global_subpixel_removes_ink_and_color(self) -> None:
        surface = VxAsciiSurface(width=1, height=1, resolution=5, ascii_ramp=DENSITY_RAMP)

        surface.paint_global_subpixel(2, 2, radius=4, value=1.0, color=3)
        self.assertNotEqual(surface.char_at(0, 0), " ")
        self.assertEqual(surface.color_at(0, 0), 3)

        surface.erase_global_subpixel(2, 2, radius=4)

        self.assertEqual(surface.char_at(0, 0), " ")
        self.assertEqual(surface.color_at(0, 0), None)

    def test_snapshot_and_restore_preserve_ink_and_color(self) -> None:
        surface = VxAsciiSurface(width=1, height=1, resolution=5, ascii_ramp=DENSITY_RAMP)
        surface.paint_global_subpixel(2, 2, radius=2, value=1.0, color=6)
        snapshot = surface.snapshot()
        drawn = surface.char_at(0, 0)

        surface.clear()
        surface.restore(snapshot)

        self.assertEqual(surface.char_at(0, 0), drawn)
        self.assertEqual(surface.color_at(0, 0), 6)


if __name__ == "__main__":
    unittest.main()
