#!/usr/bin/env python3
"""Gate: curated catalog + protocol ready for human enrollment ([HYPO])."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACK = ROOT / "reports/warmth_trigger_pilot_pack_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/warmth_trigger_pilot_readiness_v1_latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_readiness(pack: dict[str, Any]) -> dict[str, Any]:
    cat = pack.get("catalog_readiness") or {}
    checks = {
        "min_curated_items": bool(cat.get("min_items_met")),
        "all_dose_reviews_approved": bool(cat.get("all_approved")),
        "protocol_target_n30": int(pack.get("target_n_participants") or 0) >= 30,
        "pilot_ready_for_enrollment": bool(pack.get("pilot_ready_for_enrollment")),
        "human_n30_collected": bool(pack.get("human_n30_gate_met")),
    }
    enrollment_ready = (
        checks["min_curated_items"]
        and checks["all_dose_reviews_approved"]
        and checks["protocol_target_n30"]
        and checks["pilot_ready_for_enrollment"]
    )
    return {
        "schema": "warmth_trigger_pilot_readiness_v1",
        "enrollment_ready": enrollment_ready,
        "human_data_collection_complete": checks["human_n30_collected"],
        "checks": checks,
        "note_ko": (
            "enrollment_ready=참가자 모집·세션 시작 가능. "
            "human_n30_collected는 아직 false가 정상(실측 전)."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack-json", type=Path, default=DEFAULT_PACK)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict", action="store_true", help="Exit 1 if enrollment not ready.")
    args = ap.parse_args()

    pack = _load_json(args.pack_json)
    report = evaluate_readiness(pack)
    report["pack_ref"] = str(args.pack_json)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "enrollment_ready": report["enrollment_ready"]}))
    if args.strict and not report["enrollment_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
