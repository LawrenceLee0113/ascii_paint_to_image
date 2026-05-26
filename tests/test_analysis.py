import os
import sys
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ascii_paint_to_image.analysis import (
    analyze_surface,
    ascii_text_from_surface,
    build_prompt,
    build_simple_ascii_prompt,
)
from ascii_paint_to_image.surface import DENSITY_RAMP, VxAsciiSurface


class AnalysisTest(unittest.TestCase):
    def test_ascii_text_from_surface_trims_empty_border(self) -> None:
        surface = VxAsciiSurface(width=6, height=4, resolution=5)
        surface.fill_cell(2, 1, 0.8, color=2)
        surface.fill_cell(3, 1, 1.0, color=4)

        text = ascii_text_from_surface(surface)

        self.assertEqual(len(text), 2)
        self.assertGreater(DENSITY_RAMP.index(text[1]), DENSITY_RAMP.index(text[0]))

    def test_analyze_surface_reports_density_and_regions(self) -> None:
        surface = VxAsciiSurface(width=9, height=6, resolution=5)
        surface.fill_cell(1, 1, 0.35, color=2)
        surface.fill_cell(4, 2, 0.85, color=4)
        surface.paint_line_subpixels((0, 25), (44, 25), 0, color=7, value=0.6)

        analysis = analyze_surface(surface)

        self.assertEqual(analysis["ramp"], DENSITY_RAMP)
        self.assertGreater(analysis["coverage"], 0.0)
        self.assertIn("middle-center", analysis["active_regions"])
        self.assertIn("horizontal", analysis["stroke_hints"])
        self.assertIn("blue", analysis["colors"])

    def test_build_prompt_is_plain_text_and_mentions_ascii_ramp(self) -> None:
        surface = VxAsciiSurface(width=5, height=3, resolution=5)
        surface.fill_cell(2, 1, 1.0, color=2)
        analysis = analyze_surface(surface)

        prompt = build_prompt(analysis)

        self.assertIn(DENSITY_RAMP, prompt)
        self.assertIn("pure text analysis", prompt)
        self.assertIn("Do not treat this as an uploaded image", prompt)
        self.assertNotIn("data:image", prompt)

    def test_build_simple_ascii_prompt_does_not_add_analysis_or_abstract_fallback(self) -> None:
        prompt = build_simple_ascii_prompt(
            ascii_text="  /\\\n /  \\\n \\__/",
            ascii_ramp=DENSITY_RAMP,
        )

        self.assertIn("Use the ASCII sketch directly", prompt)
        self.assertIn(" .',:-=+*oO#8%&@", prompt)
        self.assertIn("  /\\", prompt)
        self.assertNotIn("Active regions", prompt)
        self.assertNotIn("Stroke and brush hints", prompt)
        self.assertNotIn("abstract", prompt.lower())


if __name__ == "__main__":
    unittest.main()
