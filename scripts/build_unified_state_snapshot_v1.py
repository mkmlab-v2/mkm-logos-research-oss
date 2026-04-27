# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.9, K:0.4, M:0.7}
# Balance: 95
# Purpose: Normalize key ops artifacts into a unified state schema.
# Keywords: unified, schema, state, control_tower, health, checklist
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _as_list(v: Any) -> list[str]:
    if isinstance(v, list):
        return [str(x) for x in v]
    if v is None:
        return []
    return [str(v)]


def _status_from_bool(ok: bool, ok_value: str = "OK", bad_value: str = "BLOCKED") -> str:
    return ok_value if ok else bad_value


def build_snapshot(
    control_tower: dict[str, Any],
    health: dict[str, Any],
    checklist: dict[str, Any],
    go_nogo: dict[str, Any],
) -> dict[str, Any]:
    ct_readiness = (control_tower.get("promotion_readiness") or {}).get("status")
    ct_reasons = _as_list((control_tower.get("promotion_readiness") or {}).get("reasons"))
    ct_panel = control_tower.get("status_panel") or {}
    ct_stage = "BTRACK_PROMOTION" if str(ct_readiness or "").upper() in {"GO_READY", "READY"} else "BTRACK_HOLD"

    hs_summary = health.get("summary") or {}
    hs_ok = bool(hs_summary.get("ops_ready"))
    hs_reasons: list[str] = []
    if not bool(hs_summary.get("all_tasks_ok", False)):
        hs_reasons.append("tasks_not_ok")
    if not bool(hs_summary.get("all_artifacts_ok", False)):
        hs_reasons.append("artifacts_not_ok")
    hs_stage = "OPS_HEALTHY" if hs_ok else "OPS_DEGRADED"

    ck_summary = checklist.get("summary") or {}
    ck_ok = bool(ck_summary.get("all_required_completed"))
    ck_stage = checklist.get("current_status", {}).get("recommended_stage") or "UNKNOWN_STAGE"
    ck_pending = [str(x.get("id")) for x in (checklist.get("checklist") or []) if not bool(x.get("done"))]

    gn_result = go_nogo.get("result") or {}
    gn_stage = gn_result.get("recommended_stage") or "UNKNOWN_STAGE"
    gn_overall = str(gn_result.get("overall_go_no_go") or "UNKNOWN")
    gn_ok = gn_overall == "GO"
    gn_reasons = _as_list(gn_result.get("failed_reasons"))

    return {
        "schema": "unified_state_snapshot_v1",
        "schema_version": 1,
        "generated_at_utc": _now_utc(),
        "state_nodes": {
            "control_tower": {
                "status": str(ct_readiness or "UNKNOWN"),
                "stage": ct_stage,
                "readiness": str(ct_readiness or "UNKNOWN"),
                "reasons": ct_reasons,
                "source_generated_at_utc": control_tower.get("generated_at_utc"),
                "meta": {
                    "signal_light": ct_panel.get("signal_light"),
                    "gate_decision": ct_panel.get("gate_decision"),
                },
            },
            "automation_health": {
                "status": _status_from_bool(hs_ok),
                "stage": hs_stage,
                "readiness": _status_from_bool(hs_ok, "READY", "NOT_READY"),
                "reasons": hs_reasons,
                "source_generated_at_utc": health.get("generated_at_utc"),
                "meta": {
                    "all_tasks_ok": hs_summary.get("all_tasks_ok"),
                    "all_artifacts_ok": hs_summary.get("all_artifacts_ok"),
                    "ops_ready": hs_summary.get("ops_ready"),
                },
            },
            "a_track_checklist": {
                "status": _status_from_bool(ck_ok, "COMPLETE", "IN_PROGRESS"),
                "stage": str(ck_stage),
                "readiness": _status_from_bool(ck_ok, "READY", "NOT_READY"),
                "reasons": ck_pending,
                "source_generated_at_utc": checklist.get("generated_at_utc"),
                "meta": {
                    "completed_total": ck_summary.get("completed_total"),
                    "required_total": ck_summary.get("required_total"),
                    "next_action": ck_summary.get("next_action"),
                },
            },
            "a_track_go_nogo": {
                "status": gn_overall,
                "stage": str(gn_stage),
                "readiness": _status_from_bool(gn_ok, "READY", "NOT_READY"),
                "reasons": gn_reasons,
                "source_generated_at_utc": (go_nogo.get("meta") or {}).get("generated_at_utc"),
                "meta": {
                    "overall_go_no_go": gn_overall,
                    "recommended_stage": gn_stage,
                },
            },
        },
        "summary": {
            "status": _status_from_bool(hs_ok and str(ct_readiness or "").upper() == "GO_READY"),
            "stage": str(gn_stage),
            "readiness": _status_from_bool(hs_ok and gn_overall in {"GO", "HOLD"}, "PARTIAL_READY", "NOT_READY"),
            "reasons": gn_reasons if gn_reasons else hs_reasons,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build unified state snapshot from core operational artifacts.")
    ap.add_argument("--control-tower", type=Path, default=ROOT / "docs/final/artifacts/control_tower_latest.json")
    ap.add_argument("--health", type=Path, default=ROOT / "docs/final/artifacts/btrack_automation_health_snapshot_latest.json")
    ap.add_argument("--checklist", type=Path, default=ROOT / "docs/final/artifacts/a_track_hold_release_checklist_v1_latest.json")
    ap.add_argument("--go-nogo", type=Path, default=ROOT / "docs/final/artifacts/a_track_go_nogo_status_latest.json")
    ap.add_argument("--out", type=Path, default=ROOT / "docs/final/artifacts/unified_state_snapshot_v1_latest.json")
    args = ap.parse_args()

    out = args.out if args.out.is_absolute() else ROOT / args.out
    payload = build_snapshot(
        control_tower=_load(args.control_tower if args.control_tower.is_absolute() else ROOT / args.control_tower),
        health=_load(args.health if args.health.is_absolute() else ROOT / args.health),
        checklist=_load(args.checklist if args.checklist.is_absolute() else ROOT / args.checklist),
        go_nogo=_load(args.go_nogo if args.go_nogo.is_absolute() else ROOT / args.go_nogo),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out}")
    print(f"summary.status={payload['summary']['status']}")
    print(f"summary.stage={payload['summary']['stage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
