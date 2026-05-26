from typing import Dict, List, Tuple

from ascii_paint_to_image.surface import DENSITY_RAMP, VxAsciiSurface


COLOR_NAMES = {
    1: "black",
    2: "red",
    3: "green",
    4: "blue",
    5: "yellow",
    6: "magenta",
    7: "cyan",
    8: "white",
}


def ascii_text_from_surface(surface: VxAsciiSurface) -> str:
    rows = [
        "".join(surface.char_at(x, y) for x in range(surface.width))
        for y in range(surface.height)
    ]
    active_rows = [index for index, row in enumerate(rows) if row.strip()]
    if not active_rows:
        return ""
    top = active_rows[0]
    bottom = active_rows[-1]
    active_columns = [
        x
        for x in range(surface.width)
        if any(rows[y][x] != " " for y in range(top, bottom + 1))
    ]
    left = active_columns[0]
    right = active_columns[-1]
    return "\n".join(row[left : right + 1].rstrip() for row in rows[top : bottom + 1])


def analyze_surface(surface: VxAsciiSurface) -> Dict[str, object]:
    cells: List[Tuple[int, int, str, float]] = []
    colors = set()
    for y in range(surface.height):
        for x in range(surface.width):
            char = surface.char_at(x, y)
            coverage = surface.coverage_at(x, y)
            if char == " " and coverage < 0.004:
                continue
            cells.append((x, y, char, coverage))
            color = surface.color_at(x, y)
            if color is not None:
                colors.add(COLOR_NAMES.get(color, f"color-{color}"))

    ascii_text = ascii_text_from_surface(surface)
    coverage = sum(cell[3] for cell in cells) / max(1, surface.width * surface.height)
    active_regions = _active_regions(cells, surface.width, surface.height)
    stroke_hints = _stroke_hints(cells)
    density_summary = _density_summary(cells)
    bbox = _bounding_box(cells)

    return {
        "canvas": {"width": surface.width, "height": surface.height},
        "ramp": surface.ascii_ramp,
        "ascii": ascii_text,
        "coverage": round(coverage, 4),
        "active_cell_count": len(cells),
        "bounding_box": bbox,
        "active_regions": active_regions,
        "stroke_hints": stroke_hints,
        "density": density_summary,
        "colors": sorted(colors),
    }


def build_prompt(analysis: Dict[str, object]) -> str:
    ascii_text = str(analysis.get("ascii") or "").strip() or "(blank canvas)"
    regions = ", ".join(analysis.get("active_regions", [])) or "no dominant region"
    strokes = ", ".join(analysis.get("stroke_hints", [])) or "soft scattered marks"
    colors = ", ".join(analysis.get("colors", [])) or "monochrome"
    density = analysis.get("density", {})
    bbox = analysis.get("bounding_box", {})
    return "\n".join(
        [
            "Create a PNG image from this pure text analysis of a terminal ASCII drawing.",
            "Do not treat this as an uploaded image; no image pixels were provided.",
            f"ASCII density ramp, from light to dark: {analysis.get('ramp', DENSITY_RAMP)}",
            f"Canvas size: {analysis.get('canvas')}. Active bounding box: {bbox}.",
            f"Overall ink coverage: {analysis.get('coverage')}. Active regions: {regions}.",
            f"Stroke and brush hints: {strokes}. Foreground color hints: {colors}.",
            f"Density summary: {density}.",
            "Interpret empty space as negative space and darker ASCII characters as stronger visual weight.",
            "If the drawing is abstract or does not clearly depict a subject, generate an abstract image guided by composition, weight, rhythm, and contrast rather than inventing a literal object.",
            "ASCII snapshot:",
            ascii_text,
        ]
    )


def build_simple_ascii_prompt(ascii_text: str, ascii_ramp: str = DENSITY_RAMP) -> str:
    sketch = ascii_text.strip("\n") or "(blank canvas)"
    return "\n".join(
        [
            "Use the ASCII sketch directly as the source drawing for image generation.",
            "Infer the most likely visible subject from the ASCII outline itself.",
            f"ASCII density ramp from light to dark: {ascii_ramp}",
            "Treat darker characters as stronger ink and empty spaces as intentional negative space.",
            "Preserve the overall silhouette, proportions, and composition from the ASCII sketch.",
            "Generate a clean, recognizable image of what the ASCII sketch appears to depict.",
            "ASCII sketch:",
            sketch,
        ]
    )


def _bounding_box(cells: List[Tuple[int, int, str, float]]) -> Dict[str, int]:
    if not cells:
        return {}
    xs = [cell[0] for cell in cells]
    ys = [cell[1] for cell in cells]
    return {
        "left": min(xs),
        "top": min(ys),
        "right": max(xs),
        "bottom": max(ys),
        "width": max(xs) - min(xs) + 1,
        "height": max(ys) - min(ys) + 1,
    }


def _active_regions(cells: List[Tuple[int, int, str, float]], width: int, height: int) -> List[str]:
    if not cells:
        return []
    regions = {}
    for x, y, _char, coverage in cells:
        col = min(2, int(x * 3 / max(1, width)))
        row = min(2, int(y * 3 / max(1, height)))
        name = (
            ("top", "middle", "bottom")[row]
            + "-"
            + ("left", "center", "right")[col]
        )
        regions[name] = regions.get(name, 0.0) + coverage
    threshold = max(regions.values()) * 0.35
    return sorted(name for name, score in regions.items() if score >= threshold)


def _stroke_hints(cells: List[Tuple[int, int, str, float]]) -> List[str]:
    chars = {cell[2] for cell in cells}
    hints = []
    if "-" in chars:
        hints.append("horizontal")
    if "|" in chars:
        hints.append("vertical")
    if "/" in chars or "\\" in chars:
        hints.append("diagonal")
    if any(char in "#8%&@" for char in chars):
        hints.append("heavy brush weight")
    if any(char in ".,':-=" for char in chars):
        hints.append("light sketch marks")
    return hints


def _density_summary(cells: List[Tuple[int, int, str, float]]) -> Dict[str, object]:
    if not cells:
        return {"average": 0.0, "darkest": " ", "lightest": " "}
    chars = [cell[2] for cell in cells]
    ramp_positions = [
        DENSITY_RAMP.index(char)
        for char in chars
        if char in DENSITY_RAMP
    ]
    average = sum(cell[3] for cell in cells) / max(1, len(cells))
    darkest = max(chars, key=lambda char: DENSITY_RAMP.index(char) if char in DENSITY_RAMP else 0)
    lightest = min(chars, key=lambda char: DENSITY_RAMP.index(char) if char in DENSITY_RAMP else 0)
    return {
        "average": round(average, 4),
        "average_ramp_index": round(sum(ramp_positions) / max(1, len(ramp_positions)), 2),
        "darkest": darkest,
        "lightest": lightest,
    }
