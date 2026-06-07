"""OCR engine wrapper: PaddleOCR (primary) + fallback support."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import numpy as np
from PIL import Image

from src.config import PADDLEOCR_MODELS_DIR, DEFAULT_LANG


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


class PaddleOcrEngine:
    """PaddleOCR engine với bundled models."""

    def __init__(self, lang: str = DEFAULT_LANG):
        self.lang = lang
        self.ocr = None
        self._loaded = False

    def _ensure_loaded(self):
        """Lazy init PaddleOCR (chỉ load khi cần)."""
        if self._loaded:
            return

        # Set model directory env var
        os.environ["PADDLEOCR_MODELS_DIR"] = str(PADDLEOCR_MODELS_DIR)

        try:
            from paddleocr import PaddleOCR

            # Kiểm tra model files có tồn tại không
            det_dir = os.path.join(PADDLEOCR_MODELS_DIR, "det")
            rec_dir = os.path.join(PADDLEOCR_MODELS_DIR, "rec")
            cls_dir = os.path.join(PADDLEOCR_MODELS_DIR, "cls")

            model_kwargs = {
                "lang": self.lang,
                "use_angle_cls": True,
                "show_log": False,
            }

            # Chỉ set custom model path nếu folder tồn tại
            if os.path.isdir(det_dir):
                model_kwargs["det_model_dir"] = det_dir
            if os.path.isdir(rec_dir):
                model_kwargs["rec_model_dir"] = rec_dir
            if os.path.isdir(cls_dir):
                model_kwargs["cls_model_dir"] = cls_dir

            self.ocr = PaddleOCR(**model_kwargs)
            self._loaded = True

        except ImportError:
            raise RuntimeError(
                "PaddleOCR not installed. "
                "Run: pip install paddlepaddle paddleocr"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load PaddleOCR: {e}")

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
        results = self.ocr.ocr(arr, cls=True)

        if not results or not results[0]:
            return OcrResult(blocks=[], full_text="", average_confidence=0.0)

        blocks = []
        all_text = []
        total_conf = 0.0

        for line in results[0]:
            bbox = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            text = line[1][0]  # Text content
            confidence = float(line[1][1])  # Confidence score

            # Convert float coords to int
            int_bbox = [[int(p[0]), int(p[1])] for p in bbox]

            block = OcrBlock(
                text=text,
                confidence=confidence,
                bbox=int_bbox,
            )
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
    """Fallback OCR using Tesseract.

    Dùng khi PaddleOCR không khả dụng.
    """

    def __init__(self, lang: str = "vie"):
        self.lang = lang
        self._available = None

    def is_available(self) -> bool:
        """Kiểm tra Tesseract có sẵn không."""
        if self._available is not None:
            return self._available

        try:
            import pytesseract
            # Try to find tesseract executable
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

        # Get detailed data
        data = pytesseract.image_to_data(
            image,
            lang=self.lang,
            output_type=pytesseract.Output.DICT,
        )

        blocks = []
        all_text = []
        total_conf = 0.0
        count = 0

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
                count += 1

        avg_conf = total_conf / count if count > 0 else 0.0

        return OcrResult(
            blocks=blocks,
            full_text=" ".join(all_text),
            average_confidence=avg_conf,
        )


def get_ocr_engine(lang: str = DEFAULT_LANG) -> PaddleOcrEngine | FallbackOcrEngine:
    """Factory: trả về OCR engine khả dụng nhất.

    Ưu tiên PaddleOCR, fallback sang Tesseract.
    """
    engine = PaddleOcrEngine(lang=lang)
    try:
        engine._ensure_loaded()
        return engine
    except RuntimeError:
        pass

    # Fallback to Tesseract
    fallback = FallbackOcrEngine()
    if fallback.is_available():
        return fallback

    raise RuntimeError(
        "No OCR engine available. "
        "Install paddleocr or tesseract."
    )


# Import cv2 cho grayscale conversion trong process()
import cv2
