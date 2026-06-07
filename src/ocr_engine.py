"""OCR engine wrapper: EasyOCR (primary) + PaddleOCR/Tesseract fallback."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import numpy as np
import cv2
from PIL import Image

from src.config import DEFAULT_LANG


@dataclass
class OcrBlock:
    """Một block text từ OCR."""
    text: str
    confidence: float
    bbox: list[list[int]]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]


@dataclass
class OcrResult:
    """Kết quả OCR cho 1 trang."""
    blocks: list[OcrBlock]
    full_text: str
    average_confidence: float


class EasyOcrEngine:
    """EasyOCR engine — ổn định, hỗ trợ vi+en, auto-download models."""

    def __init__(self, lang: str = DEFAULT_LANG):
        self.lang = lang
        self.reader = None
        self._loaded = False

    def _ensure_loaded(self):
        """Lazy init EasyOCR (chỉ load khi cần)."""
        if self._loaded:
            return

        try:
            import easyocr

            # Map language codes
            lang_list = []
            if self.lang in ("vi", "auto"):
                lang_list.append("vi")
            if self.lang in ("en", "auto"):
                lang_list.append("en")
            if not lang_list:
                lang_list = ["en"]

            self.reader = easyocr.Reader(
                lang_list,
                gpu=False,
                verbose=False,
            )
            self._loaded = True

        except ImportError:
            raise RuntimeError(
                "EasyOCR not installed. "
                "Run: pip install easyocr"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load EasyOCR: {e}")

    def process(self, image: Image.Image) -> OcrResult:
        """OCR 1 ảnh.

        Args:
            image: PIL Image (grayscale hoặc RGB).

        Returns:
            OcrResult với blocks, text, confidence.
        """
        self._ensure_loaded()

        # Convert to numpy array
        arr = np.array(image)

        # Convert grayscale to RGB nếu cần
        if len(arr.shape) == 2:
            arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB)

        # Run OCR
        results = self.reader.readtext(arr)

        blocks = []
        all_text = []
        total_conf = 0.0

        for (bbox, text, confidence) in results:
            if text.strip():
                # EasyOCR bbox: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                int_bbox = [[int(p[0]), int(p[1])] for p in bbox]
                block = OcrBlock(text=text, confidence=confidence, bbox=int_bbox)
                blocks.append(block)
                all_text.append(text)
                total_conf += confidence

        avg_conf = total_conf / len(blocks) if blocks else 0.0

        # Sort blocks by vertical position (top-to-bottom), then left
        blocks.sort(key=lambda b: (b.bbox[0][1], b.bbox[0][0]))

        return OcrResult(
            blocks=blocks,
            full_text="\n".join(b.text for b in blocks),
            average_confidence=avg_conf,
        )


class FallbackOcrEngine:
    """Fallback OCR using Tesseract."""

    def __init__(self, lang: str = "vie"):
        self.lang = lang
        self._available = None

    def is_available(self) -> bool:
        """Kiểm tra Tesseract có sẵn không."""
        if self._available is not None:
            return self._available

        try:
            import pytesseract
            if os.name == "nt":  # Windows
                common_paths = [
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                ]
                for p in common_paths:
                    if os.path.exists(p):
                        pytesseract.pytesseract.tesseract_cmd = p
                        break
            self._available = True
        except (ImportError, Exception):
            self._available = False

        return self._available

    def process(self, image: Image.Image) -> OcrResult:
        """OCR using Tesseract."""
        if not self.is_available():
            raise RuntimeError("Tesseract not available")

        import pytesseract

        data = pytesseract.image_to_data(
            image,
            lang=self.lang,
            output_type=pytesseract.Output.DICT,
        )

        blocks = []
        all_text = []
        total_conf = 0.0

        for i in range(len(data["text"])):
            text = data["text"][i].strip()
            conf = float(data["conf"][i])

            if text and conf > 0:
                bbox = [
                    [data["left"][i], data["top"][i]],
                    [data["left"][i] + data["width"][i], data["top"][i]],
                    [data["left"][i] + data["width"][i], data["top"][i] + data["height"][i]],
                    [data["left"][i], data["top"][i] + data["height"][i]],
                ]
                block = OcrBlock(text=text, confidence=conf / 100.0, bbox=bbox)
                blocks.append(block)
                all_text.append(text)
                total_conf += conf / 100.0

        avg_conf = total_conf / len(blocks) if blocks else 0.0

        return OcrResult(
            blocks=blocks,
            full_text=" ".join(all_text),
            average_confidence=avg_conf,
        )


def get_ocr_engine(lang: str = DEFAULT_LANG):
    """Factory: trả về OCR engine khả dụng nhất.

    Ưu tiên EasyOCR, fallback sang Tesseract.
    """
    # Try EasyOCR first
    try:
        engine = EasyOcrEngine(lang=lang)
        engine._ensure_loaded()
        return engine
    except Exception as e:
        print(f"[OCR] EasyOCR failed: {e}")

    # Fallback to Tesseract
    try:
        fallback = FallbackOcrEngine()
        if fallback.is_available():
            return fallback
    except Exception as e:
        print(f"[OCR] Tesseract fallback failed: {e}")

    raise RuntimeError(
        "No OCR engine available. "
        "Install easyocr: pip install easyocr"
    )
