import contextlib
import io
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ascii_paint_to_image.prompt_cli import (
    generate_from_prompt,
    main,
    parse_args,
    prompt_from_args,
)


class PromptCliTest(unittest.TestCase):
    def test_generate_from_prompt_writes_backup_and_calls_auth2api(self) -> None:
        calls = []

        def fake_runner(*args, **kwargs):
            calls.append((args, kwargs))
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout="/tmp/generated.png\n",
                stderr="",
            )

        with tempfile.TemporaryDirectory() as tmp:
            result = generate_from_prompt(
                prompt="paint a tiny neon city",
                runs_dir=Path(tmp),
                dry_run=False,
                auth2api_root=Path("/auth2api"),
                npm_bin="npm",
                now_label="2026-05-27-140000",
                runner=fake_runner,
            )

            self.assertEqual(result.image_path, Path("/tmp/generated.png"))
            self.assertEqual(result.run.prompt_path.read_text(), "paint a tiny neon city\n")
            self.assertEqual(result.run.ascii_path.read_text(), "\n")
            self.assertIn('"mode": "prompt"', result.run.analysis_path.read_text())
            self.assertEqual(calls[0][0][0][:3], ["npm", "run", "image"])

    def test_generate_from_prompt_dry_run_skips_auth2api(self) -> None:
        def fake_runner(*args, **kwargs):
            raise AssertionError("auth2api should not be called in dry-run")

        with tempfile.TemporaryDirectory() as tmp:
            result = generate_from_prompt(
                prompt="paint a quiet mountain",
                runs_dir=Path(tmp),
                dry_run=True,
                auth2api_root=Path("/auth2api"),
                npm_bin="npm",
                now_label="2026-05-27-141000",
                runner=fake_runner,
            )

            self.assertEqual(result.image_path, None)
            self.assertTrue(result.run.prompt_path.exists())

    def test_prompt_from_args_reads_prompt_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prompt.txt"
            path.write_text("a clean product render\n")

            args = parse_args(["--prompt-file", str(path)])

            self.assertEqual(prompt_from_args(args), "a clean product render")

    def test_main_dry_run_prints_run_and_prompt_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--dry-run",
                        "--runs-dir",
                        tmp,
                        "--now-label",
                        "2026-05-27-142000",
                        "a cinematic paper lantern",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("dry-run: auth2api was not called", stdout.getvalue())
            self.assertTrue((Path(tmp) / "2026-05-27-142000" / "prompt.txt").exists())

    def test_pyproject_exposes_ai_image_console_script(self) -> None:
        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        data = tomllib.loads(pyproject.read_text())

        self.assertEqual(
            data["project"]["scripts"]["ai-image"],
            "ascii_paint_to_image.prompt_cli:main",
        )


if __name__ == "__main__":
    unittest.main()
