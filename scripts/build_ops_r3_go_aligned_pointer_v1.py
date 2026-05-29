#!/usr/bin/env python3
"""Map ops 'R3 GO aligned' briefing labels to on-disk artifact paths (Fact-Lock pointer)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/ops_r3_go_aligned_pointer_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve().as_posix())


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _lane(path: Path, *, role: str, go_keys: list[str], writers: list[str]) -> dict[str, Any]:
    obj = _read_json(path)
    lane: dict[str, Any] = {
        "role": role,
        "relative_path": _rel(path),
        "exists": obj is not None,
        "writers": writers,
        "go_aligned_fields": go_keys,
    }
    if obj is not None:
        lanes = obj.get("lanes") if isinstance(obj.get("lanes"), dict) else {}
        if "live_patrol" in lanes:
            lp = lanes.get("live_patrol") or {}
            lane["live_patrol_go"] = lp.get("go")
            lane["live_patrol_ok"] = lp.get("ok")
        if "vps_go_scp" in lanes:
            vps = lanes.get("vps_go_scp") or {}
            lane["vps_go_scp_aligned"] = vps.get("aligned")
            lane["vps_go_scp_ok"] = vps.get("ok")
        if obj.get("latest_state", {}).get("stability", {}).get("current_decision"):
            lane["orchestrator_decision"] = obj["latest_state"]["stability"]["current_decision"]
        if obj.get("overall_ok") is not None:
            lane["overall_ok"] = obj.get("overall_ok")
        lane["generated_at_utc"] = obj.get("generated_at_utc") or obj.get("ts_utc")
    return lane


def build_pointer() -> dict[str, Any]:
    parallel = ROOT / "reports/parallel_ops_round_mission_log_r3_latest.json"
    companion = ROOT / "docs/final/artifacts/companion_ecosystem_conditional_go_plus_report_latest.json"
    ko_gold = ROOT / "reports/constitution/btrack_pilot/comp_logos_rag_retrieval_r3_ko_gold_v1_latest.json"
    en_r3 = ROOT / "reports/constitution/btrack_pilot/comp_logos_rag_retrieval_r3_latest.json"

    doc: dict[str, Any] = {
        "schema": "ops_r3_go_aligned_pointer_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "interpretation": (
            "Mission-log 'R3 GO aligned' refers to parallel ops lane bundle (live_patrol GO + "
            "vps_go_scp aligned), NOT prophecy A-track promote or live trading ON."
        ),
        "track_wall": {
            "prophecy_auto_promote": False,
            "live_trading_on": False,
            "logos_non_gating": True,
        },
        "primary_ops_bundle": _rel(parallel),
        "lanes": {
            "parallel_ops_mission_log_r3": _lane(
                parallel,
                role="ops_scheduler_panel_go_aligned",
                go_keys=["lanes.live_patrol.go", "lanes.vps_go_scp.aligned"],
                writers=["MISSION_LOG.md parallel round R3", "manual ops closure"],
            ),
            "companion_ecosystem_conditional_go_plus": _lane(
                companion,
                role="orchestrator_conditional_go_stability",
                go_keys=["latest_state.stability.current_decision"],
                writers=["scripts/build_mkm_conditional_go_plus_report_v2.py"],
            ),
            "logos_rag_retrieval_r3_ko_gold": _lane(
                ko_gold,
                role="logos_track_b_r3_ko_gold_eval",
                go_keys=["overall_ok", "ko_proxy_pass"],
                writers=["scripts/run_logos_rag_retrieval_r3_ko_gold_v1.py"],
            ),
            "logos_rag_retrieval_r3_en": _lane(
                en_r3,
                role="logos_track_b_r3_en_eval",
                go_keys=["hybrid_mean", "ko_mean"],
                writers=["scripts/run_logos_rag_retrieval_r3_v1.py (if present)"],
            ),
        },
    }
    primary = doc["lanes"]["parallel_ops_mission_log_r3"]
    doc["go_aligned_summary"] = {
        "parallel_ops_ok": bool(primary.get("live_patrol_go") == "GO" and primary.get("vps_go_scp_aligned") is True),
        "note": "Use parallel_ops when briefing says 'GO aligned'; Logos R3 JSON is separate research lane.",
    }
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build R3 GO aligned artifact pointer")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    doc = build_pointer()
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "wrote": str(out), "primary": doc["primary_ops_bundle"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
