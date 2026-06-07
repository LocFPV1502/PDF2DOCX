"""PDF processing: extract text layer, convert scanned pages to images."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from pdfminer.high_level import extract_text, extract_pages
from pdfminer.layout import LTTextContainer, LTFigure, LTImage
from pdf2image import convert_from_path
from PIL import Image

from src.config import DEFAULT_DPI


@dataclass
class PdfAnalysis:
    """Kết quả phân tích PDF."""
    total_pages: int
    has_text_layer: list[bool]
    text_content: list[Optional[str]]
    page_sizes: list[tuple[int, int]]  # (width, height) points
    scanned_pages: list[int]  # 0-indexed page numbers


@dataclass
class PageResult:
    """Kết quả xử lý 1 trang."""
    page_num: int
    text: Optional[str] = None
    has_text: bool = False
    image: Optional[Image.Image] = None


def analyze_pdf(pdf_path: str) -> PdfAnalysis:
    """Phân tích PDF: detect trang nào có text layer.

    Args:
        pdf_path: Đường dẫn file PDF.

    Returns:
        PdfAnalysis object.
    """
    pdf_path = str(pdf_path)

    # Extract text cho từng trang
    all_text = []
    has_text = []
    page_num = 0

    for page_layout in extract_pages(pdf_path):
        page_text_parts = []
        has_text_layer = False

        for element in page_layout:
            if isinstance(element, LTTextContainer):
                text = element.get_text().strip()
                if text:
                    page_text_parts.append(text)
                    has_text_layer = True

        full_text = "\n".join(page_text_parts).strip()
        all_text.append(full_text if full_text else None)
        has_text.append(has_text_layer)
        page_num += 1

        # Get page size
        if hasattr(page_layout, 'width') and hasattr(page_layout, 'height'):
            pass  # handled below

    # Get page sizes using convert_from_path (lightweight pass)
    page_sizes = _get_page_sizes(pdf_path, page_num)

    total_pages = page_num
    scanned_pages = [i for i, h in enumerate(has_text) if not h]

    return PdfAnalysis(
        total_pages=total_pages,
        has_text_layer=has_text,
        text_content=all_text,
        page_sizes=page_sizes,
        scanned_pages=scanned_pages,
    )


def extract_text_pages(pdf_path: str) -> list[Optional[str]]:
    """Extract text content từ PDF, trả về list text cho từng trang.

    Args:
        pdf_path: Đường dẫn file PDF.

    Returns:
        List of text strings. None nếu trang không có text layer.
    """
    pages_text = []

    for page_layout in extract_pages(pdf_path):
        page_text_parts = []

        for element in page_layout:
            if isinstance(element, LTTextContainer):
                text = element.get_text().strip()
                if text:
                    page_text_parts.append(text)

        full_text = "\n".join(page_text_parts).strip()
        pages_text.append(full_text if full_text else None)

    return pages_text


def pdf_to_images(
    pdf_path: str,
    dpi: int = DEFAULT_DPI,
    pages: Optional[list[int]] = None,
) -> list[Image.Image]:
    """Convert PDF pages to PIL Images (chỉ cho scanned pages).

    Args:
        pdf_path: Đường dẫn file PDF.
        dpi: DPI cho output images.
        pages: Danh sách trang cần convert (0-indexed). None = tất cả.

    Returns:
        List PIL Images.
    """
    # pdf2image dùng 1-indexed
    first_page = (pages[0] + 1) if pages else None
    last_page = (pages[-1] + 1) if pages else None

    images = convert_from_path(
        pdf_path,
        dpi=dpi,
        fmt="jpeg",
        first_page=first_page,
        last_page=last_page,
    )

    # Nếu chỉ request 1 vài trang, filter lại
    if pages and len(pages) > 1:
        # pdf2image trả về từ first_page đến last_page
        # cần filter đúng các trang được yêu cầu
        start = pages[0]
        filtered = []
        for i, img in enumerate(images):
            page_idx = start + i
            if page_idx in pages:
                filtered.append(img)
        return filtered

    return images


def _get_page_sizes(pdf_path: str, num_pages: int) -> list[tuple[int, int]]:
    """Lấy kích thước từng trang (width, height) points."""
    sizes = []
    for page_layout in extract_pages(pdf_path):
        if hasattr(page_layout, 'width') and hasattr(page_layout, 'height'):
            sizes.append((int(page_layout.width), int(page_layout.height)))
        else:
            sizes.append((612, 792))  # Default A4 size
    return sizes


def get_page_thumbnail(
    pdf_path: str,
    page_num: int,
    dpi: int = 72,
) -> Optional[Image.Image]:
    """Tạo thumbnail cho 1 trang PDF.

    Args:
        pdf_path: Đường dẫn file PDF.
        page_num: Số trang (0-indexed).
        dpi: DPI cho thumbnail (thấp hơn = nhanh hơn).

    Returns:
        PIL Image hoặc None nếu lỗi.
    """
    try:
        images = convert_from_path(
            pdf_path,
            dpi=dpi,
            first_page=page_num + 1,
            last_page=page_num + 1,
        )
        return images[0] if images else None
    except Exception:
        return None


def get_all_thumbnails(
    pdf_path: str,
    dpi: int = 72,
) -> list[Image.Image]:
    """Tạo thumbnails cho tất cả trang PDF."""
    return convert_from_path(pdf_path, dpi=dpi, fmt="jpeg")
