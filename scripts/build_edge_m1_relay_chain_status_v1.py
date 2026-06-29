#!/usr/bin/env python3
"""Aggregate M1 bench + live bridge + inter-agent status (B-track relay chain)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/edge_m1_relay_chain_status_latest.json"
BENCH = ROOT / "reports/edge_m1_guardrail_bench_latest.json"
BRIDGE_RES = ROOT / "reports/pet_companion_device_bridge_live_response_latest.json"
BRIDGE_REQ = ROOT / "reports/pet_companion_device_bridge_live_request_latest.json"
INTER_AGENT = ROOT / "docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json"
AI_POINTER = ROOT / "docs/final/artifacts/mkm_ai_status_pointer_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def build(*, inter_agent_strict_exit: int | None) -> dict[str, Any]:
    bench = _read(BENCH)
    bridge_res = _read(BRIDGE_RES)
    bridge_req = _read(BRIDGE_REQ)
    inter = _read(INTER_AGENT)
    ai = _read(AI_POINTER)

    live_ok = (
        isinstance(bridge_res, dict)
        and bridge_res.get("schema") == "pet_companion_device_memory_bridge_response_v1"
        and bridge_res.get("status") in ("GUIDED_CHECKLIST", "OK", "ABSTAIN")
    )
    inter_pytest_ok = inter_agent_strict_exit == 0 if inter_agent_strict_exit is not None else None
    core_ready = bool(inter.get("rq_019_milestones_core_ready")) if inter else False

    watch_reasons: list[str] = []
    if not live_ok:
        watch_reasons.append("live_bridge_response_missing_or_invalid")
    if inter_agent_strict_exit not in (None, 0):
        watch_reasons.append("inter_agent_strict_exit_nonzero")
    if ai and ai.get("status") == "HOLD_OPERATIONAL_V1":
        watch_reasons.append("mkm_ai_hold_operational_v1")
    if not core_ready:
        watch_reasons.append("rq_019_milestones_core_ready_false")

    combined_pass = bench is not None and live_ok and not watch_reasons
    b_track_lane_go = bool(bench is not None and live_ok)
    b_track_watch_reasons: list[str] = []
    if not core_ready:
        b_track_watch_reasons.append("rq_019_milestones_core_ready_false")
    if inter_agent_strict_exit not in (None, 0):
        b_track_watch_reasons.append("inter_agent_strict_exit_nonzero")
    if ai and ai.get("status") == "HOLD_OPERATIONAL_V1":
        b_track_watch_reasons.append("mkm_ai_hold_operational_v1_track_a_wall")

    return {
        "schema": "edge_m1_relay_chain_status_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "final_action_hint": "WATCH" if watch_reasons else "GO_RESEARCH_BENCH_OK",
        "watch_reasons": watch_reasons,
        "combined_pass": combined_pass,
        "b_track_lane_go": b_track_lane_go,
        "b_track_final_action_hint": (
            "GO_BTRACK_PET_M1_PILOT" if b_track_lane_go and not b_track_watch_reasons else "WATCH_BTRACK"
        ),
        "b_track_watch_reasons": b_track_watch_reasons,
        "track_a_promotion_blocked": True,
        "m1_bench_present": bench is not None,
        "live_bridge_ok": live_ok,
        "live_bridge_status": bridge_res.get("status") if bridge_res else None,
        "live_bridge_base_url": bridge_res.get("_mkm_meta", {}).get("base_url")
        if isinstance(bridge_res.get("_mkm_meta"), dict)
        else None,
        "inter_agent_strict_exit": inter_agent_strict_exit,
        "inter_agent_pytest_strict_ok": inter_pytest_ok,
        "rq_019_milestones_core_ready": core_ready,
        "mkm_ai_status": ai.get("status") if ai else None,
        "paths": {
            "bench_json": str(BENCH),
            "bridge_request_json": str(BRIDGE_REQ) if bridge_req else None,
            "bridge_response_json": str(BRIDGE_RES) if bridge_res else None,
            "inter_agent_status_json": str(INTER_AGENT) if inter else None,
        },
        "track_wall": {
            "note": "Not Track A compression KPI or commercial LLM Final; edge % transplant forbidden.",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--inter-agent-strict-exit",
        type=int,
        default=None,
        help="Exit code from build_mkm_inter_agent_encoding_status --strict-exit",
    )
    args = ap.parse_args()
    doc = build(inter_agent_strict_exit=args.inter_agent_strict_exit)
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "combined_pass": doc["combined_pass"]}, ensure_ascii=False))
    return 0 if doc["combined_pass"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
