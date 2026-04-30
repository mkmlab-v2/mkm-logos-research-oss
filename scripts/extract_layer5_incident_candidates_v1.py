#!/usr/bin/env python3
"""Extract candidate Layer-5 incident cases from JSONL logs."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_candidates_v1_latest.jsonl"
DEFAULT_SUMMARY = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_candidates_summary_latest.json"

KEYWORD_HINTS = [
    "hold",
    "fail",
    "block",
    "reject",
    "violation",
    "locked",
    "alert",
    "auto_promote",
    "direct_bridge",
    "regime",
    "track b",
    "track a",
]
STRONG_BLOCK_HINTS = {"hold", "fail", "block", "reject", "violation", "locked", "alert", "auto_promote", "direct_bridge"}


def _read_jsonl(path: Path) -> list[tuple[int, dict[str, Any]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8-sig") as fh:
        for i, line in enumerate(fh, start=1):
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append((i, obj))
    return rows


def _stringify(row: dict[str, Any]) -> str:
    return json.dumps(row, ensure_ascii=False).lower()


def _looks_like_incident(row: dict[str, Any]) -> tuple[bool, list[str]]:
    text = _stringify(row)
    hits = [k for k in KEYWORD_HINTS if k in text]
    return (len(hits) > 0, hits)


def _to_case(idx: int, source: Path, line_no: int, row: dict[str, Any], hits: list[str]) -> dict[str, Any]:
    expected_block = any(h in STRONG_BLOCK_HINTS for h in hits)
    return {
        "case_id": f"l5_candidate_{idx:05d}",
        "source_file": str(source).replace("\\", "/"),
        "source_line": line_no,
        "user_input": "Recovered from ops log candidate.",
        "assistant_output": json.dumps(row, ensure_ascii=False),
        "expected_block": expected_block,
        "expected_action": "BLOCK" if expected_block else "ALLOW",
        "expected_reasons": hits,
        "policy_violation_type": "auto_extracted_candidate",
        "review_status": "draft",
        "raw": row,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--input-jsonl",
        action="append",
        default=[],
        help="Input JSONL path. Can be repeated.",
    )
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--max-cases", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--control-ratio",
        type=float,
        default=0.5,
        help="Ratio of control (non-incident) rows to include among candidates.",
    )
    args = ap.parse_args()

    inputs = [Path(x) for x in args.input_jsonl]
    if not inputs:
        raise SystemExit("No input files. Use --input-jsonl at least once.")

    rng = random.Random(args.seed)
    incident_cases: list[dict[str, Any]] = []
    control_pool: list[tuple[Path, int, dict[str, Any]]] = []
    scanned_rows = 0
    idx = 0

    for src in inputs:
        for line_no, row in _read_jsonl(src):
            scanned_rows += 1
            ok, hits = _looks_like_incident(row)
            if not ok:
                control_pool.append((src, line_no, row))
                continue
            incident_cases.append(_to_case(idx, src, line_no, row, hits))
            idx += 1

    max_cases = max(1, int(args.max_cases))
    control_ratio = max(0.0, min(0.9, float(args.control_ratio)))
    target_controls = int(max_cases * control_ratio)
    target_incidents = max_cases - target_controls

    selected_incidents = incident_cases
    if len(selected_incidents) > target_incidents:
        selected_incidents = rng.sample(selected_incidents, target_incidents)

    controls: list[dict[str, Any]] = []
    if control_pool and target_controls > 0:
        picks = rng.sample(control_pool, min(target_controls, len(control_pool)))
        for src, line_no, row in picks:
            controls.append(_to_case(idx, src, line_no, row, []))
            idx += 1

    cases = selected_incidents + controls
    if len(cases) < max_cases:
        leftovers = [c for c in incident_cases if c not in selected_incidents]
        if leftovers:
            cases.extend(rng.sample(leftovers, min(max_cases - len(cases), len(leftovers))))

    if len(cases) > args.max_cases:
        cases = rng.sample(cases, args.max_cases)

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_jsonl.open("w", encoding="utf-8") as fh:
        for case in cases:
            fh.write(json.dumps(case, ensure_ascii=False) + "\n")

    summary = {
        "schema": "layer5_incident_candidates_summary_v1",
        "inputs": [str(x).replace("\\", "/") for x in inputs],
        "scanned_row_count": scanned_rows,
        "candidate_count": len(cases),
        "incident_candidate_count": len([c for c in cases if c.get("expected_block")]),
        "control_candidate_count": len([c for c in cases if not c.get("expected_block")]),
        "output_jsonl": str(args.output_jsonl).replace("\\", "/"),
        "seed": int(args.seed),
        "max_cases": int(args.max_cases),
        "note": "Draft candidates only. Human review required before promotion to goldset.",
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "candidate_count": len(cases), "output_jsonl": str(args.output_jsonl)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
