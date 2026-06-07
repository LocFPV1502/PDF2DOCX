# PDF OCR Windows App

Convert scanned PDF to Word (.docx) using OCR with image processing.

## Features

- **PDF → Word**: Convert scanned PDF pages to editable Word documents
- **Text layer detection**: Automatically detect pages with text vs scanned pages
- **Image preprocessing**: Grayscale, denoise, OTSU threshold, deskew
- **OCR**: PaddleOCR (primary) with Tesseract fallback
- **Vietnamese + English**: Support both languages
- **Windows .exe**: Build standalone executable with PyInstaller

## Tech Stack

| Component | Technology |
|---|---|
| UI | Streamlit |
| OCR Engine | PaddleOCR (bundled models) |
| Image Processing | OpenCV |
| PDF Processing | pdf2image + pdfminer.six |
| DOCX Builder | python-docx |
| Packaging | PyInstaller |

---

## Build Windows .exe — Step by Step

### Prerequisites

| Yêu cầu | Link |
|---|---|
| Python 3.10 (64-bit) | https://www.python.org/downloads/release/python-31011/ |
| Visual C++ Redistributable | https://aka.ms/vs/17/release/vc_redist.x64.exe |
| Git | https://git-scm.com/download/win |

> **Lưu ý:** Python phải là version **3.10** (64-bit) vì PaddleOCR tương thích tốt nhất với version này. KHÔNG dùng Python 3.11+ hoặc 32-bit.

### Step 1: Clone project

```powershell
git clone git@github.com:LocFPV1502/PDF2DOCX.git
cd PDF2DOCX
```

### Step 2: Tạo virtualenv

```powershell
python -m venv venv
.\venv\Scripts\activate
```

### Step 3: Cài dependencies

```powershell
pip install -r requirements.txt
pip install pyinstaller
```

### Step 4: Download PaddleOCR models (1 lần duy nhất)

```powershell
# Lần đầu chạy sẽ tự download ~150MB models
# Models lưu tại: %USERPROFILE%\.paddleocr\
python -c "from paddleocr import PaddleOCR; PaddleOCR(lang='vi'); PaddleOCR(lang='en')"
```

### Step 5: Copy models vào project (để bundle vào .exe)

```powershell
# Tạo thư mục assets/ocr_models nếu chưa có
mkdir assets\ocr_models 2>nul

# Copy models
xcopy /E /I /Y "%USERPROFILE%\.paddleocr" "assets\ocr_models"
```

### Step 6: Chạy thử (verify)

```powershell
# Chạy Streamlit app
streamlit run app.py

# Hoặc dùng bootstrapper (tự mở browser)
python run.py
```

Mở browser: `http://localhost:8501`

### Step 7: Build .exe

```powershell
pyinstaller build.spec
```

Thời gian build: ~10-15 phút (lần đầu).

### Step 8: Kiểm tra kết quả

```
dist\OCR_PDF_Converter\
├── OCR_PDF_Converter.exe    (~1.2-1.5GB)
├── python310.dll
├── *.pyd, *.dll             (dependencies)
├── streamlit\static\        (Streamlit UI)
└── assets\ocr_models\       (PaddleOCR models, ~150MB)
```

### Step 9: Phân phối

Copy toàn bộ thư mục `dist\OCR_PDF_Converter\` sang máy đích.

**Yêu cầu máy đích:**
- Windows 10/11 64-bit
- Visual C++ Redistributable đã cài

**Chạy:** Double-click `OCR_PDF_Converter.exe` → tự mở browser → dùng bình thường.

---

## Troubleshooting

| Vấn đề | Giải pháp |
|---|---|
| `ModuleNotFoundError: No module named 'paddleocr'` | Chạy lại `pip install paddleocr` trong venv |
| `RuntimeError: PaddleOCR not installed` | Đảm bảo đã cài paddlepaddle + paddleocr |
| `poppler not found` | Cài poppler cho Windows hoặc dùng pdfminer thay thế |
| `.exe` quá lớn (>2GB) | Thêm `paddle*` vào `upx_exclude` trong build.spec |
| Streamlit không mở browser | Truy cập thủ công `http://localhost:8501` |
| PaddleOCR lỗi trên máy đích | Đảm bảo Visual C++ Redistributable đã cài |

---

## Project Structure

```
PDF2DOCX/
├── Agents.md               # Agent instructions
├── app.py                  # Streamlit UI
├── run.py                  # Bootstrapper
├── requirements.txt
├── build.spec              # PyInstaller config
├── README.md
├── src/
│   ├── __init__.py
│   ├── config.py           # Configuration constants
│   ├── pdf_processor.py    # PDF → images + text layer detection
│   ├── image_processor.py  # OpenCV preprocessing pipeline
│   ├── ocr_engine.py       # PaddleOCR + fallback wrapper
│   └── docx_builder.py     # DOCX generation
├── assets/
│   ├── ocr_models/         # Bundled PaddleOCR models (gitignored)
│   └── icon.ico
├── output/                 # Generated files (gitignored)
└── log_md/                 # Session logs
```

## Usage

1. Upload PDF file via drag & drop
2. Preview pages in **Preview** tab
3. Select language and preprocessing options in sidebar
4. Click **Start processing** in **Processing** tab
5. Download result in **Result** tab

## Limitations

- PaddleOCR bundle size: ~1.2-1.5GB (includes PaddlePaddle runtime)
- RAM usage: ~800MB-1.2GB during processing
- Vietnamese OCR accuracy: ~92-95% (depends on image quality)
- Large PDFs (>50 pages) may take several minutes to process
