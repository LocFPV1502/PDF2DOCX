# Agents Instructions — PDF OCR Windows App

## 1. Bắt buộc đọc file này

Mỗi lần bắt đầu phiên làm việc, **phải đọc toàn bộ file `Agents.md`** trước khi làm bất kỳ việc gì khác.

---

## 2. Pipeline dự án

Đây là thứ tự các bước xây dựng ứng dụng. **Phải tuân thủ đúng thứ tự.** Không được nhảy cóc.

| Bước | Module/File | Mô tả |
|---|---|---|
| 1 | `requirements.txt` | Ghi toàn bộ dependencies |
| 2 | `src/__init__.py` | Package init (empty OK) |
| 3 | `src/config.py` | Constants: paths, DPI, pipeline options |
| 4 | `src/pdf_processor.py` | PDF → ảnh + detect text layer (pdfminer + pdf2image) |
| 5 | `src/image_processor.py` | OpenCV pipeline: grayscale → OTSU → deskew → denoise |
| 6 | `src/ocr_engine.py` | PaddleOCR wrapper + bundled model path + Windows.Media.Ocr fallback |
| 7 | `src/docx_builder.py` | python-docx: build file .docx từ text + OCR results |
| 8 | `app.py` | Streamlit UI: upload, preview, progress, download |
| 9 | `run.py` | Bootstrapper: start streamlit server + mở browser |
| 10 | `build.spec` | PyInstaller config để build .exe cho Windows |
| 11 | `README.md` | Hướng dẫn cài đặt và build |
| 12 | Build & test | Build .exa và chạy thử trên Windows |

Mỗi bước phải hoàn thành và được xác nhận (bởi user hoặc agent tự kiểm tra) trước khi chuyển sang bước tiếp theo.

---

## 3. Quy tắc làm việc

### 3.1 Trước khi code

- Nếu có ý kiến khác với pipeline trên (sửa thứ tự, thay đổi công nghệ, thêm bước, v.v.), **phải hỏi người dùng trước khi triển khai**.
- Nếu phát hiện vấn đề trong code đã viết (bug, thiếu chức năng, không tương thích), hãy ghi vào log và hỏi user hướng xử lý.

### 3.2 Trong khi code

- **Không được xóa, sửa, hoặc đổi tên file `Agents.md`** trừ khi người dùng cho phép rõ ràng.
- Code theo đúng cấu trúc thư mục đã định.
- Tuân thủ các quyết định đã thống nhất với user (PaddleOCR bundle model, Streamlit, PyInstaller, v.v.).
- Nếu cần thêm file ngoài pipeline, hỏi user trước.

### 3.3 Sau khi kết thúc phiên làm việc

Luôn ghi log vào thư mục `log_md/` với định dạng:

```
log_md/YYYY-MM-DD_HH-MM.md
```

Nội dung log gồm:

```markdown
# Log: YYYY-MM-DD HH:MM

## Agent
- Tên / loại agent: [ví dụ: Claude Code, GPT-4, ...]
- Phiên bản: [nếu có]

## Công việc đã làm
- [file đã tạo/sửa] Mô tả ngắn
- ...

## Pipeline status
- Bước đã hoàn thành: [vd: 1-4]
- Bước hiện tại: [vd: 5]
- Bước tiếp theo: [vd: 6]

## Quyết định / thay đổi (nếu có)
- [mô tả quyết định đã hỏi user và kết quả]

## Vấn đề còn tồn đọng
- [nếu có]
```

---

## 4. Cấu trúc thư mục (đã thống nhất)

```
pdf_ocr_app/
├── Agents.md
├── app.py
├── run.py
├── requirements.txt
├── build.spec
├── README.md
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── pdf_processor.py
│   ├── image_processor.py
│   ├── ocr_engine.py
│   └── docx_builder.py
├── assets/
│   ├── icon.ico
│   └── ocr_models/       # PaddleOCR models (bundled, copy từ ~/.paddleocr/)
├── output/                # Temp files (gitignored)
├── log_md/                # Session logs
└── .gitignore
```

---

## 5. Tech stack (đã thống nhất)

| Thành phần | Công nghệ |
|---|---|
| UI | Streamlit (web UI, browser localhost) |
| OCR Engine | PaddleOCR (model bundled sẵn, accuracy ~92-95% VI) |
| Fallback OCR | Windows.Media.Ocr (trên Win 10/11) |
| Image Processing | OpenCV (grayscale → OTSU → deskew → denoise) |
| PDF → Ảnh | pdf2image + poppler-utils |
| Text layer detection | pdfminer.six |
| DOCX Builder | python-docx |
| Packaging | PyInstaller → folder .exe (~1.2-1.5GB) |
| Target OS | Windows 10/11 64-bit |

---

## 6. Lưu ý kỹ thuật

- `paddlepaddle==2.6.1` (CPU only, không GPU)
- PaddleOCR models: bundle từ `%USERPROFILE%\.paddleocr\`, set env `PADDLEOCR_MODELS_DIR`
- `pdf2image` cần poppler DLLs trên Windows — bundle vào `assets/poppler/`
- Streamlit chạy qua `subprocess` từ `run.py`
- Ẩn console Windows: PyInstaller `console=False`
