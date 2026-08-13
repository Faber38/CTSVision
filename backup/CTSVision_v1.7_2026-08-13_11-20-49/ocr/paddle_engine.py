from __future__ import annotations

import os
from pathlib import Path

# Paddle/oneDNN vor dem Import von PaddleOCR begrenzen.
# Das reduziert die Gefahr von Speicherzugriffsfehlern bei
# mehreren OCR-Aufrufen innerhalb desselben Programmlaufs.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("FLAGS_use_mkldnn", "0")

from PIL import Image
from paddleocr import PaddleOCR

from .models import OCRBox, OCRLine, OCRResult


class PaddleEngine:

    def __init__(self) -> None:

        print("OCR: Lade PaddleOCR...")

        self.ocr = PaddleOCR(
            lang="en",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            cpu_threads=1,
        )

        print("OCR: bereit.")

    def read_image(
        self,
        image: str | Path | Image.Image,
    ) -> OCRResult:
        """
        Liest den kompletten Text eines Bildes.
        """

        result = self.ocr.predict(image)

        lines: list[OCRLine] = []

        texts: list[str] = []

        confidences: list[float] = []

        if not result:
            return OCRResult()

        prediction = result[0]

        rec_texts = prediction.get("rec_texts", [])
        rec_scores = prediction.get("rec_scores", [])
        rec_polys = prediction.get("rec_polys", [])

        for index, (text, score) in enumerate(zip(rec_texts, rec_scores)):
            text = str(text).strip()
            score = float(score)

            box: OCRBox | None = None

            if index < len(rec_polys):
                polygon = rec_polys[index]

                xs = [int(point[0]) for point in polygon]

                ys = [int(point[1]) for point in polygon]

                left = min(xs)
                right = max(xs)
                top = min(ys)
                bottom = max(ys)

                box = OCRBox(
                    x=left,
                    y=top,
                    width=right - left,
                    height=bottom - top,
                )

            lines.append(
                OCRLine(
                    text=text,
                    confidence=score,
                    box=box,
                )
            )

            texts.append(text)
            confidences.append(score)

        confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return OCRResult(
            text="\n".join(texts),
            confidence=confidence,
            lines=lines,
        )
