#!/usr/bin/env python3
"""B-track AB: compare WTT compression with/without Docling-style pre-normalization."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

DEFAULT_DOCLING_INPUT = ROOT / "reports" / "nvidia_inception_pitch_deck_v1.pdf"
DEFAULT_DOCLING_MD = ROOT / "reports" / "docling_btrack_smoke_v1_latest.md"
DEFAULT_OUT = ROOT / "reports" / "docling_wtt_compression_ab_v1_latest.json"
DEFAULT_WTT_CORPUS = ROOT / "data" / "compression" / "stateless_poc_prospect_wtt-premium-cs-customer-v1_v1.jsonl"
DEFAULT_OVERLAY = ROOT / "docs/final" / "artifacts" / "tenant_wtt-premium-cs-customer-v1_must_keep_overlay_v1.json"

TEXT_KEYS = ("text", "raw_text", "content", "body")
MULTISPACE_RE = re.compile(r"[ \t]{2,}")
TABLE_PIPE_RE = re.compile(r"\|\s*")


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


def _row_text(obj: dict[str, Any]) -> str | None:
    for key in TEXT_KEYS:
        val = obj.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return None


def _load_wtt_samples(path: Path, sample_count: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            continue
        text = _row_text(obj)
        if not text:
            continue
        row_id = str(obj.get("id") or f"row-{len(rows)}")
        rows.append({"id": row_id, "text": text, "source": obj})
        if len(rows) >= max(1, sample_count):
            break
    return rows


def _pre_normalize_docling_style(text: str) -> str:
    """Deterministic R1 pre-normalization proxy (no markdown injection)."""
    normalized = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    lines = []
    for line in normalized.split("\n"):
        stripped = line.rstrip()
        if "|" in stripped:
            stripped = TABLE_PIPE_RE.sub("| ", stripped).replace("|  ", "| ")
        stripped = MULTISPACE_RE.sub(" ", stripped)
        lines.append(stripped)
    return "\n".join(lines).strip()


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows).strip()
    path.write_text((body + "\n") if body else "", encoding="utf-8")


def _run_customer_poc(
    input_jsonl: Path,
    out_json: Path,
    *,
    max_cases: int,
    overlay_json: Path | None,
) -> tuple[int, dict[str, Any] | None, str]:
    cmd = [
        PY,
        str(ROOT / "scripts" / "run_customer_compression_stateless_poc_v1.py"),
        "--input-jsonl",
        str(input_jsonl),
        "--out-json",
        str(out_json),
        "--max-cases",
        str(max_cases),
        "--compression-profile",
        "economy",
        "--loss-profile",
        "semantic_general",
        "--jaccard-floor",
        "0.73",
        "--relax-pass-gate",
    ]
    if overlay_json is not None and overlay_json.is_file():
        cmd.extend(["--must-keep-overlay-json", str(overlay_json)])
    code, log = _run(cmd)
    if code != 0 or not out_json.is_file():
        return code, None, log
    return code, _read_json(out_json), log


def _aggregate_from_cases(cases: list[dict[str, Any]]) -> dict[str, float]:
    if not cases:
        return {
            "mean_token_saving_rate_proxy": 0.0,
            "mean_jaccard_proxy": 0.0,
        }
    saving = sum(float(c.get("token_saving_rate_proxy") or 0.0) for c in cases) / len(cases)
    jacc = sum(float(c.get("jaccard_proxy") or 0.0) for c in cases) / len(cases)
    return {
        "mean_token_saving_rate_proxy": round(saving, 6),
        "mean_jaccard_proxy": round(jacc, 6),
    }


def _extract_metrics(doc: dict[str, Any]) -> dict[str, Any]:
    agg = doc.get("aggregate") if isinstance(doc.get("aggregate"), dict) else {}
    cases = doc.get("cases") if isinstance(doc.get("cases"), list) else []
    all_agg = _aggregate_from_cases([c for c in cases if isinstance(c, dict)])
    return {
        "case_count": int(doc.get("case_count") or 0),
        "cases_passed": int(doc.get("cases_passed") or 0),
        "mean_token_saving_rate_proxy": float(agg.get("mean_token_saving_rate_proxy") or 0.0),
        "mean_jaccard_proxy": float(agg.get("mean_jaccard_proxy") or 0.0),
        "mean_token_saving_rate_proxy_all_cases": float(all_agg["mean_token_saving_rate_proxy"]),
        "mean_jaccard_proxy_all_cases": float(all_agg["mean_jaccard_proxy"]),
    }


def _per_case_delta(raw_doc: dict[str, Any], repair_doc: dict[str, Any]) -> list[dict[str, Any]]:
    raw_cases = {
        str(c.get("id")): c for c in (raw_doc.get("cases") or []) if isinstance(c, dict) and c.get("id")
    }
    repair_cases = {
        str(c.get("id")): c
        for c in (repair_doc.get("cases") or [])
        if isinstance(c, dict) and c.get("id")
    }
    deltas: list[dict[str, Any]] = []
    for row_id in sorted(set(raw_cases) & set(repair_cases)):
        raw = raw_cases[row_id]
        repair = repair_cases[row_id]
        raw_s = float(raw.get("token_saving_rate_proxy") or 0.0)
        repair_s = float(repair.get("token_saving_rate_proxy") or 0.0)
        raw_j = float(raw.get("jaccard_proxy") or 0.0)
        repair_j = float(repair.get("jaccard_proxy") or 0.0)
        deltas.append(
            {
                "id": row_id,
                "raw": {
                    "token_saving_rate_proxy": raw_s,
                    "jaccard_proxy": raw_j,
                },
                "repair_v2": {
                    "token_saving_rate_proxy": repair_s,
                    "jaccard_proxy": repair_j,
                },
                "delta": {
                    "token_saving_rate_proxy_repair_minus_raw": round(repair_s - raw_s, 6),
                    "jaccard_proxy_repair_minus_raw": round(repair_j - raw_j, 6),
                },
            }
        )
    return deltas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sample-count", type=int, default=10)
    ap.add_argument("--docling-input", type=Path, default=DEFAULT_DOCLING_INPUT)
    ap.add_argument("--docling-markdown", type=Path, default=DEFAULT_DOCLING_MD)
    ap.add_argument("--wtt-jsonl", type=Path, default=DEFAULT_WTT_CORPUS)
    ap.add_argument("--wtt-overlay-json", type=Path, default=DEFAULT_OVERLAY)
    ap.add_argument("--skip-docling-run", action="store_true")
    args = ap.parse_args()

    out_json = args.out_json.resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    sample_count = max(1, int(args.sample_count))

    report: dict[str, Any] = {
        "schema": "docling_wtt_compression_ab_v1",
        "generated_at_utc": _utc(),
        "lane": "b_track_hypo",
        "disclaimer": "research_only",
        "send_gate": "HOLD",
        "track_a_promotion": False,
        "sample_count": sample_count,
        "raw_vs_repair_contract": {
            "raw_required": True,
            "repair_v2_required": True,
            "status": "pure_r1_pre_normalization_only",
            "markdown_hint_injection": False,
        },
        "inputs": {
            "wtt_jsonl": _rel(args.wtt_jsonl),
            "docling_input": _rel(args.docling_input),
            "docling_markdown": _rel(args.docling_markdown),
        },
    }

    if not args.wtt_jsonl.is_file():
        report.update({"status": "fail", "error": "missing_wtt_jsonl"})
        out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        return 1

    docling_log = ""
    if not args.skip_docling_run and args.docling_input.is_file():
        cmd = [
            PY,
            str(ROOT / "scripts" / "smoke_docling_btrack_v1.py"),
            "--input",
            str(args.docling_input),
        ]
        code, docling_log = _run(cmd)
        if code != 0:
            report.update(
                {
                    "status": "fail",
                    "error": "docling_smoke_failed",
                    "docling_log_tail": docling_log[-600:],
                }
            )
            out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
            return 1

    samples = _load_wtt_samples(args.wtt_jsonl.resolve(), sample_count)
    if not samples:
        report.update({"status": "fail", "error": "no_wtt_samples"})
        out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        return 1

    raw_rows = [{"id": s["id"], "text": s["text"]} for s in samples]
    repair_rows = [
        {
            "id": s["id"],
            "text": _pre_normalize_docling_style(s["text"]),
        }
        for s in samples
    ]
    changed_ids = [r["id"] for r in raw_rows if r["text"] != next(x["text"] for x in repair_rows if x["id"] == r["id"])]
    report["normalization_summary"] = {
        "rows_changed_by_r1": len(changed_ids),
        "rows_unchanged": len(raw_rows) - len(changed_ids),
        "changed_ids": changed_ids,
    }

    tmp_dir = ROOT / "reports" / "tmp"
    raw_jsonl = tmp_dir / f"docling_ab_raw_wtt_{sample_count}_latest.jsonl"
    repair_jsonl = tmp_dir / f"docling_ab_repair_wtt_{sample_count}_latest.jsonl"
    raw_json = tmp_dir / f"docling_ab_raw_wtt_{sample_count}_report_latest.json"
    repair_json = tmp_dir / f"docling_ab_repair_wtt_{sample_count}_report_latest.json"

    _write_jsonl(raw_jsonl, raw_rows)
    _write_jsonl(repair_jsonl, repair_rows)

    overlay = args.wtt_overlay_json.resolve() if args.wtt_overlay_json else None
    raw_code, raw_doc, raw_log = _run_customer_poc(
        raw_jsonl,
        raw_json,
        max_cases=sample_count,
        overlay_json=overlay,
    )
    repair_code, repair_doc, repair_log = _run_customer_poc(
        repair_jsonl,
        repair_json,
        max_cases=sample_count,
        overlay_json=overlay,
    )

    if raw_code != 0 or raw_doc is None:
        report.update({"status": "fail", "error": "raw_lane_failed", "raw_log_tail": raw_log[-600:]})
        out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        return 1
    if repair_code != 0 or repair_doc is None:
        report.update(
            {
                "status": "fail",
                "error": "repair_lane_failed",
                "repair_log_tail": repair_log[-600:],
            }
        )
        out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        return 1

    raw_metrics = _extract_metrics(raw_doc)
    repair_metrics = _extract_metrics(repair_doc)
    per_case = _per_case_delta(raw_doc, repair_doc)
    delta_saving = (
        repair_metrics["mean_token_saving_rate_proxy_all_cases"]
        - raw_metrics["mean_token_saving_rate_proxy_all_cases"]
    )
    delta_jacc = repair_metrics["mean_jaccard_proxy_all_cases"] - raw_metrics["mean_jaccard_proxy_all_cases"]

    report.update(
        {
            "status": "ok",
            "docling_smoke_log_tail": docling_log[-300:] if docling_log else "",
            "raw": raw_metrics,
            "repair_v2": repair_metrics,
            "delta": {
                "alignment_pass_rate_delta_repair_v2_minus_raw": None,
                "mean_token_saving_rate_proxy_repair_minus_raw": round(delta_saving, 6),
                "mean_jaccard_proxy_repair_minus_raw": round(delta_jacc, 6),
            },
            "per_case": per_case,
            "artifacts": {
                "raw_jsonl": _rel(raw_jsonl),
                "repair_jsonl": _rel(repair_jsonl),
                "raw_report": _rel(raw_json),
                "repair_report": _rel(repair_json),
            },
            "reproduce": [
                f"py scripts/run_docling_wtt_compression_ab_v1.py --sample-count {sample_count}",
                "py scripts/run_docling_wtt_compression_ab_v1.py --sample-count 10 --skip-docling-run",
            ],
        }
    )

    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
