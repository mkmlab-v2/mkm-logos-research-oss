#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B-track [HYPO]: inspect CoT-Fabric Hub sample JSONL vs control-integrity golden set fields.

Exits 0 when sample is missing but fit report remains pending (no false pass).
Exits 1 when sample exists but required golden fields cannot be mapped.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE = ROOT / "data" / "research" / "btrack" / "samples" / "aihub_cot_fabric_sample_v1.jsonl"
DEFAULT_GOLDEN_PREVIEW = ROOT / "data" / "research" / "btrack" / "samples" / "aihub_cot_fabric_golden_preview_v1.jsonl"
GOLDEN_SCHEMA = ROOT / "docs" / "final" / "schemas" / "mkm_control_integrity_golden_set_v1.schema.json"
DEFAULT_REPORT = (
    ROOT
    / "projects"
    / "bitcoin-trading"
    / "memory"
    / "v2"
    / "btrack"
    / "raw_feeds"
    / "aihub"
    / "aihub_cot_fabric_fit_report_v1.json"
)
GOLDEN_REQUIRED = (
    "prompt",
    "expected_response",
    "domain",
    "language",
    "policy_tags",
    "must_include",
    "must_not_include",
    "scoring_profile",
)

PROMPT_KEYS = ("prompt", "question", "input", "prompt_text", "instruction")
RESPONSE_KEYS = ("expected_response", "answer", "output", "response", "final_answer")
COT_KEYS = ("cot_steps", "reasoning_chain", "steps", "chain_of_thought", "reasoning")


def _first_str(row: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for k in keys:
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, list) and v:
            parts = [str(x).strip() for x in v if str(x).strip()]
            if parts:
                return "\n".join(parts)
    return None


def _inspect_row(row: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    prompt = _first_str(row, PROMPT_KEYS)
    response = _first_str(row, RESPONSE_KEYS)
    cot = _first_str(row, COT_KEYS)

    out["prompt"] = "found" if prompt else "missing"
    out["expected_response"] = "found" if response else ("derivable_from_cot" if cot else "missing")
    out["domain"] = "found" if row.get("domain") else "missing"
    out["language"] = "found" if row.get("language") or row.get("lang") else "missing"
    out["policy_tags"] = "derived_required"
    out["must_include"] = "derived_required"
    out["must_not_include"] = "derived_required"
    out["scoring_profile"] = "template_required"
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Check CoT-Fabric sample fit (B-track, pending-safe)")
    p.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    p.add_argument("--golden-preview", type=Path, default=DEFAULT_GOLDEN_PREVIEW)
    p.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    p.add_argument("--max-rows", type=int, default=3)
    args = p.parse_args()

    if not args.sample.is_file():
        print(
            f"PENDING: sample missing at {args.sample.relative_to(ROOT)} — "
            "fit check skipped (exit 0, no false pass)."
        )
        if args.report.is_file():
            report = json.loads(args.report.read_text(encoding="utf-8"))
            if report.get("overall_fit") not in (None, "pending"):
                print("WARN: fit report overall_fit is not pending while sample missing", file=sys.stderr)
                return 1
        return 0

    lines = [ln.strip() for ln in args.sample.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        print("FAIL: sample file is empty", file=sys.stderr)
        return 1

    rows: list[dict[str, Any]] = []
    for i, line in enumerate(lines[: args.max_rows], start=1):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"FAIL: line {i} invalid JSON: {e}", file=sys.stderr)
            return 1

    inspections = [_inspect_row(r) for r in rows]
    blockers = []
    for field in ("prompt", "expected_response"):
        if any(inspections[0].get(field) == "missing" for _ in [0]):
            if inspections[0][field] == "missing":
                blockers.append(field)

    print(f"OK: inspected_rows={len(rows)} sample={args.sample.relative_to(ROOT)}")
    for idx, ins in enumerate(inspections, start=1):
        print(f"  row_{idx}: " + ", ".join(f"{k}={v}" for k, v in ins.items()))

    if blockers:
        print(
            "FAIL: cannot map required golden fields from sample: " + ", ".join(blockers),
            file=sys.stderr,
        )
        return 1

    golden_ok = False
    if args.golden_preview.is_file() and GOLDEN_SCHEMA.is_file():
        try:
            import jsonschema
        except ImportError:
            print("WARN: jsonschema missing — skip golden preview validation", file=sys.stderr)
        else:
            schema = json.loads(GOLDEN_SCHEMA.read_text(encoding="utf-8"))
            glines = [
                ln.strip()
                for ln in args.golden_preview.read_text(encoding="utf-8").splitlines()
                if ln.strip()
            ]
            for i, line in enumerate(glines[: args.max_rows], start=1):
                jsonschema.validate(instance=json.loads(line), schema=schema)
            golden_ok = bool(glines)
            print(
                f"GOLDEN_PREVIEW_OK: rows={min(len(glines), args.max_rows)} "
                f"path={args.golden_preview.relative_to(ROOT)}"
            )

    if golden_ok:
        print(
            "COMPATIBLE: Hub sample maps to schema-valid golden preview — "
            "terms review still required before ingest promotion."
        )
        return 0

    print(
        "PARTIAL: prompt/response mappable — still requires derived policy_tags, "
        "must_include/must_not_include, scoring_profile before golden set ingest."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
