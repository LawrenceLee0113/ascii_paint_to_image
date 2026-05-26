import re
from dataclasses import dataclass


SGR_MOUSE_RE = re.compile(r"^\x1b\[<(\d+);(\d+);(\d+)([Mm])$")


@dataclass(frozen=True)
class SgrMouseEvent:
    button: int
    x: int
    y: int
    final: str

    @property
    def is_release(self) -> bool:
        return self.final == "m"

    @property
    def is_motion(self) -> bool:
        return bool(self.button & 32)

    @property
    def is_left(self) -> bool:
        return (self.button & 3) == 0


@dataclass(frozen=True)
class SubpixelPoint:
    cell_x: int
    cell_y: int
    subpixel_x: int
    subpixel_y: int

    def to_global(self, resolution: int) -> tuple:
        return self.cell_x * resolution + self.subpixel_x, self.cell_y * resolution + self.subpixel_y


def parse_sgr_mouse_event(sequence: str) -> SgrMouseEvent:
    match = SGR_MOUSE_RE.match(sequence)
    if not match:
        raise ValueError("Not a complete SGR mouse sequence")
    button, x, y, final = match.groups()
    return SgrMouseEvent(button=int(button), x=int(x), y=int(y), final=final)


def sgr_event_to_subpixel(
    event: SgrMouseEvent,
    coordinate_mode: str,
    terminal_columns: int,
    terminal_rows: int,
    cell_pixel_width: int,
    cell_pixel_height: int,
    resolution: int,
) -> tuple:
    mode = _resolve_coordinate_mode(event, coordinate_mode, terminal_columns, terminal_rows)
    if mode == "cell":
        return cell_to_subpixel(event.x, event.y, resolution), mode
    return (
        pixel_to_subpixel(
            pixel_x=event.x,
            pixel_y=event.y,
            cell_pixel_width=cell_pixel_width,
            cell_pixel_height=cell_pixel_height,
            resolution=resolution,
        ),
        mode,
    )


def cell_to_subpixel(cell_x: int, cell_y: int, resolution: int) -> SubpixelPoint:
    if resolution <= 0:
        raise ValueError("Resolution must be positive")
    return SubpixelPoint(
        cell_x=max(0, cell_x - 1),
        cell_y=max(0, cell_y - 1),
        subpixel_x=resolution // 2,
        subpixel_y=resolution // 2,
    )


def pixel_to_subpixel(
    pixel_x: int,
    pixel_y: int,
    cell_pixel_width: int,
    cell_pixel_height: int,
    resolution: int,
) -> SubpixelPoint:
    if cell_pixel_width <= 0 or cell_pixel_height <= 0:
        raise ValueError("Cell pixel dimensions must be positive")
    if resolution <= 0:
        raise ValueError("Resolution must be positive")
    zero_x = max(0, pixel_x - 1)
    zero_y = max(0, pixel_y - 1)
    cell_x = zero_x // cell_pixel_width
    cell_y = zero_y // cell_pixel_height
    local_x = zero_x % cell_pixel_width
    local_y = zero_y % cell_pixel_height
    return SubpixelPoint(
        cell_x=cell_x,
        cell_y=cell_y,
        subpixel_x=min(resolution - 1, local_x * resolution // cell_pixel_width),
        subpixel_y=min(resolution - 1, local_y * resolution // cell_pixel_height),
    )


def _resolve_coordinate_mode(
    event: SgrMouseEvent,
    coordinate_mode: str,
    terminal_columns: int,
    terminal_rows: int,
) -> str:
    if coordinate_mode not in ("auto", "pixel", "cell"):
        raise ValueError("coordinate_mode must be auto, pixel, or cell")
    if coordinate_mode != "auto":
        return coordinate_mode
    if event.x <= terminal_columns and event.y <= terminal_rows:
        return "cell"
    return "pixel"
