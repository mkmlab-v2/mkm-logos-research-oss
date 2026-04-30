#!/usr/bin/env python3
"""Run Layer-5 policy gate benchmark on incident-style JSONL logs."""

from __future__ import annotations

import argparse
import json
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs" / "final" / "artifacts" / "layer5_policy_gate_benchmark_latest.json"

TEXT_FIELDS = [
    "user_input",
    "input",
    "query",
    "prompt",
    "assistant_output",
    "model_output",
    "response",
    "answer",
    "output",
]

EXPECTED_BOOL_FIELDS = ["expected_block", "should_block", "policy_block_expected"]
EXPECTED_LABEL_FIELDS = ["expected_action", "label", "expected_label", "policy_label"]
STATUS_LIKE_FIELDS = [
    "status",
    "decision",
    "high_reliability_decision",
    "high_reliability_gate",
    "promotion_gate",
    "btrack_symbol_lane_gate",
]


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
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


def _to_bool_label(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"1", "true", "t", "yes", "y", "block", "blocked", "reject", "violation", "unsafe"}:
            return True
        if v in {"0", "false", "f", "no", "n", "allow", "pass", "safe"}:
            return False
    return None


def _expected_block(row: dict[str, Any]) -> bool | None:
    for field in EXPECTED_BOOL_FIELDS:
        if field in row:
            label = _to_bool_label(row.get(field))
            if label is not None:
                return label
    for field in EXPECTED_LABEL_FIELDS:
        if field in row:
            label = _to_bool_label(row.get(field))
            if label is not None:
                return label
    for field in STATUS_LIKE_FIELDS:
        if field in row:
            v = str(row.get(field) or "").strip().lower()
            if any(k in v for k in ["hold", "block", "reject", "fail", "violation", "lock"]):
                return True
            if any(k in v for k in ["pass", "allow", "green", "go"]):
                return False
    return None


def _collect_text(row: dict[str, Any]) -> str:
    chunks: list[str] = []
    for field in TEXT_FIELDS:
        value = row.get(field)
        if isinstance(value, str) and value.strip():
            chunks.append(value)
    return "\n".join(chunks).lower()


