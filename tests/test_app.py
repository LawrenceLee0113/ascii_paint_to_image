import os
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ascii_paint_to_image.app import parse_args, run_demo


class AppTest(unittest.TestCase):
    def test_parse_args_uses_project_defaults(self) -> None:
        args = parse_args([])

        self.assertEqual(args.auth2api_root, "/Users/lawrencelee0113/workspace/auth2api")
        self.assertFalse(args.dry_run)
        self.assertEqual(args.char_ramp, " .',:-=+*oO#8%&@")

    def test_parse_args_accepts_input_image_alias(self) -> None:
        args = parse_args(["--image", "sketch.png"])

        self.assertEqual(args.input_image, "sketch.png")

    def test_run_demo_dry_run_writes_prompt_without_calling_auth2api(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_demo(
                runs_dir=Path(tmp),
                dry_run=True,
                now_label="2026-05-26-160000",
            )

            self.assertEqual(result.image_path, None)
            self.assertTrue((result.run.path / "prompt.txt").exists())
            self.assertTrue((result.run.path / "ascii.txt").exists())

    def test_run_demo_simple_prompt_skips_analysis_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_demo(
                runs_dir=Path(tmp),
                dry_run=True,
                now_label="2026-05-26-170000",
                prompt_mode="simple",
            )

            prompt = result.run.prompt_path.read_text()
            analysis = result.run.analysis_path.read_text()
            self.assertIn("Use the ASCII sketch directly", prompt)
            self.assertIn('"mode": "simple-ascii"', analysis)
            self.assertNotIn("Active regions", prompt)
            self.assertNotIn("abstract", prompt.lower())


if __name__ == "__main__":
    unittest.main()
