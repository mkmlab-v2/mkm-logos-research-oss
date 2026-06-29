#!/usr/bin/env python3
"""Export MKM Universal Root 1-page executive summary (print HTML) to PDF."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "docs/final/artifacts/mkm_universal_root_executive_summary_1p_print.html"
PDF = ROOT / "docs/final/artifacts/mkm_universal_root_executive_summary_1p_latest.pdf"
MANIFEST = ROOT / "docs/final/artifacts/mkm_universal_root_executive_summary_1p_latest.json"
DOWNLOADS_COPY = Path.home() / "Downloads" / "MKM_Universal_Root_Executive_Summary_1p.pdf"
MIN_PDF_BYTES = 4_000
MAX_PAGES = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _find_browser() -> Path:
    candidates = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    ]
    for p in candidates:
        if p.is_file():
            return p
    raise FileNotFoundError("Edge/Chrome not found for headless PDF export")


def _print_pdf(browser: Path, html_path: Path, pdf_path: Path) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    if pdf_path.exists():
        pdf_path.unlink()
    uri = html_path.resolve().as_uri()
    cmd = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=5000",
        f"--print-to-pdf={pdf_path.resolve()}",
        uri,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0 or not pdf_path.is_file():
        raise RuntimeError(
            f"PDF export failed exit={proc.returncode} stderr={proc.stderr[:500]!r}"
        )


def _validate_pdf(pdf_path: Path) -> dict[str, Any]:
    try:
        import pypdf
    except ImportError as exc:
        raise SystemExit("pypdf required: pip install pypdf") from exc
    reader = pypdf.PdfReader(str(pdf_path))
    pages = len(reader.pages)
    if pages < 1:
        raise SystemExit("pdf has zero pages")
    if pages > MAX_PAGES:
        raise SystemExit(f"expected 1 page executive summary, got {pages} pages")
    return {"pages": pages, "encrypted": reader.is_encrypted}


def _copy_to_downloads(pdf_path: Path) -> str:
    import shutil

    DOWNLOADS_COPY.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pdf_path, DOWNLOADS_COPY)
    return str(DOWNLOADS_COPY)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--html", type=Path, default=HTML)
    ap.add_argument("--pdf", type=Path, default=PDF)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--open", action="store_true")
    args = ap.parse_args()

    if not args.html.is_file():
        raise SystemExit(f"html missing: {args.html}")

    if args.dry_run:
        doc: dict[str, Any] = {
            "schema": "mkm_universal_root_executive_summary_1p_export_v1",
            "generated_at_utc": _utc_now(),
            "dry_run": True,
            "html": args.html.relative_to(ROOT).as_posix(),
            "pdf_target": args.pdf.relative_to(ROOT).as_posix(),
        }
        args.manifest.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "dry_run": True}, ensure_ascii=False))
        return 0

    browser = _find_browser()
    _print_pdf(browser, args.html, args.pdf)
    size_bytes = args.pdf.stat().st_size
    if size_bytes < MIN_PDF_BYTES:
        raise SystemExit(f"pdf too small: {size_bytes} bytes")

    validation = _validate_pdf(args.pdf)
    downloads_copy = _copy_to_downloads(args.pdf)

    doc = {
        "schema": "mkm_universal_root_executive_summary_1p_export_v1",
        "generated_at_utc": _utc_now(),
        "browser": browser.name,
        "html": args.html.relative_to(ROOT).as_posix(),
        "pdf": args.pdf.relative_to(ROOT).as_posix(),
        "md_source": "docs/research/MKM_UNIVERSAL_ROOT_EXECUTIVE_SUMMARY_1P_KO_V1.md",
        "size_kb": round(size_bytes / 1024, 1),
        "pages": validation["pages"],
        "downloads_copy": downloads_copy,
        "content_scope": "slide_04_06_fact_only",
        "send_gate": "HOLD",
        "repro": "py scripts/export_mkm_universal_root_executive_summary_1p_pdf_v1.py",
    }
    args.manifest.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "pdf": str(args.pdf),
                "pages": validation["pages"],
                "size_kb": doc["size_kb"],
                "downloads_copy": downloads_copy,
            },
            ensure_ascii=False,
        )
    )
    if args.open:
        subprocess.Popen([str(browser), str(args.pdf.resolve())], close_fds=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
