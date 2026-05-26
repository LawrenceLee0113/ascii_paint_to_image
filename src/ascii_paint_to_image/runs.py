import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional


@dataclass(frozen=True)
class RunBackup:
    path: Path
    ascii_path: Path
    analysis_path: Path
    prompt_path: Path


@dataclass(frozen=True)
class Auth2ApiConfig:
    root: Path = Path("/Users/lawrencelee0113/workspace/auth2api")
    npm_bin: str = field(default_factory=lambda: default_npm_bin())


@dataclass(frozen=True)
class Auth2ApiCommand:
    cwd: Path
    args: list


def default_npm_bin(
    path_value: Optional[str] = None,
    candidates: Optional[list] = None,
) -> str:
    found = shutil.which("npm", path=path_value or os.environ.get("PATH"))
    if found:
        return found
    for candidate in candidates or [
        Path("/opt/homebrew/bin/npm"),
        Path("/usr/local/bin/npm"),
        Path("/usr/bin/npm"),
    ]:
        if candidate.exists():
            return str(candidate)
    return "npm"


def timestamp_label(now: Optional[datetime] = None) -> str:
    current = now or datetime.now()
    return current.strftime("%Y-%m-%d-%H%M%S")


def create_run_backup(
    runs_dir: Path,
    ascii_text: str,
    analysis: dict,
    prompt: str,
    now_label: Optional[str] = None,
) -> RunBackup:
    label = now_label or timestamp_label()
    run_dir = _unique_run_dir(runs_dir.resolve(), label)
    run_dir.mkdir(parents=True, exist_ok=False)
    ascii_path = run_dir / "ascii.txt"
    analysis_path = run_dir / "analysis.json"
    prompt_path = run_dir / "prompt.txt"
    ascii_path.write_text(_with_newline(ascii_text))
    analysis_path.write_text(json.dumps(analysis, indent=2, ensure_ascii=False) + "\n")
    prompt_path.write_text(_with_newline(prompt))
    return RunBackup(
        path=run_dir,
        ascii_path=ascii_path,
        analysis_path=analysis_path,
        prompt_path=prompt_path,
    )


def build_auth2api_command(
    config: Auth2ApiConfig,
    out_dir: Path,
    prompt: str,
) -> Auth2ApiCommand:
    return Auth2ApiCommand(
        cwd=config.root,
        args=[
            config.npm_bin,
            "run",
            "image",
            "--",
            "--out",
            str(out_dir.resolve()),
            prompt,
        ],
    )


def run_auth2api_image(
    command: Auth2ApiCommand,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> Optional[Path]:
    completed = runner(
        command.args,
        cwd=str(command.cwd),
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    image_lines = [
        line.strip()
        for line in (completed.stdout or "").splitlines()
        if line.strip().lower().endswith(".png")
    ]
    if not image_lines:
        return None
    return Path(image_lines[-1])


def _unique_run_dir(runs_dir: Path, label: str) -> Path:
    candidate = runs_dir / label
    if not candidate.exists():
        return candidate
    suffix = 2
    while True:
        candidate = runs_dir / f"{label}-{suffix}"
        if not candidate.exists():
            return candidate
        suffix += 1


def _with_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"
