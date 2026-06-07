"""Streamlit UI for PDF OCR Converter."""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

import streamlit as st
from PIL import Image

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import (
    OUTPUT_DIR,
    DEFAULT_DPI,
    DEFAULT_LANG,
    DEFAULT_PIPELINE,
    PIPELINE_OPTIONS,
    OCR_LANGUAGES,
)
from src.pdf_processor import analyze_pdf, pdf_to_images, get_all_thumbnails
from src.image_processor import preprocess
from src.ocr_engine import get_ocr_engine, OcrResult
from src.docx_builder import build_docx


# --- Page config ---
st.set_page_config(
    page_title="PDF OCR Converter",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Cài đặt")

    lang = st.selectbox(
        "Ngôn ngữ OCR",
        options=OCR_LANGUAGES,
        index=OCR_LANGUAGES.index(DEFAULT_LANG),
        format_func=lambda x: {"vi": "Tiếng Việt", "en": "English", "auto": "Auto-detect"}[x],
    )

    pipeline = st.selectbox(
        "Image preprocessing",
        options=PIPELINE_OPTIONS,
        index=PIPELINE_OPTIONS.index(DEFAULT_PIPELINE),
        format_func=lambda x: {
            "full": "Full (grayscale + denoise + threshold + deskew)",
            "light": "Light (grayscale + threshold)",
            "deskew_only": "Deskew only",
            "none": "None",
        }[x],
    )

    include_images = st.checkbox(
        "Chèn ảnh gốc vào DOCX",
        value=False,
        help="Nếu bật, mỗi trang sẽ có cả ảnh gốc + text OCR",
    )

    st.divider()
    st.markdown(
        "**PDF OCR Converter**\n\n"
        "Convert scanned PDF to Word with OCR.\n\n"
        "Engine: PaddleOCR | UI: Streamlit"
    )


# --- Main ---
st.title("📄 PDF → Word OCR Converter")
st.markdown("Upload file PDF, hệ thống sẽ xử lý OCR và tạo file Word.")

# File uploader
uploaded_file = st.file_uploader(
    "Chọn file PDF",
    type=["pdf"],
    help="Hỗ trợ PDF text layer + scanned pages",
)

if uploaded_file is not None:
    # Save uploaded file to temp
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        pdf_path = tmp.name

    try:
        # --- Tab 1: Preview ---
        tab1, tab2, tab3 = st.tabs(["📋 Preview", "⚙️ Xử lý", "📥 Kết quả"])

        with tab1:
            st.subheader("Thông tin PDF")

            # Analyze PDF
            with st.spinner("Đang phân tích PDF..."):
                analysis = analyze_pdf(pdf_path)

            col1, col2, col3 = st.columns(3)
            col1.metric("Tổng số trang", analysis.total_pages)
            col2.metric("Trang có text", len(analysis.has_text_layer) - len(analysis.scanned_pages))
            col3.metric("Trang scanned (OCR)", len(analysis.scanned_pages))

            # Show page breakdown
            if analysis.scanned_pages:
                st.info(
                    f"Cần OCR: trang {', '.join(str(p+1) for p in analysis.scanned_pages)}"
                )
            else:
                st.success("Tất cả trang đều có text layer — không cần OCR.")

            # Thumbnails
            st.subheader("Preview trang")
            with st.spinner("Đang tạo thumbnails..."):
                thumbnails = get_all_thumbnails(pdf_path, dpi=72)

            # Display thumbnails in grid
            cols_per_row = 4
            for row_start in range(0, len(thumbnails), cols_per_row):
                cols = st.columns(cols_per_row)
                for i, col in enumerate(cols):
                    idx = row_start + i
                    if idx < len(thumbnails):
                        with col:
                            label = f"Trang {idx + 1}"
                            if idx in analysis.scanned_pages:
                                label += " 🔍 (OCR)"
                            else:
                                label += " ✅"
                            st.image(thumbnails[idx], caption=label, use_container_width=True)

        # --- Tab 2: Processing ---
        with tab2:
            st.subheader("Xử lý PDF → Word")

            if st.button("▶️ Bắt đầu xử lý", type="primary", use_container_width=True):
                # Create output dir
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                output_filename = f"{Path(uploaded_file.name).stem}_ocr.docx"
                output_path = os.path.join(OUTPUT_DIR, output_filename)

                progress_bar = st.progress(0, text="Khởi tạo...")
                status_area = st.empty()
                log_area = st.empty()

                start_time = time.time()
                logs = []

                def update_progress(pct: float, text: str, log_msg: str = ""):
                    progress_bar.progress(pct, text=text)
                    if log_msg:
                        logs.append(log_msg)
                        log_area.code("\n".join(logs[-20:]), language=None)

                try:
                    # Step 1: Analyze
                    update_progress(0.05, "Đang phân tích PDF...", "[1/5] Phân tích PDF...")
                    analysis = analyze_pdf(pdf_path)

                    # Step 2: Extract text for text-layer pages
                    update_progress(0.15, "Đang trích xuất text layer...", "[2/5] Trích xuất text layer...")
                    text_pages = [None] * analysis.total_pages
                    from src.pdf_processor import extract_text_pages
                    extracted_texts = extract_text_pages(pdf_path)
                    for i, text in enumerate(extracted_texts):
                        if text:
                            text_pages[i] = text
                            update_progress(
                                0.15 + 0.1 * (i / analysis.total_pages),
                                f"Trang {i+1}: tìm thấy text layer",
                                f"  → Trang {i+1}: text layer OK ({len(text)} chars)",
                            )

                    # Step 3: Convert scanned pages to images
                    scanned_images = []
                    if analysis.scanned_pages:
                        update_progress(0.3, "Đang convert scanned pages → ảnh...", "[3/5] Convert scanned pages...")
                        scanned_images = pdf_to_images(
                            pdf_path,
                            dpi=DEFAULT_DPI,
                            pages=analysis.scanned_pages,
                        )
                        for i, img in enumerate(scanned_images):
                            page_num = analysis.scanned_pages[i]
                            update_progress(
                                0.3 + 0.1 * (i / len(scanned_images)),
                                f"Trang {page_num+1}: convert xong",
                                f"  → Trang {page_num+1}: converted to {img.size[0]}x{img.size[1]}",
                            )

                    # Step 4: OCR
                    ocr_results: dict[int, OcrResult] = {}
                    if scanned_images:
                        update_progress(0.5, "Đang OCR...", "[4/5] OCR processing...")
                        engine = get_ocr_engine(lang=lang if lang != "auto" else "vi")
                        for i, img in enumerate(scanned_images):
                            page_num = analysis.scanned_pages[i]
                            update_progress(
                                0.5 + 0.3 * (i / len(scanned_images)),
                                f"Trang {page_num+1}: OCR đang xử lý...",
                                f"  → Trang {page_num+1}: OCR...",
                            )

                            # Preprocess
                            processed_img = preprocess(img, pipeline=pipeline)

                            # OCR
                            result = engine.process(processed_img)
                            ocr_results[page_num] = result

                            update_progress(
                                0.5 + 0.3 * ((i + 1) / len(scanned_images)),
                                f"Trang {page_num+1}: OCR xong",
                                f"  → Trang {page_num+1}: {len(result.blocks)} blocks, conf={result.average_confidence:.1%}",
                            )

                    # Step 5: Build DOCX
                    update_progress(0.85, "Đang tạo file Word...", "[5/5] Tạo DOCX...")
                    build_docx(
                        text_pages=text_pages,
                        ocr_results=ocr_results,
                        output_path=output_path,
                        source_images=scanned_images if analysis.scanned_pages else None,
                        include_images=include_images,
                    )

                    elapsed = time.time() - start_time
                    update_progress(1.0, f"Hoàn thành! ({elapsed:.1f}s)", f"[DONE] Tổng thời gian: {elapsed:.1f}s")

                    # Save to session state for download tab
                    st.session_state["output_path"] = output_path
                    st.session_state["output_filename"] = output_filename
                    st.session_state["elapsed"] = elapsed
                    st.session_state["analysis"] = analysis
                    st.session_state["ocr_results"] = ocr_results

                    st.success(f"✅ Hoàn thành trong {elapsed:.1f}s!")

                except Exception as e:
                    st.error(f"❌ Lỗi: {e}")
                    import traceback
                    st.code(traceback.format_exc())

        # --- Tab 3: Result ---
        with tab3:
            st.subheader("Kết quả")

            if "output_path" in st.session_state:
                output_path = st.session_state["output_path"]
                output_filename = st.session_state["output_filename"]
                elapsed = st.session_state["elapsed"]
                analysis = st.session_state["analysis"]
                ocr_results = st.session_state["ocr_results"]

                col1, col2 = st.columns(2)
                col1.metric("Thời gian xử lý", f"{elapsed:.1f}s")
                col2.metric("Số trang", analysis.total_pages)

                # OCR stats
                if ocr_results:
                    avg_conf = sum(r.average_confidence for r in ocr_results.values()) / len(ocr_results)
                    st.metric("OCR Confidence TB", f"{avg_conf:.1%}")

                # Download button
                with open(output_path, "rb") as f:
                    st.download_button(
                        label="📥 Tải file Word",
                        data=f.read(),
                        file_name=output_filename,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        type="primary",
                        use_container_width=True,
                    )
            else:
                st.info("Chưa có kết quả. Vui lòng xử lý trước ở tab '⚙️ Xử lý'.")

    finally:
        # Cleanup temp file
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)

else:
    # Welcome screen
    st.info("👆 Upload file PDF để bắt đầu.")

    st.markdown("---")
    st.markdown(
        """
        ### Hướng dẫn sử dụng
        1. Upload file PDF vào ô phía trên
        2. Xem preview ở tab **Preview**
        3. Chọn cài đặt ở sidebar (ngôn ngữ, preprocessing)
        4. Click **Bắt đầu xử lý** ở tab **Xử lý**
        5. Tải kết quả ở tab **Kết quả**

        ### Hỗ trợ
        - PDF text layer: trích xuất text trực tiếp (nhanh)
        - PDF scanned: OCR với PaddleOCR (chậm hơn)
        - Tiếng Việt + English
        """
    )
