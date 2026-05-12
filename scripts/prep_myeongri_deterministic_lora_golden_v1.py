#!/usr/bin/env python3
"""Emit one JSONL row for Pack 0-B (myeongri deterministic LoRA golden set v1).

Runs the same engine path as ``run_saju_global_birth_v1.py`` and writes
``expected_result`` with ``full_saju`` **without** ``calculated_at`` (determinism).

Example::

  py scripts/prep_myeongri_deterministic_lora_golden_v1.py \\
    --utc-instant 1992-03-12T17:00:00Z --iana-tz Asia/Seoul \\
    --sample-id mdl-gs-v1-0003 --split train --out-jsonl data/training/myeongri_lora_golden_v1.jsonl --append
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_WS = Path(__file__).resolve().parent.parent
if str(_WS) not in sys.path:
    sys.path.insert(0, str(_WS))

from scripts.manseryeok_perfect_final import PerfectManseryeok  # noqa: E402
from scripts.saju_birth_resolver_v1 import resolve_from_utc_instant  # noqa: E402


def _build_body(utc_instant: str, iana_tz: str, is_male: bool) -> dict:
    res = resolve_from_utc_instant(utc_instant, iana_tz)
    eng = PerfectManseryeok()
    full = eng.calculate_full_saju_perfect(
        res.engine_year,
        res.engine_month,
        res.engine_day,
        res.engine_hour,
        is_solar=True,
        is_male=is_male,
    )
    return {
        "schema": "saju_global_birth_result_v1",
        "version": "1.0.0",
        "resolution": {
            "birth_instant_utc": res.birth_instant_utc.strftime("%Y-%m-%dT%H:%M:%S") + "Z",
            "iana_tz": res.iana_tz,
            "local_iso": res.local_datetime.isoformat(),
            "engine_inputs": {
                "year": res.engine_year,
                "month": res.engine_month,
                "day": res.engine_day,
                "hour": res.engine_hour,
            },
            "warnings": list(res.warnings),
            "meta": res.meta,
        },
        "full_saju": full,
    }


def _strip_calculated_at(full_saju: dict) -> dict:
    return {k: v for k, v in full_saju.items() if k != "calculated_at"}


def build_golden_row_dict(
    utc_instant: str,
    iana_tz: str,
    is_male: bool,
    sample_id: str,
    split: str,
) -> dict:
    """Build one golden row dict (for tests and CLI)."""
    body = _build_body(utc_instant, iana_tz, is_male)
    fs = _strip_calculated_at(body["full_saju"])
    return {
        "schema_version": "myeongri_deterministic_lora_golden_set_v1",
        "sample_id": sample_id,
        "split": split,
        "birth_instant_utc": utc_instant,
        "iana_tz": iana_tz,
        "is_male": bool(is_male),
        "expected_result": {
            "schema": body["schema"],
            "version": body["version"],
            "resolution": body["resolution"],
            "full_saju": fs,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Prep one myeongri deterministic LoRA golden JSONL row.")
    ap.add_argument("--utc-instant", required=True, help="ISO Z birth instant")
    ap.add_argument("--iana-tz", required=True)
    ap.add_argument("--is-male", action="store_true", default=False)
    ap.add_argument("--sample-id", required=True, help="e.g. mdl-gs-v1-0001")
    ap.add_argument(
        "--split",
        required=True,
        choices=("train", "validation", "test", "locked_eval"),
    )
    ap.add_argument("--out-jsonl", type=Path, required=True)
    ap.add_argument("--append", action="store_true")
    args = ap.parse_args()

    row = build_golden_row_dict(
        args.utc_instant,
        args.iana_tz,
        args.is_male,
        args.sample_id,
        args.split,
    )

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False) + "\n"
    mode = "a" if args.append else "w"
    with args.out_jsonl.open(mode, encoding="utf-8") as f:
        f.write(line)
    print(f"Wrote 1 row -> {args.out_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
