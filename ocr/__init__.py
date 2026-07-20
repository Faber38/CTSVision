"""
OCR-Modul für CTSVision.
"""

from .paddle_engine import PaddleEngine
from .models import OCRResult, OCRLine

__all__ = [
    "PaddleEngine",
    "OCRResult",
    "OCRLine",
]
