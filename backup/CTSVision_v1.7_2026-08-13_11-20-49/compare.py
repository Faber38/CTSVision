from pathlib import Path

from PIL import Image, ImageChops, ImageStat


def compare_images(
    reference_path: Path,
    current_image: Image.Image,
) -> float:
    """Vergleicht Referenzbild und aktuelles Bild.

    Rückgabe:
        Ähnlichkeit zwischen 0.0 und 1.0
    """

    if not reference_path.exists():
        raise FileNotFoundError(f"Referenzbild nicht gefunden: {reference_path}")

    reference = Image.open(reference_path).convert("RGB")
    current = current_image.convert("RGB")

    if current.size != reference.size:
        current = current.resize(reference.size)

    difference = ImageChops.difference(reference, current)
    statistics = ImageStat.Stat(difference)

    mean_difference = sum(statistics.mean) / len(statistics.mean)
    similarity = 1.0 - (mean_difference / 255.0)

    return max(0.0, min(1.0, similarity))
