from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


@dataclass(frozen=True)
class TemplateMatchResult:
    """Ergebnis einer Template-Suche."""

    similarity: float
    x: int
    y: int


def find_template(
    template_path: Path,
    search_image: Image.Image,
) -> TemplateMatchResult:
    """
    Sucht ein Referenzbild innerhalb eines größeren Suchbildes.

    Rückgabe:
        TemplateMatchResult:
            - similarity: Ähnlichkeit zwischen 0.0 und 1.0
            - x: Position des besten Treffers im Suchbild
            - y: Position des besten Treffers im Suchbild
    """

    if not template_path.exists():
        raise FileNotFoundError(f"Referenzbild nicht gefunden: {template_path}")

    template_pil = Image.open(template_path).convert("RGB")
    search_pil = search_image.convert("RGB")

    if template_pil.width > search_pil.width or template_pil.height > search_pil.height:
        raise ValueError("Das Referenzbild darf nicht größer als der Suchbereich sein.")

    template_rgb = np.array(template_pil)
    search_rgb = np.array(search_pil)

    template_gray = cv2.cvtColor(
        template_rgb,
        cv2.COLOR_RGB2GRAY,
    )
    search_gray = cv2.cvtColor(
        search_rgb,
        cv2.COLOR_RGB2GRAY,
    )

    # Leicht glätten, damit kleine Beleuchtungsunterschiede
    # und Bildrauschen weniger Einfluss haben.
    template_blurred = cv2.GaussianBlur(
        template_gray,
        (3, 3),
        0,
    )
    search_blurred = cv2.GaussianBlur(
        search_gray,
        (3, 3),
        0,
    )

    template_gray = cv2.cvtColor(
        template_rgb,
        cv2.COLOR_RGB2GRAY,
    )
    search_gray = cv2.cvtColor(
        search_rgb,
        cv2.COLOR_RGB2GRAY,
    )

    result = cv2.matchTemplate(
        search_gray,
        template_gray,
        cv2.TM_CCOEFF_NORMED,
    )

    _, max_similarity, _, max_location = cv2.minMaxLoc(result)

    match_x, match_y = max_location

    return TemplateMatchResult(
        similarity=float(max_similarity),
        x=int(match_x),
        y=int(match_y),
    )
