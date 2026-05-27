import os
import sys
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ascii_paint_to_image.history import SurfaceHistory
from ascii_paint_to_image.surface import VxAsciiSurface


class SurfaceHistoryTest(unittest.TestCase):
    def test_undo_and_redo_restore_surface_snapshots(self) -> None:
        surface = VxAsciiSurface(width=2, height=1, resolution=3)
        history = SurfaceHistory()

        history.remember(surface)
        surface.fill_cell(0, 0, value=1.0, color=2)
        drawn = surface.char_at(0, 0)

        self.assertTrue(history.undo(surface))
        self.assertEqual(surface.char_at(0, 0), " ")
        self.assertEqual(surface.color_at(0, 0), None)

        self.assertTrue(history.redo(surface))
        self.assertEqual(surface.char_at(0, 0), drawn)
        self.assertEqual(surface.color_at(0, 0), 2)

    def test_new_edit_after_undo_clears_redo_stack(self) -> None:
        surface = VxAsciiSurface(width=2, height=1, resolution=3)
        history = SurfaceHistory()

        history.remember(surface)
        surface.fill_cell(0, 0, value=1.0, color=2)
        history.undo(surface)

        history.remember(surface)
        surface.fill_cell(1, 0, value=1.0, color=4)

        self.assertFalse(history.redo(surface))
        self.assertEqual(surface.char_at(0, 0), " ")
        self.assertNotEqual(surface.char_at(1, 0), " ")


if __name__ == "__main__":
    unittest.main()
