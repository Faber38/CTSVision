from __future__ import annotations

import sys

from ocr import PaddleEngine


def main():

    if len(sys.argv) != 2:
        print("Aufruf:")
        print()
        print("python -m ocr.ocr_test bild.png")
        return

    engine = PaddleEngine()

    result = engine.read_image(sys.argv[1])

    print()
    print("========== OCR ==========")
    print()

    print("Gesamter Text:")
    print("----------------")
    print(result.text)

    print()

    print(f"Konfidenz: {result.confidence:.3f}")

    print()

    print("Einzelne Zeilen")
    print("----------------")

    for line in result.lines:

        print(f"{line.confidence:.3f}   {line.text}")

        if line.box is not None:
            print(
                f"    Box: "
                f"x={line.box.x} "
                f"y={line.box.y} "
                f"w={line.box.width} "
                f"h={line.box.height} "
                f"center=({line.box.center_x}, {line.box.center_y})"
            )

    print()

    tritium = result.find_line("TRITIUM")

    if tritium is not None:
        print("TRITIUM gefunden")

        if tritium.box is not None:
            print(f"Y-Mittelpunkt: {tritium.box.center_y}")
    else:
        print("TRITIUM nicht gefunden")


if __name__ == "__main__":
    main()
