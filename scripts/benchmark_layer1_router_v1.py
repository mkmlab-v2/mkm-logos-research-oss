#!/usr/bin/env python3
"""Benchmark Layer-1 router classification on incident goldset."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs" / "final" / "artifacts" / "layer1_router_benchmark_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _collect_text(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("user_input", "assistant_output"):
        v = row.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(v)
    raw = row.get("raw")
    if isinstance(raw, dict):
        parts.append(json.dumps(raw, ensure_ascii=False))
    return "\n".join(parts).lower()


def _predict_route(row: dict[str, Any]) -> str:
    text = _collect_text(row)
    # Safety-critical path routing hints
    if re.search(r"\b(hold|fail|reject|block|violation|locked|alert)\b", text):
        return "safety_critical"
    if re.search(r"\b(track b|direct_bridge|auto_promote|regime)\b", text):
        return "safety_critical"
    return "standard"


def _expected_route(row: dict[str, Any]) -> str | None:
    expected = row.get("expected_block")
    if isinstance(expected, bool):
        return "safety_critical" if expected else "standard"
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-jsonl", type=Path, required=True)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--min-router-accuracy", type=float, default=0.95)
    args = ap.parse_args()

    rows = _read_jsonl(args.input_jsonl)
    labeled = 0
    correct = 0
    tp = fp = tn = fn = 0
    preview: list[dict[str, Any]] = []

    for idx, row in enumerate(rows):
        pred = _predict_route(row)
        exp = _expected_route(row)
        if exp is not None:
            labeled += 1
            if pred == exp:
                correct += 1
            if exp == "safety_critical" and pred == "safety_critical":
                tp += 1
            elif exp == "standard" and pred == "safety_critical":
                fp += 1
            elif exp == "standard" and pred == "standard":
                tn += 1
            elif exp == "safety_critical" and pred == "standard":
                fn += 1
        if idx < 10:
            preview.append(
                {
                    "idx": idx,
                    "case_id": row.get("case_id", f"row_{idx}"),
                    "predicted_route": pred,
                    "expected_route": exp,
                }
            )

    accuracy = (correct / labeled) if labeled else 0.0
    status = "PASS" if accuracy >= float(args.min_router_accuracy) else "HOLD"
    out = {
        "schema": "layer1_router_benchmark_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "input_jsonl": str(args.input_jsonl).replace("\\", "/"),
            "sample_size_used": len(rows),
        },
        "metrics": {
            "labeled_count": labeled,
            "correct": correct,
            "accuracy": accuracy,
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
        },
        "thresholds": {
            "min_router_accuracy": float(args.min_router_accuracy),
        },
        "benchmark_status": status,
        "sample_preview": preview,
        "note": "Layer-1 router benchmark from expected_block-derived labels.",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "status": status}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
