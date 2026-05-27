import argparse
import math
import os
import select
import sys
import termios
import time
import tty
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from ascii_paint_to_image.analysis import (
    analyze_surface,
    ascii_text_from_surface,
    build_prompt,
    build_simple_ascii_prompt,
)
from ascii_paint_to_image.history import SurfaceHistory
from ascii_paint_to_image.runs import (
    Auth2ApiConfig,
    RunBackup,
    build_auth2api_command,
    create_run_backup,
    default_npm_bin,
    run_auth2api_image,
)
from ascii_paint_to_image.runtime import (
    ansi_fg,
    consume_raw_input,
    drawable_canvas_size,
    number_key_selection,
    terminal_size,
)
from ascii_paint_to_image.sgr_mouse import parse_sgr_mouse_event, sgr_event_to_subpixel
from ascii_paint_to_image.surface import DENSITY_RAMP, VxAsciiSurface, ink_value_for_speed


DEFAULT_AUTH2API_ROOT = "/Users/lawrencelee0113/workspace/auth2api"


@dataclass(frozen=True)
class GenerationResult:
    run: RunBackup
    prompt: str
    image_path: Optional[Path]


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Draw ASCII in the terminal, analyze it as text, and generate an image through auth2api."
    )
    parser.add_argument("--runs-dir", default="runs")
    parser.add_argument("--auth2api-root", default=DEFAULT_AUTH2API_ROOT)
    parser.add_argument("--npm-bin", default=default_npm_bin())
    parser.add_argument("--char-resolution", type=int, default=9)
    parser.add_argument("--char-gamma", type=float, default=1.6)
    parser.add_argument("--char-ramp", default=DENSITY_RAMP)
    parser.add_argument("--brush-size", type=int, default=3)
    parser.add_argument("--pixel-cell-width", type=int, default=8)
    parser.add_argument("--pixel-cell-height", type=int, default=16)
    parser.add_argument("--sgr-coordinate-mode", choices=("auto", "pixel", "cell"), default="auto")
    parser.add_argument("--vx-fast-speed", type=float, default=24.0)
    parser.add_argument("--vx-min-ink", type=float, default=0.25)
    parser.add_argument("--demo", action="store_true", help="create a sample run without opening the UI")
    parser.add_argument("--dry-run", action="store_true", help="write backups but do not call auth2api")
    parser.add_argument(
        "--prompt-mode",
        choices=("analysis", "simple"),
        default="analysis",
        help="analysis uses derived text metrics; simple sends the raw ASCII sketch with minimal instructions",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    if args.demo:
        result = run_demo(
            runs_dir=Path(args.runs_dir),
            dry_run=args.dry_run,
            auth2api_root=Path(args.auth2api_root),
            npm_bin=args.npm_bin,
            char_resolution=args.char_resolution,
            char_gamma=args.char_gamma,
            char_ramp=args.char_ramp,
            prompt_mode=args.prompt_mode,
        )
        print(result.run.path)
        print(result.run.prompt_path)
        if result.image_path is not None:
            print(result.image_path)
        elif args.dry_run:
            print("dry-run: auth2api was not called")
        return 0
    return run_interactive(args)


def run_demo(
    runs_dir: Path,
    dry_run: bool,
    now_label: Optional[str] = None,
    auth2api_root: Path = Path(DEFAULT_AUTH2API_ROOT),
    npm_bin: str = "npm",
    char_resolution: int = 9,
    char_gamma: float = 1.6,
    char_ramp: str = DENSITY_RAMP,
    prompt_mode: str = "analysis",
) -> GenerationResult:
    surface = build_demo_surface(
        char_resolution=char_resolution,
        char_gamma=char_gamma,
        char_ramp=char_ramp,
    )
    return generate_from_surface(
        surface=surface,
        runs_dir=runs_dir,
        dry_run=dry_run,
        auth2api_config=Auth2ApiConfig(root=auth2api_root, npm_bin=npm_bin),
        now_label=now_label,
        prompt_mode=prompt_mode,
    )


def build_demo_surface(
    char_resolution: int = 9,
    char_gamma: float = 1.6,
    char_ramp: str = DENSITY_RAMP,
) -> VxAsciiSurface:
    surface = VxAsciiSurface(
        width=36,
        height=12,
        resolution=char_resolution,
        ascii_ramp=char_ramp,
        gamma=char_gamma,
    )
    mid_y = surface.resolution * 4 + surface.resolution // 2
    surface.paint_line_subpixels((surface.resolution * 2, mid_y), (surface.resolution * 33, mid_y), 1, color=4, value=0.45)
    surface.paint_line_subpixels((surface.resolution * 8, surface.resolution * 2), (surface.resolution * 27, surface.resolution * 9), 2, color=2, value=0.55)
    surface.paint_global_subpixel(surface.resolution * 18, surface.resolution * 5, 4, color=7, value=0.4)
    return surface


def generate_from_surface(
    surface: VxAsciiSurface,
    runs_dir: Path,
    dry_run: bool,
    auth2api_config: Auth2ApiConfig,
    now_label: Optional[str] = None,
    prompt_mode: str = "analysis",
) -> GenerationResult:
    if prompt_mode not in ("analysis", "simple"):
        raise ValueError("prompt_mode must be analysis or simple")
    ascii_text = ascii_text_from_surface(surface)
    if prompt_mode == "simple":
        analysis = {
            "mode": "simple-ascii",
            "ramp": surface.ascii_ramp,
            "ascii": ascii_text,
        }
        prompt = build_simple_ascii_prompt(ascii_text, surface.ascii_ramp)
    else:
        analysis = analyze_surface(surface)
        ascii_text = str(analysis["ascii"]) or ascii_text
        prompt = build_prompt(analysis)
    run = create_run_backup(
        runs_dir=runs_dir,
        ascii_text=ascii_text,
        analysis=analysis,
        prompt=prompt,
        now_label=now_label,
    )
    image_path = None
    if not dry_run:
        command = build_auth2api_command(auth2api_config, run.path, prompt)
        image_path = run_auth2api_image(command)
    return GenerationResult(run=run, prompt=prompt, image_path=image_path)


def run_interactive(args: argparse.Namespace) -> int:
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    terminal_width, terminal_height = terminal_size()
    surface_width, surface_height = drawable_canvas_size(terminal_width, terminal_height)
    surface = VxAsciiSurface(
        width=surface_width,
        height=surface_height,
        resolution=args.char_resolution,
        ascii_ramp=args.char_ramp,
        gamma=args.char_gamma,
    )
    mouse_is_down = False
    last_point: Optional[Tuple[int, int]] = None
    last_time: Optional[float] = None
    stroke_recorded = False
    brush_size = args.brush_size
    selected_color: Optional[int] = 2
    history = SurfaceHistory()
    resolved_coordinate_mode = args.sgr_coordinate_mode
    message = "q quit | z undo | y redo | 0 erase | g/i gen | c clear | 1-8 color"
    buffer = ""

    try:
        tty.setcbreak(fd)
        sys.stdout.write("\033[?1049h\033[?25l\033[?1003h\033[?1006h\033[?1016h")
        sys.stdout.flush()
        _render(surface, brush_size, selected_color, message, args.sgr_coordinate_mode, resolved_coordinate_mode)

        while True:
            terminal_width, terminal_height = terminal_size()
            surface_width, surface_height = drawable_canvas_size(terminal_width, terminal_height)
            surface.resize(surface_width, surface_height)
            readable, _, _ = select.select([sys.stdin], [], [], 0.05)
            if not readable:
                continue

            chunk = os.read(fd, 4096).decode("utf-8", errors="ignore")
            buffer += chunk
            while buffer:
                parsed, buffer = consume_raw_input(buffer)
                if parsed is None:
                    break
                kind, payload = parsed
                if kind == "key":
                    key = payload
                    if key in ("q", "Q"):
                        return 0
                    if key in ("c", "C"):
                        history.remember(surface)
                        surface.clear()
                        mouse_is_down = False
                        last_point = None
                        last_time = None
                        stroke_recorded = False
                        message = "Canvas cleared"
                    elif key in ("z", "Z"):
                        mouse_is_down = False
                        last_point = None
                        last_time = None
                        stroke_recorded = False
                        message = "Undo" if history.undo(surface) else "Nothing to undo"
                    elif key in ("y", "Y"):
                        mouse_is_down = False
                        last_point = None
                        last_time = None
                        stroke_recorded = False
                        message = "Redo" if history.redo(surface) else "Nothing to redo"
                    elif key in ("g", "G"):
                        try:
                            result = generate_from_surface(
                                surface=surface,
                                runs_dir=Path(args.runs_dir),
                                dry_run=args.dry_run,
                                auth2api_config=Auth2ApiConfig(
                                    root=Path(args.auth2api_root),
                                    npm_bin=args.npm_bin,
                                ),
                                prompt_mode="analysis",
                            )
                            if args.dry_run:
                                message = "Dry run saved " + str(result.run.prompt_path)
                            else:
                                message = "Generated " + str(result.image_path or result.run.path)
                        except Exception as err:
                            message = "Generate failed: " + str(err)
                    elif key in ("i", "I"):
                        try:
                            result = generate_from_surface(
                                surface=surface,
                                runs_dir=Path(args.runs_dir),
                                dry_run=args.dry_run,
                                auth2api_config=Auth2ApiConfig(
                                    root=Path(args.auth2api_root),
                                    npm_bin=args.npm_bin,
                                ),
                                prompt_mode="simple",
                            )
                            if args.dry_run:
                                message = "Simple dry run saved " + str(result.run.prompt_path)
                            else:
                                message = "Simple generated " + str(result.image_path or result.run.path)
                        except Exception as err:
                            message = "Simple generate failed: " + str(err)
                    elif key == "0":
                        selected_color = None
                        message = "eraser"
                    elif key in "12345678":
                        selected, brush_size = number_key_selection(
                            int(key),
                            selected_color or 2,
                            brush_size,
                        )
                        selected_color = selected
                        message = "color={0}".format(selected_color)
                elif kind == "mouse":
                    event = parse_sgr_mouse_event(payload)
                    if event.is_release:
                        mouse_is_down = False
                        last_point = None
                        last_time = None
                        stroke_recorded = False
                        continue
                    point, resolved_coordinate_mode = sgr_event_to_subpixel(
                        event=event,
                        coordinate_mode=args.sgr_coordinate_mode,
                        terminal_columns=terminal_width,
                        terminal_rows=terminal_height,
                        cell_pixel_width=args.pixel_cell_width,
                        cell_pixel_height=args.pixel_cell_height,
                        resolution=args.char_resolution,
                    )
                    if not (0 <= point.cell_x < surface.width and 0 <= point.cell_y < surface.height):
                        continue
                    global_point = point.to_global(args.char_resolution)
                    now = time.monotonic()
                    should_paint = event.is_left and (not event.is_motion or mouse_is_down)
                    if should_paint:
                        if not stroke_recorded:
                            history.remember(surface)
                            stroke_recorded = True
                        speed = 0.0
                        value = 1.0
                        if last_point is not None and last_time is not None and mouse_is_down:
                            distance = math.hypot(
                                global_point[0] - last_point[0],
                                global_point[1] - last_point[1],
                            )
                            elapsed = max(0.001, now - last_time)
                            speed = distance / max(1, args.char_resolution) / elapsed
                            value = ink_value_for_speed(speed, args.vx_fast_speed, args.vx_min_ink)
                            if selected_color is None:
                                surface.erase_line_subpixels(last_point, global_point, brush_size)
                            else:
                                surface.paint_line_subpixels(
                                    last_point,
                                    global_point,
                                    brush_size,
                                    color=selected_color,
                                    value=value,
                                )
                        else:
                            if selected_color is None:
                                surface.erase_global_subpixel(global_point[0], global_point[1], brush_size)
                            else:
                                surface.paint_global_subpixel(
                                    global_point[0],
                                    global_point[1],
                                    brush_size,
                                    color=selected_color,
                                    value=value,
                                )
                        mouse_is_down = True
                        last_point = global_point
                        last_time = now
                        tool = "eraser" if selected_color is None else "color={0}".format(selected_color)
                        message = "coord={0} cell=({1},{2}) speed={3:.1f} ink={4:.2f} {5}".format(
                            resolved_coordinate_mode,
                            point.cell_x,
                            point.cell_y,
                            speed,
                            value,
                            tool,
                        )
                _render(surface, brush_size, selected_color, message, args.sgr_coordinate_mode, resolved_coordinate_mode)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sys.stdout.write("\033[?1016l\033[?1006l\033[?1003l\033[?25h\033[?1049l")
        sys.stdout.flush()


def _render(
    surface: VxAsciiSurface,
    brush_size: int,
    selected_color: Optional[int],
    message: str,
    coordinate_mode: str,
    resolved_coordinate_mode: str,
) -> None:
    terminal_width, terminal_height = terminal_size()
    lines = [_row(surface, y, terminal_width) for y in range(surface.height)]
    status = (
        "ascii-paint-to-image coord={coord}/{resolved} "
        "tool={tool} brush={brush} canvas={width}x{height}"
    ).format(
        coord=coordinate_mode,
        resolved=resolved_coordinate_mode,
        tool="eraser" if selected_color is None else "color={0}".format(selected_color),
        brush=brush_size,
        width=surface.width,
        height=surface.height,
    )
    lines.append(status[:terminal_width])
    lines.append(message[:terminal_width])
    while len(lines) < terminal_height:
        lines.append("")
    sys.stdout.write("\033[H" + "\n".join("\033[2K" + line for line in lines[:terminal_height]))
    sys.stdout.flush()


def _row(surface: VxAsciiSurface, y: int, terminal_width: int) -> str:
    parts: List[str] = []
    current_color: Optional[int] = None
    for x in range(min(surface.width, terminal_width)):
        char = surface.char_at(x, y)
        color = surface.color_at(x, y) if char != " " else None
        if color != current_color:
            parts.append(ansi_fg(color))
            current_color = color
        parts.append(char)
    if current_color is not None:
        parts.append("\033[0m")
    return "".join(parts)


if __name__ == "__main__":
    raise SystemExit(main())
