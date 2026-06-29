#!/usr/bin/env python3
"""Gate: A-code operator-assist lane remains fixed ([HYPO] · non-gating)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LANE = ROOT / "docs/final/artifacts/a_code_operator_assist_lane_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/a_code_operator_assist_lane_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def evaluate_gate(lane: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "lane_schema_ok": lane.get("schema") == "a_code_operator_assist_lane_v1",
        "operator_lane_ready": lane.get("operator_lane_ready") is True,
        "lane_status_fixed": lane.get("lane_status") == "OPERATOR_ASSIST_FIXED",
        "research_only": lane.get("research_only") is True,
        "non_gating": lane.get("non_gating") is True,
        "track_wall_blocks_promotion": (lane.get("track_wall") or {}).get("track_a_auto_promotion") is False,
    }
    pass_count = sum(1 for v in checks.values() if v)
    total = len(checks)
    decision = "PASS_OPERATOR_ASSIST" if all(checks.values()) else "HOLD_RESEARCH"

    return {
        "schema": "a_code_operator_assist_lane_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "rq_id": "RQ-031",
        "research_only": True,
        "non_gating": True,
        "summary": {
            "decision": decision,
            "pass_count": pass_count,
            "total": total,
            "operator_lane_ready": lane.get("operator_lane_ready"),
            "lane_status": lane.get("lane_status"),
        },
        "checks": checks,
        "track_wall": lane.get("track_wall") or {},
        "operator_hint_ko": (
            "운영자 보조 레인 게이트 PASS — Track A/live 승격 아님 [HYPO]"
            if decision == "PASS_OPERATOR_ASSIST"
            else "운영자 보조 레인 게이트 미통과 — 번들 재실행 [HYPO]"
        ),
        "source": str(DEFAULT_LANE.relative_to(ROOT)).replace("\\", "/"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", type=Path, default=DEFAULT_LANE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    lane = _read(args.lane)
    if not lane:
        raise SystemExit(f"missing lane artifact: {args.lane}")

    report = evaluate_gate(lane)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"OK: {args.out} decision={report['summary']['decision']} "
        f"{report['summary']['pass_count']}/{report['summary']['total']}"
    )
    if args.strict and report["summary"]["decision"] != "PASS_OPERATOR_ASSIST":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
