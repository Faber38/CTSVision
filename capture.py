from pathlib import Path

from PIL import Image, ImageGrab
from window_finder import WindowInfo


def capture_region(
    x: int,
    y: int,
    width: int,
    height: int,
    output_path: Path | None = None,
) -> Image.Image:
    """Capture a rectangular desktop region.

    If output_path is supplied, the image is also saved.
    """

    if width <= 0 or height <= 0:
        raise ValueError("Breite und Höhe müssen größer als 0 sein.")

    box = (
        x,
        y,
        x + width,
        y + height,
    )

    image = ImageGrab.grab(bbox=box)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)

    return image


def capture_window_region(
    window: WindowInfo,
    x: int,
    y: int,
    width: int,
    height: int,
    output_path: Path | None = None,
) -> Image.Image:
    """Nimmt einen Ausschnitt relativ zum Elite-Fenster auf."""

    desktop_x = window.x + x
    desktop_y = window.y + y
    print(
        f"Capture: Desktop=({desktop_x},{desktop_y}) "
        f"Window=({window.x},{window.y}) "
        f"Rel=({x},{y})"
    )

    return capture_region(
        x=desktop_x,
        y=desktop_y,
        width=width,
        height=height,
        output_path=output_path,
    )
