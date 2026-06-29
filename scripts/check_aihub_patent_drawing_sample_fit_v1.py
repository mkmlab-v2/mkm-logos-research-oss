#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B-track [HYPO]: inspect patent-drawing Hub sample vs control-integrity golden fields.

Exits 0 when sample missing (pending). Exits 1 when sample exists but prompt/response unmapped.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE = ROOT / "data" / "research" / "btrack" / "samples" / "aihub_patent_drawing_sample_v1.jsonl"
DEFAULT_ZIP = ROOT / "data" / "research" / "btrack" / "samples" / "aihub_raw" / "TL_patent_circuit.zip"
DEFAULT_REPORT = (
    ROOT
    / "projects"
    / "bitcoin-trading"
    / "memory"
    / "v2"
    / "btrack"
    / "raw_feeds"
    / "aihub"
    / "aihub_patent_drawing_fit_report_v1.json"
)

PROMPT_KEYS = ("prompt", "question", "input", "instruction", "prompt_text", "task")
RESPONSE_KEYS = ("expected_response", "answer", "output", "response", "final_answer")
COT_KEYS = ("cot_steps", "reasoning_chain", "steps", "chain_of_thought", "reasoning", "thought")


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


def _flatten_hub_row(raw: dict[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = dict(raw)
    for nest_key in ("instruction", "instruction_id", "label", "annotation", "data"):
        nested = raw.get(nest_key)
        if isinstance(nested, dict):
            flat.update({f"{nest_key}.{k}": v for k, v in nested.items()})
            for k, v in nested.items():
                if k not in flat:
                    flat[k] = v
    return flat


def _inspect_row(row: dict[str, Any]) -> dict[str, str]:
    flat = _flatten_hub_row(row)
    prompt = _first_str(flat, PROMPT_KEYS)
    response = _first_str(flat, RESPONSE_KEYS)
    cot = _first_str(flat, COT_KEYS)
    out: dict[str, str] = {}
    out["prompt"] = "found" if prompt else "missing"
    out["expected_response"] = "found" if response else ("derivable_from_cot" if cot else "missing")
    out["domain"] = "found" if flat.get("domain") else "missing"
    out["language"] = "found" if flat.get("language") or flat.get("lang") else "missing"
    out["text_only_sidecar"] = "unknown"
    image_keys = [k for k in flat if "image" in k.lower() or "drawing" in k.lower() or k.endswith("_path")]
    if image_keys and not prompt and not response and not cot:
        out["text_only_sidecar"] = "blocked_multimodal_only"
    elif prompt or response or cot:
        out["text_only_sidecar"] = "ok"
    return out


def _load_rows(sample: Path, zip_path: Path, max_rows: int) -> list[dict[str, Any]]:
    if sample.is_file():
        lines = [ln.strip() for ln in sample.read_text(encoding="utf-8").splitlines() if ln.strip()]
        return [json.loads(ln) for ln in lines[:max_rows]]

    if zip_path.is_file():
        rows: list[dict[str, Any]] = []
        with zipfile.ZipFile(zip_path) as zf:
            names = sorted(n for n in zf.namelist() if n.lower().endswith(".json"))
            for name in names[:max_rows]:
                rows.append(json.loads(zf.read(name).decode("utf-8")))
        return rows
    return []


def main() -> int:
    p = argparse.ArgumentParser(description="Check patent-drawing sample fit (B-track)")
    p.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    p.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    p.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    p.add_argument("--max-rows", type=int, default=3)
    args = p.parse_args()

    rows = _load_rows(args.sample, args.zip, args.max_rows)
    if not rows:
        print(
            f"PENDING: sample missing at {args.sample.relative_to(ROOT)} "
            f"and zip missing at {args.zip.relative_to(ROOT)} — fit check skipped (exit 0)."
        )
        if args.report.is_file():
            report = json.loads(args.report.read_text(encoding="utf-8"))
            if report.get("overall_fit") not in (None, "pending"):
                print("WARN: fit report overall_fit is not pending while sample missing", file=sys.stderr)
                return 1
        return 0

    inspections = [_inspect_row(r) for r in rows]
    blockers = [f for f in ("prompt", "expected_response") if inspections[0].get(f) == "missing"]

    print(f"OK: inspected_rows={len(rows)}")
    for idx, ins in enumerate(inspections, start=1):
        print(f"  row_{idx}: " + ", ".join(f"{k}={v}" for k, v in ins.items()))

    if blockers:
        print("FAIL: cannot map required golden fields: " + ", ".join(blockers), file=sys.stderr)
        return 1

    if any(i.get("text_only_sidecar") == "blocked_multimodal_only" for i in inspections):
        print("PARTIAL: multimodal-only rows — text sidecar extraction required for golden ingest.")
        return 0

    print("PARTIAL: prompt/response mappable — derived policy_tags still required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
