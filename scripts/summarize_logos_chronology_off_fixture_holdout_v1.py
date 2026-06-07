#!/usr/bin/env python3
"""Partition holdout compare for off-fixture text_blind v1 vs v2 (disjoint from historical 47)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
REP = ROOT / "reports"
DEFAULT_V1 = ART / "logos_chronology_off_fixture_eval_text_blind_v1_latest.json"
DEFAULT_V2 = ART / "logos_chronology_off_fixture_eval_text_blind_v2_v1_latest.json"
DEFAULT_OUT = REP / "logos_chronology_off_fixture_holdout_v1_latest.json"

from summarize_logos_chronology_partition_holdout_v1 import _load, build_holdout  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v1-json", type=Path, default=DEFAULT_V1)
    ap.add_argument("--v2-json", type=Path, default=DEFAULT_V2)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    v1_path = args.v1_json if args.v1_json.is_absolute() else ROOT / args.v1_json
    v2_path = args.v2_json if args.v2_json.is_absolute() else ROOT / args.v2_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    v1 = _load(v1_path)
    v2 = _load(v2_path)
    doc = build_holdout(
        v1,
        v2,
        schema="logos_chronology_off_fixture_holdout_v1",
        v1_input=str(v1_path.relative_to(ROOT)).replace("\\", "/"),
        v2_input=str(v2_path.relative_to(ROOT)).replace("\\", "/"),
        cohort="off_fixture",
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc["compare"], ensure_ascii=False))
    print(f"WROTE: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
