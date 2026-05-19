#!/usr/bin/env python3
"""Regenerate OpenData 327 Part B/C HTML and PDF via headless Edge/Chrome."""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MERGE_GUIDE = ROOT / "docs/final/artifacts/opendata_327_submission_pdf_merge_guide_v1_latest.json"
REPORTS = ROOT / "reports"

STRIP_HEADINGS = ("(부록) 우선 준비", "변경 이력")


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


def _strip_md(text: str) -> str:
    lines: list[str] = []
    skip = False
    for line in text.splitlines():
        if any(h in line for h in STRIP_HEADINGS):
            skip = True
            continue
        if skip and line.startswith("## ") and not any(h in line for h in STRIP_HEADINGS):
            skip = False
        if skip:
            continue
        if "제출 시 삭제" in line or "파란색 안내" in line:
            continue
        lines.append(line)
    return "\n".join(lines).strip() + "\n"


def _md_to_html(md_text: str, title: str) -> str:
    body = html.escape(md_text)
    return (
        "<!DOCTYPE html><html><head><meta charset=utf-8>"
        f"<title>{html.escape(title)}</title></head><body>"
        '<pre style="white-space:pre-wrap;font-family:Malgun Gothic,Segoe UI,sans-serif;'
        f'font-size:11pt;line-height:1.45">{body}</pre></body></html>'
    )


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
        f"--print-to-pdf={pdf_path.resolve()}",
        uri,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0 or not pdf_path.is_file():
        raise RuntimeError(
            f"PDF export failed exit={proc.returncode} stderr={proc.stderr[:500]!r}"
        )


def _export_part(
    *,
    browser: Path,
    source_md: Path,
    html_out: Path,
    pdf_out: Path,
    title: str,
) -> dict[str, Any]:
    md = _strip_md(source_md.read_text(encoding="utf-8"))
    html_out.parent.mkdir(parents=True, exist_ok=True)
    html_out.write_text(_md_to_html(md, title), encoding="utf-8")
    _print_pdf(browser, html_out, pdf_out)
    size_kb = round(pdf_out.stat().st_size / 1024, 1)
    return {
        "source_md": source_md.relative_to(ROOT).as_posix(),
        "html": html_out.relative_to(ROOT).as_posix(),
        "pdf": pdf_out.relative_to(ROOT).as_posix(),
        "size_kb": size_kb,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-part-c", action="store_true")
    args = ap.parse_args()

    guide = json.loads(MERGE_GUIDE.read_text(encoding="utf-8"))
    part_b_md = ROOT / guide["merge_order"][1]["source_md"]
    part_c_md = ROOT / guide["merge_order"][2]["source_md"]

    browser = _find_browser()
    out: dict[str, Any] = {
        "schema": "opendata_327_pdf_export_v1",
        "generated_at_utc": _utc_now(),
        "browser": browser.name,
        "parts": [],
    }

    out["parts"].append(
        _export_part(
            browser=browser,
            source_md=part_b_md,
            html_out=REPORTS / "opendata_327_part_b_draft_v1.html",
            pdf_out=REPORTS / "opendata_327_part_b_v1.pdf",
            title="OpenData 327 Part B",
        )
    )
    merge_pdf = REPORTS / guide["output_target"]["filename_suggestion"]
    shutil.copy2(REPORTS / "opendata_327_part_b_v1.pdf", merge_pdf)
    out["part_b_pdf_merge_name"] = merge_pdf.relative_to(ROOT).as_posix()

    if not args.skip_part_c:
        out["parts"].append(
            _export_part(
                browser=browser,
                source_md=part_c_md,
                html_out=REPORTS / "opendata_327_part_c_draft_v1.html",
                pdf_out=REPORTS / "opendata_327_part_c_draft_v1.pdf",
                title="OpenData 327 Part C",
            )
        )

    summary_path = REPORTS / "opendata_327_pdf_export_latest.json"
    summary_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(summary_path), "parts": out["parts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
