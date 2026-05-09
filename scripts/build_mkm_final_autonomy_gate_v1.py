#!/usr/bin/env python3
"""Evaluate final-autonomy promotion gate for MKM AI."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAFE_PACK = ROOT / "docs" / "final" / "artifacts" / "mkm_commercial_gate_pack_v1_latest.json"
DEFAULT_WEEKLY = ROOT / "docs" / "final" / "artifacts" / "mkm_three_lens_weekly_quality_report_v1_latest.json"
DEFAULT_STAGE = ROOT / "docs" / "final" / "artifacts" / "three_lens_staged_inclusion_status_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "mkm_final_autonomy_gate_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--safe-pack-json", type=Path, default=DEFAULT_SAFE_PACK)
    ap.add_argument("--weekly-quality-json", type=Path, default=DEFAULT_WEEKLY)
    ap.add_argument("--staged-status-json", type=Path, default=DEFAULT_STAGE)
    ap.add_argument("--min-weekly-samples", type=int, default=14)
    ap.add_argument("--max-hold-rate", type=float, default=0.05)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    safe_pack = _read_json(args.safe_pack_json if args.safe_pack_json.is_absolute() else ROOT / args.safe_pack_json)
    weekly = _read_json(args.weekly_quality_json if args.weekly_quality_json.is_absolute() else ROOT / args.weekly_quality_json)
    staged = _read_json(args.staged_status_json if args.staged_status_json.is_absolute() else ROOT / args.staged_status_json)

    gate_action = ((safe_pack.get("gate_summary") or {}).get("action") if isinstance(safe_pack.get("gate_summary"), dict) else None)
    safe_mode = bool(safe_pack.get("commercial_ready_safe_mode") is True)
    weekly_samples = int(weekly.get("sample_count") or 0)
    rates = weekly.get("rates") if isinstance(weekly.get("rates"), dict) else {}
    hold_rate = float(rates.get("hold_rate") or 0.0)
    stage_summary = staged.get("summary") if isinstance(staged.get("summary"), dict) else {}
    shadow_missing_count = int(stage_summary.get("shadow_missing_count") or 0)

    checks = {
        "safe_mode_true": safe_mode,
        "gate_action_go_or_watch": gate_action in {"GO", "WATCH"},
        "weekly_samples_ok": weekly_samples >= args.min_weekly_samples,
        "hold_rate_ok": hold_rate <= args.max_hold_rate,
        "shadow_missing_zero": shadow_missing_count == 0,
    }
    passed = all(checks.values())
    decision = "PROMOTE_FINAL_AUTONOMY" if passed else "HOLD_SAFE_MODE"

    payload = {
        "schema": "mkm_final_autonomy_gate_v1",
        "generated_at_utc": _now(),
        "inputs": {
            "safe_pack_json": str(args.safe_pack_json),
            "weekly_quality_json": str(args.weekly_quality_json),
            "staged_status_json": str(args.staged_status_json),
        },
        "thresholds": {
            "min_weekly_samples": args.min_weekly_samples,
            "max_hold_rate": args.max_hold_rate,
        },
        "metrics": {
            "gate_action": gate_action,
            "commercial_ready_safe_mode": safe_mode,
            "weekly_sample_count": weekly_samples,
            "weekly_hold_rate": hold_rate,
            "shadow_missing_count": shadow_missing_count,
        },
        "checks": checks,
        "decision": decision,
        "passed": passed,
    }

    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "decision": decision, "out": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
