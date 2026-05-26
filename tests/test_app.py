import os
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ascii_paint_to_image.app import parse_args, run_demo
from ascii_paint_to_image.app import run_controlnet_demo
from ascii_paint_to_image.controlnet import ControlNetResult, default_controlnet_experiments


class AppTest(unittest.TestCase):
    def test_parse_args_uses_project_defaults(self) -> None:
        args = parse_args([])

        self.assertEqual(args.auth2api_root, "/Users/lawrencelee0113/workspace/auth2api")
        self.assertFalse(args.dry_run)
        self.assertEqual(args.char_ramp, " .',:-=+*oO#8%&@")

    def test_parse_args_accepts_controlnet_demo(self) -> None:
        args = parse_args(["--controlnet-demo", "--controlnet-steps", "7"])

        self.assertTrue(args.controlnet_demo)
        self.assertEqual(args.controlnet_steps, 7)

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

    def test_run_controlnet_demo_writes_outline_and_report_with_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            def fake_runner(outline_path, output_dir, experiments, **kwargs):
                results = []
                for experiment in experiments:
                    image_path = output_dir / f"{experiment.slug()}.png"
                    image_path.write_bytes(b"png")
                    results.append(ControlNetResult(experiment=experiment, image_path=image_path))
                return results

            result = run_controlnet_demo(
                runs_dir=Path(tmp),
                now_label="2026-05-26-controlnet",
                runner=fake_runner,
                experiments=default_controlnet_experiments()[:1],
            )

            self.assertTrue((result.run.path / "outline.png").exists())
            self.assertTrue(result.report_path.exists())
            self.assertEqual(len(result.results), 1)


if __name__ == "__main__":
    unittest.main()
