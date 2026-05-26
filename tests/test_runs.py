import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ascii_paint_to_image.runs import (
    Auth2ApiConfig,
    build_auth2api_command,
    create_run_backup,
    default_npm_bin,
    run_auth2api_image,
)


class RunsTest(unittest.TestCase):
    def test_create_run_backup_writes_prompt_ascii_and_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = create_run_backup(
                runs_dir=Path(tmp),
                ascii_text=" @\n##",
                analysis={"coverage": 0.5, "active_regions": ["center"]},
                prompt="Generate an image from ASCII composition.",
                now_label="2026-05-26-153000",
            )

            self.assertEqual(run.path.name, "2026-05-26-153000")
            self.assertEqual((run.path / "ascii.txt").read_text(), " @\n##\n")
            self.assertEqual((run.path / "prompt.txt").read_text(), "Generate an image from ASCII composition.\n")
            data = json.loads((run.path / "analysis.json").read_text())
            self.assertEqual(data["coverage"], 0.5)

    def test_create_run_backup_returns_absolute_path_for_relative_runs_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmp)
                run = create_run_backup(
                    runs_dir=Path("runs"),
                    ascii_text="@",
                    analysis={"coverage": 1.0},
                    prompt="prompt",
                    now_label="2026-05-26-170000",
                )
            finally:
                os.chdir(old_cwd)

        self.assertTrue(run.path.is_absolute())

    def test_build_auth2api_command_places_out_before_prompt(self) -> None:
        command = build_auth2api_command(
            Auth2ApiConfig(root=Path("/auth2api"), npm_bin="npm"),
            out_dir=Path("/project/runs/one"),
            prompt="plain text prompt",
        )

        self.assertEqual(command.cwd, Path("/auth2api"))
        self.assertEqual(
            command.args,
            ["npm", "run", "image", "--", "--out", "/project/runs/one", "plain text prompt"],
        )

    def test_build_auth2api_command_resolves_relative_out_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmp)
                command = build_auth2api_command(
                    Auth2ApiConfig(root=Path("/auth2api"), npm_bin="npm"),
                    out_dir=Path("runs/one"),
                    prompt="plain text prompt",
                )
            finally:
                os.chdir(old_cwd)

        self.assertEqual(
            command.args,
            ["npm", "run", "image", "--", "--out", str((Path(tmp) / "runs" / "one").resolve()), "plain text prompt"],
        )

    def test_run_auth2api_image_ignores_npm_header_and_returns_png_path(self) -> None:
        def fake_runner(*args, **kwargs):
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=(
                    "> auth2api@1.0.0 image\n"
                    "> tsx scripts/generate-image.ts\n"
                    "/project/runs/one/generated.png\n"
                    "size: 1024x1024\n"
                ),
                stderr="",
            )

        image_path = run_auth2api_image(
            build_auth2api_command(
                Auth2ApiConfig(root=Path("/auth2api"), npm_bin="npm"),
                out_dir=Path("/project/runs/one"),
                prompt="plain text prompt",
            ),
            runner=fake_runner,
        )

        self.assertEqual(image_path, Path("/project/runs/one/generated.png"))

    def test_default_npm_bin_uses_existing_homebrew_npm_when_path_lacks_npm(self) -> None:
        npm_bin = default_npm_bin(
            path_value="/usr/bin:/bin",
            candidates=[Path("/missing/npm"), Path("/opt/homebrew/bin/npm")],
        )

        self.assertEqual(npm_bin, "/opt/homebrew/bin/npm")


if __name__ == "__main__":
    unittest.main()
