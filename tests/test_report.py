import os
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ascii_paint_to_image.controlnet import ControlNetExperiment, ControlNetResult
from ascii_paint_to_image.report import write_controlnet_report


class ReportTest(unittest.TestCase):
    def test_write_controlnet_report_links_outline_and_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outline = root / "outline.png"
            output = root / "photo-object.png"
            outline.write_bytes(b"outline")
            output.write_bytes(b"output")
            experiment = ControlNetExperiment(
                name="photo-object",
                prompt="photorealistic object",
                negative_prompt="",
                seed=11,
                steps=8,
                guidance_scale=7.0,
                controlnet_conditioning_scale=0.8,
            )
            result = ControlNetResult(experiment=experiment, image_path=output)

            report = write_controlnet_report(
                run_dir=root,
                title="ControlNet Local Prototype",
                outline_path=outline,
                results=[result],
                base_model="base",
                controlnet_model="control",
                device="mps",
            )

            html = report.read_text()
            self.assertIn("ControlNet Local Prototype", html)
            self.assertIn("outline.png", html)
            self.assertIn("photo-object.png", html)
            self.assertIn("photorealistic object", html)


if __name__ == "__main__":
    unittest.main()
