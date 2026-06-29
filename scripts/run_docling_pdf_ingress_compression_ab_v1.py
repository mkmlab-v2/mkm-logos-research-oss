#!/usr/bin/env python3
"""B-track AB: PDF ingress — pypdf raw text vs Docling markdown compression."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

DEFAULT_PDF = ROOT / "reports" / "nvidia_inception_pitch_deck_v1.pdf"
DEFAULT_DOCLING_MD = ROOT / "reports" / "docling_btrack_smoke_v1_latest.md"
DEFAULT_OUT = ROOT / "reports" / "docling_pdf_ingress_compression_ab_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    merged = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, merged.strip()


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows).strip()
    path.write_text((body + "\n") if body else "", encoding="utf-8")


def _extract_pdf_raw_text(pdf_path: Path) -> str:
    import pypdf

    reader = pypdf.PdfReader(str(pdf_path))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts).strip()


def _run_customer_poc(input_jsonl: Path, out_json: Path) -> tuple[int, dict[str, Any] | None, str]:
    cmd = [
        PY,
        str(ROOT / "scripts" / "run_customer_compression_stateless_poc_v1.py"),
        "--input-jsonl",
        str(input_jsonl),
        "--out-json",
        str(out_json),
        "--max-cases",
        "1",
        "--compression-profile",
        "economy",
        "--loss-profile",
        "semantic_general",
        "--jaccard-floor",
        "0.73",
        "--relax-pass-gate",
    ]
    code, log = _run(cmd)
    if code != 0 or not out_json.is_file():
        return code, None, log
    return code, _read_json(out_json), log


def _case_metrics(doc: dict[str, Any]) -> dict[str, Any]:
    cases = doc.get("cases") if isinstance(doc.get("cases"), list) else []
    case = cases[0] if cases else {}
    return {
        "case_count": int(doc.get("case_count") or 0),
        "token_in_proxy": int(case.get("token_in_proxy") or 0),
        "token_out_proxy": int(case.get("token_out_proxy") or 0),
        "token_saving_rate_proxy": float(case.get("token_saving_rate_proxy") or 0.0),
        "jaccard_proxy": float(case.get("jaccard_proxy") or 0.0),
        "ok": bool(case.get("ok")),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    ap.add_argument("--docling-markdown", type=Path, default=DEFAULT_DOCLING_MD)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-docling-run", action="store_true")
    ap.add_argument("--max-chars", type=int, default=12000)
    args = ap.parse_args()

    out_json = args.out_json.resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "schema": "docling_pdf_ingress_compression_ab_v1",
        "generated_at_utc": _utc(),
        "lane": "b_track_hypo",
        "disclaimer": "research_only",
        "send_gate": "HOLD",
        "track_a_promotion": False,
        "ingress_axis": "pdf_document_not_wtt_chat",
        "raw_vs_repair_contract": {
            "raw_label": "pypdf_plain_text",
            "repair_v2_label": "docling_markdown",
            "markdown_hint_injection": False,
        },
        "inputs": {
            "pdf": _rel(args.pdf),
            "docling_markdown": _rel(args.docling_markdown),
        },
    }

    if not args.pdf.is_file():
        report.update({"status": "fail", "error": "missing_pdf"})
        out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        return 1

    docling_log = ""
    if not args.skip_docling_run:
        code, docling_log = _run(
            [
                PY,
                str(ROOT / "scripts" / "smoke_docling_btrack_v1.py"),
                "--input",
                str(args.pdf),
            ]
        )
        if code != 0:
            report.update({"status": "fail", "error": "docling_smoke_failed", "log_tail": docling_log[-500:]})
            out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return 1

    if not args.docling_markdown.is_file():
        report.update({"status": "fail", "error": "missing_docling_markdown"})
        out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1

    raw_text = _extract_pdf_raw_text(args.pdf.resolve())[: max(1, int(args.max_chars))]
    repair_text = args.docling_markdown.read_text(encoding="utf-8", errors="replace")[: max(1, int(args.max_chars))]

    report["text_stats"] = {
        "raw_chars": len(raw_text),
        "repair_v2_chars": len(repair_text),
        "char_delta_repair_minus_raw": len(repair_text) - len(raw_text),
    }

    tmp = ROOT / "reports" / "tmp"
    raw_jsonl = tmp / "docling_pdf_ingress_raw_latest.jsonl"
    repair_jsonl = tmp / "docling_pdf_ingress_repair_latest.jsonl"
    raw_report_path = tmp / "docling_pdf_ingress_raw_report_latest.json"
    repair_report_path = tmp / "docling_pdf_ingress_repair_report_latest.json"

    _write_jsonl(raw_jsonl, [{"id": "pdf-ingress-pypdf-001", "text": raw_text}])
    _write_jsonl(repair_jsonl, [{"id": "pdf-ingress-docling-md-001", "text": repair_text}])

    raw_code, raw_doc, raw_log = _run_customer_poc(raw_jsonl, raw_report_path)
    repair_code, repair_doc, repair_log = _run_customer_poc(repair_jsonl, repair_report_path)

    if raw_code != 0 or raw_doc is None:
        report.update({"status": "fail", "error": "raw_lane_failed", "log_tail": raw_log[-500:]})
        out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1
    if repair_code != 0 or repair_doc is None:
        report.update({"status": "fail", "error": "repair_lane_failed", "log_tail": repair_log[-500:]})
        out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1

    raw_metrics = _case_metrics(raw_doc)
    repair_metrics = _case_metrics(repair_doc)
    report.update(
        {
            "status": "ok",
            "docling_smoke_log_tail": docling_log[-300:] if docling_log else "",
            "raw": raw_metrics,
            "repair_v2": repair_metrics,
            "delta": {
                "token_saving_rate_proxy_repair_minus_raw": round(
                    repair_metrics["token_saving_rate_proxy"] - raw_metrics["token_saving_rate_proxy"],
                    6,
                ),
                "jaccard_proxy_repair_minus_raw": round(
                    repair_metrics["jaccard_proxy"] - raw_metrics["jaccard_proxy"],
                    6,
                ),
                "token_in_proxy_repair_minus_raw": repair_metrics["token_in_proxy"] - raw_metrics["token_in_proxy"],
            },
            "artifacts": {
                "raw_jsonl": _rel(raw_jsonl),
                "repair_jsonl": _rel(repair_jsonl),
                "raw_report": _rel(raw_report_path),
                "repair_report": _rel(repair_report_path),
            },
            "reproduce": [
                "py scripts/run_docling_pdf_ingress_compression_ab_v1.py",
                "py scripts/run_docling_pdf_ingress_compression_ab_v1.py --skip-docling-run",
            ],
        }
    )

    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
