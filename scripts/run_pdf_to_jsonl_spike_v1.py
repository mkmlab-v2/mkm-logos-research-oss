#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.79, L:0.68, K:0.74, M:0.41}
# Balance: 85
# Purpose: Run OpenDataLoader PDF extraction and adapt output JSON into JSONL rows for local spike benchmarking.
# Keywords: pdf, opendataloader, jsonl, benchmark, local, spike
"""Run a local OpenDataLoader spike: PDF -> JSON/Markdown -> JSONL + benchmark report."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


def _safe_read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _extract_text_rows(node: Any, source_pdf: str, out: list[dict[str, Any]], page_hint: int | None = None) -> None:
    if isinstance(node, dict):
        local_page = page_hint
        for key in ("page", "page_number", "pageIndex", "page_idx", "page number"):
            v = node.get(key)
            if isinstance(v, int):
                local_page = v
                break
        text = node.get("text")
        if not (isinstance(text, str) and text.strip()):
            text = node.get("content")
        if isinstance(text, str) and text.strip():
            row: dict[str, Any] = {
                "schema": "pdf_spike_jsonl_v1",
                "source_pdf": source_pdf,
                "page": local_page,
                "text": text.strip(),
            }
            for key in ("type", "label", "role"):
                v = node.get(key)
                if isinstance(v, str) and v.strip():
                    row["element_type"] = v.strip()
                    break
            for key in ("bbox", "bounding_box", "box", "coordinates", "bounding box"):
                v = node.get(key)
                if isinstance(v, (dict, list)):
                    row["bbox"] = v
                    break
            out.append(row)
        for value in node.values():
            _extract_text_rows(value, source_pdf=source_pdf, out=out, page_hint=local_page)
    elif isinstance(node, list):
        for item in node:
            _extract_text_rows(item, source_pdf=source_pdf, out=out, page_hint=page_hint)


def _infer_json_outputs(output_dir: Path) -> list[Path]:
    return sorted(output_dir.rglob("*.json"))


def _infer_markdown_outputs(output_dir: Path) -> list[Path]:
    return sorted(output_dir.rglob("*.md"))


def _load_markdown_text(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""
    return text


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Spike runner: local OpenDataLoader parse + JSONL adapter + benchmark report.",
    )
    ap.add_argument(
        "--input-pdf",
        type=Path,
        nargs="+",
        required=True,
        help="One or more PDF paths to parse.",
    )
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=Path("tmp/pdf_spike_v1"),
        help="Base output directory for OpenDataLoader outputs.",
    )
    ap.add_argument(
        "--output-jsonl",
        type=Path,
        default=Path("tmp/pdf_spike_v1/pdf_spike_rows_latest.jsonl"),
        help="JSONL file adapted from parser JSON outputs.",
    )
    ap.add_argument(
        "--output-report",
        type=Path,
        default=Path("reports/pdf_spike_benchmark_v1_latest.json"),
        help="Benchmark report path.",
    )
    ap.add_argument(
        "--format",
        default="markdown,json",
        help="OpenDataLoader output format (default: markdown,json).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan only, do not call parser.",
    )
    ns = ap.parse_args()

    missing = [str(p) for p in ns.input_pdf if not p.is_file()]
    if missing:
        print(f"missing input PDF(s): {missing}", file=sys.stderr)
        return 1

    ns.output_dir.mkdir(parents=True, exist_ok=True)
    ns.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    ns.output_report.parent.mkdir(parents=True, exist_ok=True)

    started_at = time.time()
    convert_elapsed_s: float | None = None
    convert_mode = "dry_run" if ns.dry_run else "fast_local"

    if not ns.dry_run:
        try:
            import opendataloader_pdf  # type: ignore
        except Exception as exc:  # pragma: no cover
            print(
                "opendataloader_pdf import failed. Install with: py -m pip install -U opendataloader-pdf",
                file=sys.stderr,
            )
            print(f"import error: {exc}", file=sys.stderr)
            return 2

        c0 = time.time()
        opendataloader_pdf.convert(
            input_path=[str(p) for p in ns.input_pdf],
            output_dir=str(ns.output_dir),
            format=ns.format,
            quiet=True,
        )
        convert_elapsed_s = time.time() - c0

    json_outputs = _infer_json_outputs(ns.output_dir)
    md_outputs = _infer_markdown_outputs(ns.output_dir)
    rows: list[dict[str, Any]] = []
    rows_by_pdf: dict[str, int] = {}
    chars_by_pdf: dict[str, int] = {}
    element_type_histogram: dict[str, int] = {}
    parse_errors: list[str] = []

    for json_path in json_outputs:
        try:
            payload = _safe_read_json(json_path)
            source_pdf = json_path.stem + ".pdf"
            before = len(rows)
            _extract_text_rows(payload, source_pdf=source_pdf, out=rows)
            rows_by_pdf[source_pdf] = rows_by_pdf.get(source_pdf, 0) + (len(rows) - before)
        except Exception as exc:
            parse_errors.append(f"{json_path}: {exc}")

    # Fallback: if JSON extraction did not yield rows for a document,
    # use markdown body so downstream JSONL stages still receive text.
    for md_path in md_outputs:
        source_pdf = md_path.stem + ".pdf"
        if rows_by_pdf.get(source_pdf, 0) > 0:
            continue
        md_text = _load_markdown_text(md_path)
        if not md_text:
            continue
        rows.append(
            {
                "schema": "pdf_spike_jsonl_v1",
                "source_pdf": source_pdf,
                "page": None,
                "text": md_text,
                "element_type": "markdown_fallback",
            }
        )
        rows_by_pdf[source_pdf] = rows_by_pdf.get(source_pdf, 0) + 1

    for row in rows:
        source_pdf = str(row.get("source_pdf") or "")
        text = str(row.get("text") or "")
        et = str(row.get("element_type") or "unknown")
        if source_pdf:
            chars_by_pdf[source_pdf] = chars_by_pdf.get(source_pdf, 0) + len(text)
        element_type_histogram[et] = element_type_histogram.get(et, 0) + 1

    docs_summary: list[dict[str, Any]] = []
    for source_pdf in sorted(set(rows_by_pdf.keys()) | set(chars_by_pdf.keys())):
        n_rows = int(rows_by_pdf.get(source_pdf, 0))
        n_chars = int(chars_by_pdf.get(source_pdf, 0))
        docs_summary.append(
            {
                "source_pdf": source_pdf,
                "row_count": n_rows,
                "char_count": n_chars,
                "avg_chars_per_row": (n_chars / n_rows) if n_rows > 0 else 0.0,
            }
        )

    with ns.output_jsonl.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    total_elapsed_s = time.time() - started_at
    report = {
        "schema": "pdf_spike_benchmark_v1",
        "mode": convert_mode,
        "input_pdf_count": len(ns.input_pdf),
        "input_pdfs": [str(p.resolve()) for p in ns.input_pdf],
        "output_dir": str(ns.output_dir.resolve()),
        "json_output_count": len(json_outputs),
        "markdown_output_count": len(md_outputs),
        "jsonl_path": str(ns.output_jsonl.resolve()),
        "jsonl_row_count": len(rows),
        "rows_by_pdf": rows_by_pdf,
        "chars_by_pdf": chars_by_pdf,
        "docs_summary": docs_summary,
        "element_type_histogram": element_type_histogram,
        "convert_elapsed_s": convert_elapsed_s,
        "total_elapsed_s": total_elapsed_s,
        "parse_error_count": len(parse_errors),
        "parse_errors": parse_errors[:20],
    }
    ns.output_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {ns.output_jsonl.resolve()} rows={len(rows)}", flush=True)
    print(f"WROTE: {ns.output_report.resolve()} total_elapsed_s={total_elapsed_s:.3f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
