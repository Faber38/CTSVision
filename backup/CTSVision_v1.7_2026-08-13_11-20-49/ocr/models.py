from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class OCRBox:
    """
    Rechteckiger Bereich einer erkannten Textzeile.
    """

    x: int
    y: int
    width: int
    height: int

    @property
    def left(self) -> int:
        return self.x

    @property
    def top(self) -> int:
        return self.y

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def center_x(self) -> int:
        return self.x + self.width // 2

    @property
    def center_y(self) -> int:
        return self.y + self.height // 2


@dataclass(slots=True)
class OCRLine:
    text: str
    confidence: float
    box: OCRBox | None = None


@dataclass(slots=True)
class OCRResult:
    text: str = ""
    confidence: float = 0.0
    lines: list[OCRLine] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return bool(self.text.strip())

    def find_line(
        self,
        search_text: str,
    ) -> OCRLine | None:
        """
        Sucht eine erkannte Textzeile ohne Beachtung
        der Groß- und Kleinschreibung.
        """

        needle = search_text.strip().casefold()

        for line in self.lines:
            if needle in line.text.casefold():
                return line

        return None
