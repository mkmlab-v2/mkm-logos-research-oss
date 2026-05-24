#!/usr/bin/env python3
"""Refresh comp_atom04 dryrun JSON from promotion candidate + active report (no apply)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
CANDIDATE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_PROMOTION_CANDIDATE_V1.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    cand = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    active = json.loads(ACTIVE.read_text(encoding="utf-8"))
    env = cand.get("promotion_candidate_envelope") or {}
    gates = env.get("selected_promotion_gates") or {}
    active_cm = active.get("compression_metrics") or {}
    cand_saving = (env.get("selected_report") or {}).get("compression_metrics", {}).get(
        "global_token_saving_rate"
    )
    active_saving = active_cm.get("global_token_saving_rate")

    out = {
        "schema": "comp_atom04_promotion_dryrun_v1",
        "generated_at_utc": _utc(),
        "active_report_untouched": True,
        "human_approve_required": True,
        "candidate_variant": env.get("selected_variant_id"),
        "promotion_gates": gates,
        "candidate_saving_rate": cand_saving,
        "active_saving_rate": active_saving,
        "would_change_active": bool(
            cand_saving is not None
            and active_saving is not None
            and abs(float(cand_saving) - float(active_saving)) > 1e-6
        ),
        "bench_promotion_eligible": gates.get("bench_promotion_eligible"),
        "auto_track_a_promotion_allowed": gates.get("auto_track_a_promotion_allowed"),
        "note": "Sweep may refresh CANDIDATE only; apply aborts without --human-approve-promotion.",
    }
    path = PILOT / "comp_atom04_promotion_dryrun_v1.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(path), "would_change_active": out["would_change_active"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
