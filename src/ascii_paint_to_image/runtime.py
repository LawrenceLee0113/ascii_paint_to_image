import os
from typing import Optional, Tuple


def number_key_selection(number: int, selected_color: int, brush_size: int) -> Tuple[int, int]:
    return number, brush_size


def drawable_canvas_size(terminal_width: int, terminal_height: int) -> Tuple[int, int]:
    status_rows = 2
    return max(1, terminal_width), max(1, terminal_height - status_rows)


def terminal_size() -> Tuple[int, int]:
    size = os.get_terminal_size()
    return size.columns, size.lines


def consume_raw_input(buffer: str) -> Tuple[Optional[Tuple[str, str]], str]:
    if buffer.startswith("\x1b[<"):
        endings = [index for index in (buffer.find("M"), buffer.find("m")) if index != -1]
        if not endings:
            return None, buffer
        end = min(endings)
        sequence = buffer[: end + 1]
        return ("mouse", sequence), buffer[end + 1 :]
    return ("key", buffer[0]), buffer[1:]


def ansi_fg(color_id: Optional[int]) -> str:
    if color_id is None:
        return "\033[0m"
    color_codes = {
        1: 30,
        2: 31,
        3: 32,
        4: 34,
        5: 33,
        6: 35,
        7: 36,
        8: 37,
    }
    return "\033[{0}m".format(color_codes.get(color_id, 30))
