from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class OCRLine:
    text: str
    confidence: float


@dataclass(slots=True)
class OCRResult:
    text: str = ""
    confidence: float = 0.0
    lines: list[OCRLine] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return bool(self.text.strip())
