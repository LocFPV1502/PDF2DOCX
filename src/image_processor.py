"""Image processing pipeline: grayscale, threshold, deskew, denoise."""

from __future__ import annotations

from typing import Literal

import cv2
import numpy as np
from PIL import Image

from src.config import DEFAULT_PIPELINE, PIPELINE_OPTIONS


def full_pipeline(img: Image.Image) -> Image.Image:
    """Pipeline đầy đủ cho scanned document.

    Steps:
        1. Grayscale
        2. Denoise (fastNlMeansDenoising)
        3. OTSU threshold (nhị phân hóa)
        4. Deskew (Hough Transform)
        5. Morphological cleanup

    Args:
        img: PIL Image input.

    Returns:
        PIL Image đã xử lý.
    """
    # Convert PIL → numpy array
    arr = np.array(img)

    # 1. Grayscale
    if len(arr.shape) == 3:
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    else:
        gray = arr.copy()

    # 2. Denoise
    denoised = cv2.fastNlMeansDenoising(gray, h=30)

    # 3. OTSU threshold
    _, binary = cv2.threshold(
        denoised, 0, 255,
        cv2.THRESH_BINARY | cv2.THRESH_OTSU,
    )

    # 4. Deskew
    deskewed = _deskew(binary)

    # 5. Morphological cleanup
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(deskewed, cv2.MORPH_CLOSE, kernel)

    return Image.fromarray(cleaned)


def light_pipeline(img: Image.Image) -> Image.Image:
    """Pipeline nhẹ: grayscale + OTSU threshold.

    Dùng khi input ảnh đã đẹp, chỉ cần nhị phân hóa.

    Args:
        img: PIL Image input.

    Returns:
        PIL Image đã xử lý.
    """
    arr = np.array(img)

    # Grayscale
    if len(arr.shape) == 3:
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    else:
        gray = arr.copy()

    # OTSU threshold
    _, binary = cv2.threshold(
        gray, 0, 255,
        cv2.THRESH_BINARY | cv2.THRESH_OTSU,
    )

    return Image.fromarray(binary)


def deskew_only(img: Image.Image) -> Image.Image:
    """Chỉ xoay lệch, không threshold.

    Args:
        img: PIL Image input.

    Returns:
        PIL Image đã xoay.
    """
    arr = np.array(img)

    if len(arr.shape) == 3:
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    else:
        gray = arr.copy()

    deskewed = _deskew(gray)
    return Image.fromarray(deskewed)


def no_processing(img: Image.Image) -> Image.Image:
    """Không xử lý, trả về nguyên bản."""
    return img.copy()


def preprocess(
    img: Image.Image,
    pipeline: str = DEFAULT_PIPELINE,
) -> Image.Image:
    """Process image theo pipeline được chọn.

    Args:
        img: PIL Image input.
        pipeline: Tên pipeline ("full", "light", "deskew_only", "none").

    Returns:
        PIL Image đã xử lý.

    Raises:
        ValueError: Nếu pipeline không hợp lệ.
    """
    if pipeline not in PIPELINE_OPTIONS:
        raise ValueError(
            f"Invalid pipeline '{pipeline}'. "
            f"Must be one of: {PIPELINE_OPTIONS}"
        )

    if pipeline == "full":
        return full_pipeline(img)
    elif pipeline == "light":
        return light_pipeline(img)
    elif pipeline == "deskew_only":
        return deskew_only(img)
    else:  # "none"
        return no_processing(img)


def _deskew(gray: np.ndarray) -> np.ndarray:
    """Xoay ảnh để thẳng hàng bằng Hough Transform.

    Args:
        gray: Grayscale numpy array.

    Returns:
        Deskewed grayscale numpy array.
    """
    # Edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    # Hough lines
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=200)

    if lines is None:
        return gray

    # Calculate median angle
    angles = []
    for line in lines:
        rho, theta = line[0]
        angle_deg = np.degrees(theta) - 90
        # Chỉ lấy góc nhỏ (gần 0 hoặc gần 180)
        if abs(angle_deg) < 30 or abs(angle_deg - 180) < 30:
            angles.append(angle_deg)

    if not angles:
        return gray

    median_angle = np.median(angles)

    # Skip if angle is very small (< 0.5 degree)
    if abs(median_angle) < 0.5:
        return gray

    # Rotate
    (h, w) = gray.shape
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)

    # Calculate new bounding box to avoid cropping
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])
    new_w = int(h * sin + w * cos)
    new_h = int(h * cos + w * sin)
    M[0, 2] += (new_w - w) / 2
    M[1, 2] += (new_h - h) / 2

    rotated = cv2.warpAffine(
        gray, M, (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )

    return rotated
