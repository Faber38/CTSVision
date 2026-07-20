from __future__ import annotations

from pathlib import Path

from PIL import Image
from paddleocr import PaddleOCR

from .models import OCRLine, OCRResult


class PaddleEngine:

    def __init__(self) -> None:

        print("OCR: Lade PaddleOCR...")

        self.ocr = PaddleOCR(
            lang="en",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
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

        for text, score in zip(rec_texts, rec_scores):

            text = str(text).strip()

            score = float(score)

            lines.append(
                OCRLine(
                    text=text,
                    confidence=score,
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
