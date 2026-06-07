"""Application configuration constants."""

import os

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# PaddleOCR bundled models path
# Khi build PyInstaller, set env PADDLEOCR_MODELS_DIR trước khi import
PADDLEOCR_MODELS_DIR = os.environ.get(
    "PADDLEOCR_MODELS_DIR",
    os.path.join(ASSETS_DIR, "ocr_models"),
)

# --- PDF Processing ---
DEFAULT_DPI = 300
SUPPORTED_FORMATS = ["pdf"]

# --- Image Processing ---
PIPELINE_OPTIONS = ["full", "light", "deskew_only", "none"]
DEFAULT_PIPELINE = "full"

# --- OCR ---
OCR_LANGUAGES = ["vi", "en", "auto"]
DEFAULT_LANG = "vi"

# --- DOCX Output ---
DEFAULT_OUTPUT_FORMAT = "docx"

# --- Streamlit ---
STREAMLIT_PORT = 8501
STREAMLIT_HOST = "localhost"
