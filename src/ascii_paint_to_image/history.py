from typing import List

from ascii_paint_to_image.surface import SurfaceSnapshot, VxAsciiSurface


class SurfaceHistory:
    def __init__(self, limit: int = 50) -> None:
        if limit <= 0:
            raise ValueError("history limit must be positive")
        self.limit = limit
        self._undo: List[SurfaceSnapshot] = []
        self._redo: List[SurfaceSnapshot] = []

    def remember(self, surface: VxAsciiSurface) -> None:
        self._undo.append(surface.snapshot())
        if len(self._undo) > self.limit:
            self._undo.pop(0)
        self._redo.clear()

    def undo(self, surface: VxAsciiSurface) -> bool:
        if not self._undo:
            return False
        self._redo.append(surface.snapshot())
        surface.restore(self._undo.pop())
        return True

    def redo(self, surface: VxAsciiSurface) -> bool:
        if not self._redo:
            return False
        self._undo.append(surface.snapshot())
        if len(self._undo) > self.limit:
            self._undo.pop(0)
        surface.restore(self._redo.pop())
        return True
