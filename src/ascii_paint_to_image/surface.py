import math
from typing import List, Optional, Tuple


DENSITY_RAMP = " .',:-=+*oO#8%&@"


def _clamp(value: float) -> float:
    return min(1.0, max(0.0, value))


def ink_value_for_speed(speed: float, fast_speed: float, min_value: float) -> float:
    if fast_speed <= 0:
        raise ValueError("fast_speed must be positive")
    if not (0 < min_value <= 1):
        raise ValueError("min_value must be between 0 and 1")
    normalized = min(1.0, max(0.0, speed / fast_speed))
    return round(1.0 - normalized * (1.0 - min_value), 4)


class VxAsciiSurface:
    def __init__(
        self,
        width: int,
        height: int,
        resolution: int = 9,
        ascii_ramp: str = DENSITY_RAMP,
        gamma: float = 1.0,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("ASCII surface width and height must be positive")
        if resolution <= 0:
            raise ValueError("ASCII surface resolution must be positive")
        if not ascii_ramp:
            raise ValueError("ASCII ramp must not be empty")
        if gamma <= 0:
            raise ValueError("ASCII gamma must be positive")
        self.width = width
        self.height = height
        self.resolution = resolution
        self.ascii_ramp = ascii_ramp
        self.gamma = gamma
        self._ink: List[List[List[List[float]]]] = [
            [
                [[0.0 for _ in range(resolution)] for _ in range(resolution)]
                for _ in range(width)
            ]
            for _ in range(height)
        ]
        self._colors: List[List[Optional[int]]] = [
            [None for _ in range(width)] for _ in range(height)
        ]
        self._char_cache: List[List[Optional[str]]] = [
            [None for _ in range(width)] for _ in range(height)
        ]
        self._char_dirty: List[List[bool]] = [
            [True for _ in range(width)] for _ in range(height)
        ]

    def clear(self) -> None:
        for y, row in enumerate(self._ink):
            for x, block in enumerate(row):
                for subrow in block:
                    for sub_x in range(self.resolution):
                        subrow[sub_x] = 0.0
                self._colors[y][x] = None
                self._char_cache[y][x] = " "
                self._char_dirty[y][x] = False

    def resize(self, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("ASCII surface width and height must be positive")
        if width == self.width and height == self.height:
            return
        resized = [
            [
                [[0.0 for _ in range(self.resolution)] for _ in range(self.resolution)]
                for _ in range(width)
            ]
            for _ in range(height)
        ]
        resized_colors: List[List[Optional[int]]] = [
            [None for _ in range(width)] for _ in range(height)
        ]
        resized_cache: List[List[Optional[str]]] = [
            [" " for _ in range(width)] for _ in range(height)
        ]
        resized_dirty: List[List[bool]] = [
            [False for _ in range(width)] for _ in range(height)
        ]
        for y in range(min(self.height, height)):
            for x in range(min(self.width, width)):
                resized[y][x] = self._ink[y][x]
                resized_colors[y][x] = self._colors[y][x]
                resized_cache[y][x] = self._char_cache[y][x]
                resized_dirty[y][x] = self._char_dirty[y][x]
        self.width = width
        self.height = height
        self._ink = resized
        self._colors = resized_colors
        self._char_cache = resized_cache
        self._char_dirty = resized_dirty

    def fill_cell(
        self,
        cell_x: int,
        cell_y: int,
        value: float,
        color: Optional[int] = None,
    ) -> None:
        self._validate_cell(cell_x, cell_y)
        clamped = _clamp(value)
        for y in range(self.resolution):
            for x in range(self.resolution):
                self._ink[cell_y][cell_x][y][x] = clamped
        if color is not None:
            self._colors[cell_y][cell_x] = color
        self._mark_char_dirty(cell_x, cell_y)

    def paint_cell(
        self,
        cell_x: int,
        cell_y: int,
        radius: int,
        color: Optional[int] = None,
        value: float = 1.0,
    ) -> None:
        center = self.resolution // 2
        self.paint_global_subpixel(
            cell_x * self.resolution + center,
            cell_y * self.resolution + center,
            radius,
            color,
            value,
        )

    def paint_line_subpixels(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        radius: int,
        color: Optional[int] = None,
        value: float = 1.0,
    ) -> None:
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        steps = max(abs(dx), abs(dy), 1)
        for step in range(steps + 1):
            x = round(start[0] + dx * step / steps)
            y = round(start[1] + dy * step / steps)
            self.paint_global_subpixel(x, y, radius, color, value)

    def paint_global_subpixel(
        self,
        global_x: int,
        global_y: int,
        radius: int,
        color: Optional[int] = None,
        value: float = 1.0,
    ) -> None:
        radius = max(0, radius)
        clamped_value = _clamp(value)
        radius_squared = radius * radius
        for y in range(global_y - radius, global_y + radius + 1):
            for x in range(global_x - radius, global_x + radius + 1):
                if radius > 0 and (x - global_x) ** 2 + (y - global_y) ** 2 > radius_squared:
                    continue
                cell_x = x // self.resolution
                cell_y = y // self.resolution
                if not (0 <= cell_x < self.width and 0 <= cell_y < self.height):
                    continue
                local_x = x % self.resolution
                local_y = y % self.resolution
                self._ink[cell_y][cell_x][local_y][local_x] = min(
                    1.0,
                    self._ink[cell_y][cell_x][local_y][local_x] + clamped_value,
                )
                if color is not None:
                    self._colors[cell_y][cell_x] = color
                self._mark_char_dirty(cell_x, cell_y)

    def char_at(self, cell_x: int, cell_y: int) -> str:
        self._validate_cell(cell_x, cell_y)
        cached = self._char_cache[cell_y][cell_x]
        if cached is None or self._char_dirty[cell_y][cell_x]:
            cached = block_to_ascii_vx(
                self._ink[cell_y][cell_x],
                ascii_ramp=self.ascii_ramp,
                gamma=self.gamma,
            )
            self._char_cache[cell_y][cell_x] = cached
            self._char_dirty[cell_y][cell_x] = False
        return cached

    def color_at(self, cell_x: int, cell_y: int) -> Optional[int]:
        self._validate_cell(cell_x, cell_y)
        return self._colors[cell_y][cell_x]

    def coverage_at(self, cell_x: int, cell_y: int) -> float:
        self._validate_cell(cell_x, cell_y)
        block = self._ink[cell_y][cell_x]
        total = sum(sum(row) for row in block)
        return total / max(1, self.resolution * self.resolution)

    def _validate_cell(self, cell_x: int, cell_y: int) -> None:
        if not (0 <= cell_x < self.width and 0 <= cell_y < self.height):
            raise IndexError(f"Cell ({cell_x}, {cell_y}) is outside {self.width}x{self.height}")

    def _mark_char_dirty(self, cell_x: int, cell_y: int) -> None:
        self._char_dirty[cell_y][cell_x] = True


def block_to_ascii_vx(
    block: List[List[float]],
    ascii_ramp: str = DENSITY_RAMP,
    gamma: float = 1.0,
) -> str:
    if not ascii_ramp:
        raise ValueError("ASCII ramp must not be empty")
    if gamma <= 0:
        raise ValueError("ASCII gamma must be positive")
    height = len(block)
    width = len(block[0]) if height else 0
    total = sum(sum(row) for row in block)
    area = max(1, width * height)
    coverage = total / area
    if coverage < 0.004:
        return " "

    shape = _thin_axis_shape(block, total)
    if shape is not None:
        return shape

    slash_score = 0.0
    backslash_score = 0.0
    for y, row in enumerate(block):
        for x, value in enumerate(row):
            if value <= 0:
                continue
            slash_score += value / (1 + abs((width - 1 - x) - y))
            backslash_score += value / (1 + abs(x - y))

    if 0.035 <= coverage <= 0.32:
        if slash_score > backslash_score * 1.35:
            return "/"
        if backslash_score > slash_score * 1.35:
            return "\\"

    midpoint = max(1, width // 2)
    left = sum(sum(row[:midpoint]) for row in block)
    right = sum(sum(row[midpoint:]) for row in block)
    if coverage >= 0.18 and left > right * 1.4:
        return "%"

    adjusted_coverage = coverage ** gamma
    ramp_index = max(1, round(adjusted_coverage * (len(ascii_ramp) - 1)))
    return ascii_ramp[min(len(ascii_ramp) - 1, ramp_index)]


def _thin_axis_shape(block: List[List[float]], total: float) -> Optional[str]:
    if total <= 0:
        return None
    active = [
        (x, y)
        for y, row in enumerate(block)
        for x, value in enumerate(row)
        if value > 0.02
    ]
    if not active:
        return None
    xs = [point[0] for point in active]
    ys = [point[1] for point in active]
    x_span = max(xs) - min(xs) + 1
    y_span = max(ys) - min(ys) + 1
    width = len(block[0])
    height = len(block)
    row_sums = [sum(row) for row in block]
    col_sums = [sum(block[y][x] for y in range(height)) for x in range(width)]
    horizontal_strength = max(row_sums) / total
    vertical_strength = max(col_sums) / total

    if x_span >= math.ceil(width * 0.55) and y_span <= max(2, math.ceil(height * 0.34)):
        if horizontal_strength >= 0.45:
            return "-"
    if y_span >= math.ceil(height * 0.55) and x_span <= max(2, math.ceil(width * 0.34)):
        if vertical_strength >= 0.45:
            return "|"
    return None
