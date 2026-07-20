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

    for line in result.lines:
        print(f"{line.confidence:.3f}   {line.text}")


if __name__ == "__main__":
    main()
