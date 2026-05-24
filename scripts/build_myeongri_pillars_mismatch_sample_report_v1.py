#!/usr/bin/env python3
"""Summarize pillars-tier mismatches from locked_eval predictions (no GPU)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.myeongri_deterministic_lora_golden_views_v1 import pillars_view  # noqa: E402

DEFAULT_GOLDEN = ROOT / "data/training/myeongri_deterministic_lora_golden_bulk_v1/locked_eval.jsonl"
DEFAULT_PRED = ROOT / "reports/myeongri_deterministic_lora_locked_eval_predictions_latest.jsonl"
DEFAULT_OUT = ROOT / "reports/myeongri_pillars_mismatch_sample_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--golden-jsonl", type=Path, default=DEFAULT_GOLDEN)
    ap.add_argument("--predictions-jsonl", type=Path, default=DEFAULT_PRED)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sample-limit", type=int, default=10)
    args = ap.parse_args()

    if not args.golden_jsonl.is_file():
        print(f"missing golden: {args.golden_jsonl}", file=sys.stderr)
        return 2
    if not args.predictions_jsonl.is_file():
        print(f"missing predictions: {args.predictions_jsonl}", file=sys.stderr)
        return 2

    gold: dict[str, dict] = {}
    for line in args.golden_jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        gold[str(row["sample_id"])] = row["expected_result"]

    parse_ok = 0
    pillars_match = 0
    samples: list[dict] = []
    n = 0
    for line in args.predictions_jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        n += 1
        o = json.loads(line)
        sid = str(o["id"])
        exp = pillars_view(gold[sid])
        pred_n: dict = {}
        note = o.get("mismatch_note") or ""
        if o.get("parse_ok"):
            parse_ok += 1
            try:
                pred_n = json.loads(o["prediction"])
            except json.JSONDecodeError:
                note = "json_parse_failed"
        got = pillars_view(pred_n) if pred_n else {}
        matched = exp == got
        if matched:
            pillars_match += 1
        elif len(samples) < args.sample_limit:
            samples.append(
                {
                    "sample_id": sid,
                    "mismatch_note": note or "pillars_mismatch",
                    "expected_saju": (exp.get("full_saju") or {}).get("saju"),
                    "predicted_saju": (got.get("full_saju") or {}).get("saju"),
                    "expected_local_iso": (exp.get("resolution") or {}).get("local_iso"),
                    "predicted_local_iso": (got.get("resolution") or {}).get("local_iso"),
                    "expected_ilgan": (exp.get("full_saju") or {}).get("ilgan"),
                    "predicted_ilgan": (got.get("full_saju") or {}).get("ilgan"),
                }
            )

    doc = {
        "schema": "myeongri_pillars_mismatch_sample_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "rows": n,
        "parse_ok_rate": round(parse_ok / n, 6) if n else 0.0,
        "pillars_alignment_pass_rate": round(pillars_match / n, 6) if n else 0.0,
        "predictions_jsonl": str(args.predictions_jsonl.relative_to(ROOT)).replace("\\", "/"),
        "golden_jsonl": str(args.golden_jsonl.relative_to(ROOT)).replace("\\", "/"),
        "sample_limit": args.sample_limit,
        "mismatch_samples": samples,
        "track_wall": {"a_track_auto_promotion": False, "ready_for_external_send": False},
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out_json),
                "pillars_alignment_pass_rate": doc["pillars_alignment_pass_rate"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
