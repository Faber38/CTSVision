from __future__ import annotations

from paddleocr import PaddleOCR


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
