#!/usr/bin/env python3
"""PDF text extraction with OCR fallback (B-track, research_only).

Backends (in auto order): pdfminer.six → pymupdf text layer → rapidocr-onnxruntime.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any

MIN_TEXT_CHARS_DEFAULT = 80


def _extract_pdfminer(path: Path) -> str:
    from pdfminer.high_level import extract_text

    return (extract_text(str(path)) or "").strip()


def _extract_pymupdf(path: Path) -> str:
    import fitz

    doc = fitz.open(str(path))
    try:
        return "\n".join((doc[i].get_text() or "") for i in range(len(doc))).strip()
    finally:
        doc.close()


def _extract_rapidocr(
    path: Path,
    *,
    max_pages: int | None = None,
    dpi_scale: float = 2.0,
) -> str:
    import fitz
    from rapidocr_onnxruntime import RapidOCR

    ocr = RapidOCR()
    doc = fitz.open(str(path))
    page_count = len(doc)
    limit = page_count if max_pages is None else min(page_count, max_pages)
    chunks: list[str] = []
    matrix = fitz.Matrix(dpi_scale, dpi_scale)

    with tempfile.TemporaryDirectory(prefix="mkm_ocr_") as tmp:
        tmp_path = Path(tmp)
        for i in range(limit):
            pix = doc[i].get_pixmap(matrix=matrix)
            img = tmp_path / f"page_{i:04d}.png"
            pix.save(str(img))
            result, _ = ocr(str(img))
            if not result:
                continue
            page_text = " ".join(str(row[1]) for row in result if len(row) > 1)
            page_text = re.sub(r"\s+", " ", page_text).strip()
            if page_text:
                chunks.append(page_text)
    doc.close()
    return "\n\n".join(chunks).strip()


def extract_pdf_text(
    path: Path,
    *,
    backend: str = "auto",
    min_chars: int = MIN_TEXT_CHARS_DEFAULT,
    ocr_max_pages: int | None = 150,
) -> tuple[str, str]:
    """Return (text, backend_name). Raises RuntimeError if all backends fail."""
    path = path.resolve()
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"not a pdf: {path}")

    attempts: list[tuple[str, str]] = []

    if backend in {"auto", "pdfminer"}:
        try:
            text = _extract_pdfminer(path)
            attempts.append(("pdfminer.six", text))
            if len(text) >= min_chars:
                return text, "pdfminer.six"
        except Exception:
            pass

    if backend in {"auto", "pymupdf"}:
        try:
            text = _extract_pymupdf(path)
            attempts.append(("pymupdf", text))
            if len(text) >= min_chars:
                return text, "pymupdf"
        except Exception:
            pass

    if backend in {"auto", "rapidocr"}:
        try:
            text = _extract_rapidocr(path, max_pages=ocr_max_pages)
            attempts.append(("rapidocr-onnxruntime", text))
            if len(text) >= min_chars:
                return text, "rapidocr-onnxruntime"
        except ImportError as exc:
            raise RuntimeError(
                "rapidocr-onnxruntime required for scanned PDFs: pip install rapidocr-onnxruntime"
            ) from exc

    if attempts:
        best_backend, best_text = max(attempts, key=lambda x: len(x[1]))
        return best_text, best_backend

    raise RuntimeError(f"no text extracted from {path}")


def probe_pdf_backends(path: Path, *, ocr_max_pages: int = 2) -> dict[str, Any]:
    """Diagnostic: char counts per backend (for ops)."""
    out: dict[str, Any] = {"pdf": str(path)}
    for name, fn in (
        ("pdfminer.six", lambda: _extract_pdfminer(path)),
        ("pymupdf", lambda: _extract_pymupdf(path)),
        ("rapidocr-onnxruntime", lambda: _extract_rapidocr(path, max_pages=ocr_max_pages)),
    ):
        try:
            text = fn()
            out[name] = {"chars": len(text), "sample": text[:120]}
        except Exception as exc:  # noqa: BLE001
            out[name] = {"error": str(exc)}
    return out
