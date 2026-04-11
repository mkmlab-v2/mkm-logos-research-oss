#!/usr/bin/env python3
"""Export general_prophecy_registry_v1 JSON to instruction-tuning JSONL (B-track research).

Schema SSOT: docs/final/GENERAL_PROPHECY_SCHEMA_V1.json — forecast snapshots do not
require lens_rationale; when absent, output uses pointer + rubric fallback (no invented L3).

Output lines: {"instruction": "...", "output": "..."}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_latest.json"
DEFAULT_OUT = ROOT / "data" / "training" / "macro_prophecy_dataset_v1.jsonl"

GUARD_PREFIX = (
    "[HYPO] (B-Track Research) 본 분석은 확률적 가설이며 단정적 미래를 보장하지 않습니다. "
)


def _first_forecast(q: dict[str, Any]) -> dict[str, Any]:
    fcs = q.get("forecasts")
    if not isinstance(fcs, list) or not fcs:
        return {}
    fc0 = fcs[0]
    return fc0 if isinstance(fc0, dict) else {}


def _lens_rationale_text(fc: dict[str, Any]) -> str | None:
    lr = fc.get("lens_rationale")
    if isinstance(lr, dict):
        parts: list[str] = []
        for key in ("logos", "myeongni", "sasang", "로고스", "명리", "사상"):
            val = lr.get(key)
            if isinstance(val, str) and val.strip():
                parts.append(f"[{key}] {val.strip()}")
        if parts:
            return "\n".join(parts)
    if isinstance(lr, str) and lr.strip():
        return lr.strip()
    return None


def _fallback_response_body(q: dict[str, Any], fc: dict[str, Any]) -> str:
    lines: list[str] = []
    ref = q.get("layer3_interpretation_ref")
    if ref:
        lines.append(f"Layer3 reference (pointer only): {ref}")
    sd = fc.get("source_detail")
    if isinstance(sd, str) and sd.strip():
        lines.append(f"Forecast source_detail: {sd.strip()}")
    p = fc.get("probability_0_1")
    if isinstance(p, (int, float)):
        lines.append(f"Layer1 probability_0_1: {p}")
    sk = fc.get("source_kind")
    if sk:
        lines.append(f"Forecast source_kind: {sk}")
    rc = q.get("resolution_criteria")
    if isinstance(rc, str) and rc.strip():
        snippet = rc.strip()
        if len(snippet) > 1200:
            snippet = snippet[:1200] + "…"
        lines.append(f"Resolution criteria (rubric): {snippet}")
    if not lines:
        lines.append(
            "(No lens_rationale and no pointer text; extend registry or add optional lens_rationale on forecast for richer training rows.)"
        )
    return "\n".join(lines)


def _row(q: dict[str, Any]) -> dict[str, str] | None:
    if not isinstance(q, dict):
        return None
    inst = q.get("question_text")
    if not isinstance(inst, str) or len(inst.strip()) < 10:
        return None
    fc = _first_forecast(q)
    body = _lens_rationale_text(fc)
    if body is None:
        body = _fallback_response_body(q, fc)
    return {
        "instruction": inst.strip(),
        "output": GUARD_PREFIX + body,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", "-i", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output", "-o", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    ns = ap.parse_args()

    if not ns.input.is_file():
        print(f"missing input: {ns.input}", file=sys.stderr)
        return 2
    doc = json.loads(ns.input.read_text(encoding="utf-8"))
    if doc.get("schema") != "general_prophecy_registry_v1":
        print("input must be general_prophecy_registry_v1", file=sys.stderr)
        return 2

    lines_out: list[str] = []
    for q in doc.get("questions") or []:
        row = _row(q if isinstance(q, dict) else {})
        if row:
            lines_out.append(json.dumps(row, ensure_ascii=False))

    if not lines_out:
        print("no exportable questions", file=sys.stderr)
        return 2

    text = "\n".join(lines_out) + "\n"
    if ns.stdout_only:
        sys.stdout.write(text)
        return 0

    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(text, encoding="utf-8")
    print(str(ns.output.resolve()))
    print(f"rows: {len(lines_out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
