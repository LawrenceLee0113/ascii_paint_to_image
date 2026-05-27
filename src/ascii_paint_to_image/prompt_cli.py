import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from ascii_paint_to_image.app import DEFAULT_AUTH2API_ROOT
from ascii_paint_to_image.runs import (
    Auth2ApiConfig,
    RunBackup,
    build_auth2api_command,
    create_run_backup,
    default_npm_bin,
    run_auth2api_image,
)


@dataclass(frozen=True)
class PromptGenerationResult:
    run: RunBackup
    prompt: str
    image_path: Optional[Path]


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an image from a text prompt through auth2api."
    )
    parser.add_argument("prompt", nargs="*", help="text prompt to send to image generation")
    parser.add_argument("--prompt-file", help="read the prompt from a text file")
    parser.add_argument("--runs-dir", default="runs")
    parser.add_argument("--auth2api-root", default=DEFAULT_AUTH2API_ROOT)
    parser.add_argument("--npm-bin", default=default_npm_bin())
    parser.add_argument("--dry-run", action="store_true", help="write backups but do not call auth2api")
    parser.add_argument(
        "--now-label",
        help="override the run directory timestamp label; mainly useful for repeatable automation",
    )
    return parser.parse_args(argv)


def prompt_from_args(args: argparse.Namespace) -> str:
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text()
    elif args.prompt:
        prompt = " ".join(args.prompt)
    elif not sys.stdin.isatty():
        prompt = sys.stdin.read()
    else:
        raise ValueError("provide a prompt argument, --prompt-file, or piped stdin")

    prompt = prompt.strip()
    if not prompt:
        raise ValueError("prompt must not be empty")
    return prompt


def generate_from_prompt(
    prompt: str,
    runs_dir: Path,
    dry_run: bool,
    auth2api_root: Path,
    npm_bin: str,
    now_label: Optional[str] = None,
    runner: Optional[Callable[..., object]] = None,
) -> PromptGenerationResult:
    run = create_run_backup(
        runs_dir=runs_dir,
        ascii_text="",
        analysis={"mode": "prompt", "source": "ai-image"},
        prompt=prompt,
        now_label=now_label,
    )
    image_path = None
    if not dry_run:
        command = build_auth2api_command(
            Auth2ApiConfig(root=auth2api_root, npm_bin=npm_bin),
            run.path,
            prompt,
        )
        if runner is None:
            image_path = run_auth2api_image(command)
        else:
            image_path = run_auth2api_image(command, runner=runner)
    return PromptGenerationResult(run=run, prompt=prompt, image_path=image_path)


def main(argv: Optional[List[str]] = None) -> int:
    try:
        args = parse_args(argv)
        result = generate_from_prompt(
            prompt=prompt_from_args(args),
            runs_dir=Path(args.runs_dir),
            dry_run=args.dry_run,
            auth2api_root=Path(args.auth2api_root),
            npm_bin=args.npm_bin,
            now_label=args.now_label,
        )
    except Exception as err:
        print("ai-image: " + str(err), file=sys.stderr)
        return 1

    print(result.run.path)
    print(result.run.prompt_path)
    if result.image_path is not None:
        print(result.image_path)
    elif args.dry_run:
        print("dry-run: auth2api was not called")
    return 0
