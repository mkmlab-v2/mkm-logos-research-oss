#!/usr/bin/env python3
"""Build adopt_limited rehearsal result for external anchor policy."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_TIERING = ART / "external_bible_anchor_tiering_latest.json"
DEFAULT_APPLY_GATE = ART / "external_bible_crossref_threshold_apply_gate_latest.json"
DEFAULT_APPLY_APPROVAL = ART / "external_bible_crossref_threshold_apply_approval_latest.json"
DEFAULT_CORE100_GATE = ART / "core100_node_ref_map_quality_gate_latest.json"
DEFAULT_OUT = ART / "external_bible_anchor_adopt_limited_rehearsal_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _parse_iso_utc(s: str) -> datetime | None:
    txt = str(s or "").strip()
    if not txt:
        return None
    if txt.endswith("Z"):
        txt = txt[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(txt)
    except ValueError:
        return None
    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tiering-json", type=Path, default=DEFAULT_TIERING)
    ap.add_argument("--apply-gate-json", type=Path, default=DEFAULT_APPLY_GATE)
    ap.add_argument("--apply-approval-json", type=Path, default=DEFAULT_APPLY_APPROVAL)
    ap.add_argument("--core100-gate-json", type=Path, default=DEFAULT_CORE100_GATE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    tiering = _read_json(args.tiering_json)
    apply_gate = _read_json(args.apply_gate_json)
    apply_approval = _read_json(args.apply_approval_json)
    core100 = _read_json(args.core100_gate_json)

    tier_counts = tiering.get("tier_counts") if isinstance(tiering.get("tier_counts"), dict) else {}
    t1 = int(tier_counts.get("tier1_high_confidence") or 0)
    t2 = int(tier_counts.get("tier2_exploration") or 0)
    core100_pass = bool(((core100.get("gate") or {}).get("pass")))
    can_apply = bool(apply_gate.get("can_apply_thresholds"))
    approved = bool(apply_approval.get("approved"))

    expiry_dt = _parse_iso_utc(str(apply_approval.get("expires_at_utc") or ""))
    now = datetime.now(timezone.utc)
    approval_not_expired = bool(expiry_dt and expiry_dt > now)

    checks = {
        "tier1_exists": t1 > 0,
        "tier2_exists_for_shadow": t2 > 0,
        "core100_quality_pass": core100_pass,
        "apply_gate_can_apply": can_apply,
        "approval_granted": approved,
        "approval_not_expired": approval_not_expired,
    }
    # Adopt-limited requires manual approval chain + tier1 availability.
    adopt_ready = all(checks[k] for k in ("tier1_exists", "core100_quality_pass", "apply_gate_can_apply", "approval_granted", "approval_not_expired"))
    adopt_blockers = [k for k, v in checks.items() if not bool(v) and k != "tier2_exists_for_shadow"]

    # Shadow rehearsal is intentionally lighter: no one-shot approval required.
    shadow_ready = bool(checks["tier2_exists_for_shadow"]) and bool(checks["core100_quality_pass"])
    shadow_blockers = [
        k
        for k in ("tier2_exists_for_shadow", "core100_quality_pass")
        if not bool(checks.get(k))
    ]

    out = {
        "schema": "external_bible_anchor_adopt_limited_rehearsal_v1",
        "generated_at_utc": _iso_now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "inputs": {
            "tiering_json": str(args.tiering_json).replace("\\", "/"),
            "apply_gate_json": str(args.apply_gate_json).replace("\\", "/"),
            "apply_approval_json": str(args.apply_approval_json).replace("\\", "/"),
            "core100_gate_json": str(args.core100_gate_json).replace("\\", "/"),
        },
        "checks": checks,
        "adopt_limited": {
            "ready": adopt_ready,
            "blockers": adopt_blockers,
        },
        "shadow_rehearsal": {
            "ready": shadow_ready,
            "blockers": shadow_blockers,
        },
        "status": "READY_ADOPT_LIMITED" if adopt_ready else ("READY_SHADOW_REHEARSAL" if shadow_ready else "NOT_READY"),
        "recommended_next": (
            "run_adopt_limited_rollout"
            if adopt_ready
            else ("run_shadow_rehearsal_with_tier2" if shadow_ready else "keep_monitor_only_and_collect_tier1")
        ),
        "summary": {
            "tier1_count": t1,
            "tier2_count": t2,
            "policy_action_current": tiering.get("policy_action"),
            "policy_decision_current": tiering.get("decision"),
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json).replace("\\", "/"),
                "status": out["status"],
                "recommended_next": out["recommended_next"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
