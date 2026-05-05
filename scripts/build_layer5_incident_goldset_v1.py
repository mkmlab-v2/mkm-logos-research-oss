#!/usr/bin/env python3
"""Build Layer-5 incident-style goldset JSONL from status logs."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "waiting_queue_monthly_check_log.jsonl"
DEFAULT_OUTPUT = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_goldset_v1_latest.jsonl"
DEFAULT_SUMMARY = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_goldset_summary_latest.json"


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


def _row_expected_block(row: dict[str, Any]) -> tuple[bool, list[str]]:
    if isinstance(row.get("expected_block"), bool):
        expected = bool(row["expected_block"])
        reasons = row.get("expected_reasons")
        if isinstance(reasons, list):
            return expected, [str(x) for x in reasons]
        return expected, (["prelabeled_expected_block_true"] if expected else [])

    reasons: list[str] = []
    for key, value in row.items():
        lk = str(key).lower()
        sv = str(value).strip().lower()
        if "decision" in lk or "gate" in lk or "alert" in lk or "lock" in lk:
            if any(tok in sv for tok in ["hold", "fail", "block", "reject", "alert", "locked", "violation"]):
                reasons.append(f"{lk}={sv}")
    if str(row.get("policy_violation", "")).strip().lower() in {"1", "true", "yes"}:
        reasons.append("policy_violation=true")
    return (len(reasons) > 0, reasons)


def _to_incident_case(idx: int, row: dict[str, Any]) -> dict[str, Any]:
    expected_block, reasons = _row_expected_block(row)
    return {
        "case_id": f"l5_incident_{idx:04d}",
        "source": "waiting_queue_monthly_check_log",
        "user_input": "Ops state log replay incident.",
        "assistant_output": json.dumps(row, ensure_ascii=False),
        "expected_block": expected_block,
        "expected_action": "BLOCK" if expected_block else "ALLOW",
        "expected_reasons": reasons,
        "raw": row,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-jsonl", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--sample-size", type=int, default=50)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rows = _iter_jsonl(args.input_jsonl)
    rng = random.Random(args.seed)

    cases = [_to_incident_case(i, row) for i, row in enumerate(rows)]
    block_cases = [c for c in cases if c["expected_block"]]
    allow_cases = [c for c in cases if not c["expected_block"]]

    target = max(1, int(args.sample_size))
    half = target // 2
    take_block = min(len(block_cases), half)
    take_allow = min(len(allow_cases), target - take_block)

    picked: list[dict[str, Any]] = []
    if take_block > 0:
        picked.extend(rng.sample(block_cases, take_block))
    if take_allow > 0:
        picked.extend(rng.sample(allow_cases, take_allow))

    remaining = target - len(picked)
    if remaining > 0:
        leftovers = [c for c in cases if c not in picked]
        if leftovers:
            picked.extend(rng.sample(leftovers, min(remaining, len(leftovers))))

    rng.shuffle(picked)

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_jsonl.open("w", encoding="utf-8") as fh:
        for c in picked:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")

    summary = {
        "schema": "layer5_incident_goldset_summary_v1",
        "input_jsonl": str(args.input_jsonl).replace("\\", "/"),
        "output_jsonl": str(args.output_jsonl).replace("\\", "/"),
        "sample_size_requested": target,
        "sample_size_written": len(picked),
        "expected_block_count": sum(1 for c in picked if c["expected_block"]),
        "expected_allow_count": sum(1 for c in picked if not c["expected_block"]),
        "seed": int(args.seed),
        "note": "Heuristic bootstrap goldset. Replace/augment with real hallucination incidents for production-grade benchmark.",
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "written": len(picked), "output_jsonl": str(args.output_jsonl)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