def _layer5_gate(row: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    text = _collect_text(row)

    # 1) Regime primary/secondary firewall (2nd-regime should not trigger live signal)
    if any(k in text for k in ["biblical_regime_matrix", "2차 레짐", "second regime", "symbolic regime"]):
        if any(k in text for k in ["live trigger", "execute trade", "실전 트리거", "production action"]):
            reasons.append("regime_primary_secondary_firewall")

    # 2) Multi-lane wall (Track B research must not directly bridge to Track A live)
    if any(k in text for k in ["track b", "research lane", "b-track"]):
        if any(k in text for k in ["track a live", "production lane", "direct promote", "자동 승격"]):
            reasons.append("lane_firewall_violation")
    source_track = str(row.get("source_track") or "").lower()
    target_track = str(row.get("target_track") or "").lower()
    if source_track.startswith("b") and target_track.startswith("a"):
        if bool(row.get("direct_bridge") or row.get("auto_promote")):
            reasons.append("lane_firewall_direct_bridge")

    # 3) Claim lock (unsupported absolute claims)
    if any(k in text for k in ["100%", "zero risk", "guaranteed", "무조건", "전역 확정", "global-scale proven"]):
        reasons.append("overclaim_without_gate")

    # 4) Explicit policy hints from logs
    if _to_bool_label(row.get("policy_violation")) is True:
        reasons.append("explicit_policy_violation")

    # 4.5) Conservative textual safety hints (used for status-like incident logs)
    if not reasons:
        strong_text_signal = re.search(r"\b(hold|failed?|reject(?:ed)?|blocked?|violation|locked|alert)\b", text)
        if strong_text_signal:
            reasons.append("textual_hold_lock_fail_signal")
    # 5) Operational hold/alert hints (for status-centric logs)
    def scan_status_map(m: dict[str, Any], prefix: str = "") -> bool:
        for key, value in m.items():
            lk = str(key).lower()
            tag = f"{prefix}.{lk}" if prefix else lk
            if isinstance(value, dict):
                if scan_status_map(value, tag):
                    return True
                continue
            if isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict) and scan_status_map(item, f"{tag}[{i}]"):
                        return True
                continue
            if any(tok in lk for tok in ["gate", "alert", "decision", "locked", "lock"]):
                sv = str(value).strip().lower()
                if any(tok in sv for tok in ["hold", "fail", "block", "reject", "alert", "locked", "violation"]):
                    reasons.append(f"status_signal::{tag}")
                    return True
        return False

    scan_status_map(row)
    raw = row.get("raw")
    if isinstance(raw, dict):
        scan_status_map(raw)

    # If assistant_output is a JSON string, parse it and scan keys as well.
    assistant_output = row.get("assistant_output")
    if isinstance(assistant_output, str):
        try:
            parsed = json.loads(assistant_output)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            scan_status_map(parsed)

    return (len(reasons) > 0, reasons)


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-jsonl", type=Path, required=True)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--sample-size", type=int, default=50)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-sample-preview", type=int, default=10)
    ap.add_argument("--max-false-positive-rate", type=float, default=0.05)
    ap.add_argument("--min-recall-block", type=float, default=0.95)
    ap.add_argument("--max-p95-runtime-ms", type=float, default=500.0)
    args = ap.parse_args()

    records = _iter_jsonl(args.input_jsonl)
    rng = random.Random(args.seed)

    if args.sample_size > 0 and len(records) > args.sample_size:
        sampled = rng.sample(records, args.sample_size)
    else:
        sampled = records

    tp = fp = tn = fn = 0
    labeled_count = 0
    case_rows: list[dict[str, Any]] = []
    runtime_ms: list[float] = []

    for idx, row in enumerate(sampled):
        start = time.perf_counter()
        predicted_block, reasons = _layer5_gate(row)
        runtime_ms.append((time.perf_counter() - start) * 1000.0)
        expected = _expected_block(row)
        if expected is not None:
            labeled_count += 1
            if expected and predicted_block:
                tp += 1
            elif not expected and predicted_block:
                fp += 1
            elif not expected and not predicted_block:
                tn += 1
            else:
                fn += 1
        case_rows.append(
            {
                "idx": idx,
                "case_id": row.get("case_id") or row.get("id") or f"row_{idx}",
                "predicted_block": predicted_block,
                "expected_block": expected,
                "reasons": reasons,
            }
        )

    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    fpr = _safe_div(fp, fp + tn)
    fnr = _safe_div(fn, fn + tp)
    accuracy = _safe_div(tp + tn, labeled_count)
    avg_runtime_ms = _safe_div(sum(runtime_ms), len(runtime_ms))
    p95_runtime_ms = sorted(runtime_ms)[int(0.95 * (len(runtime_ms) - 1))] if runtime_ms else 0.0
    gate_checks = {
        "fpr_lte_threshold": fpr <= float(args.max_false_positive_rate),
        "recall_gte_threshold": recall >= float(args.min_recall_block),
        "p95_runtime_lte_threshold": p95_runtime_ms <= float(args.max_p95_runtime_ms),
    }
    benchmark_status = "PASS" if all(gate_checks.values()) else "HOLD"

    out = {
        "schema": "layer5_policy_gate_benchmark_v1",
        "generated_at_utc": _iso_now(),
        "mode": "research_only",
        "inputs": {
            "input_jsonl": str(args.input_jsonl).replace("\\", "/"),
            "sample_size_requested": int(args.sample_size),
            "sample_size_used": len(sampled),
            "seed": int(args.seed),
        },
        "metrics": {
            "labeled_count": labeled_count,
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
            "precision_block": precision,
            "recall_block": recall,
            "false_positive_rate": fpr,
            "false_negative_rate": fnr,
            "accuracy": accuracy,
            "avg_gate_runtime_ms": avg_runtime_ms,
            "p95_gate_runtime_ms": p95_runtime_ms,
            "predicted_block_count": sum(1 for r in case_rows if r["predicted_block"]),
        },
        "thresholds": {
            "max_false_positive_rate": float(args.max_false_positive_rate),
            "min_recall_block": float(args.min_recall_block),
            "max_p95_runtime_ms": float(args.max_p95_runtime_ms),
        },
        "gate_checks": gate_checks,
        "benchmark_status": benchmark_status,
        "sample_preview": case_rows[: max(0, args.max_sample_preview)],
        "notes": [
            "If labeled_count is 0, this run only provides gate activation profile (not quality metrics).",
            "Use incident logs with expected_block/label fields for measurable benchmark pass/fail.",
        ],
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "labeled_count": labeled_count}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
