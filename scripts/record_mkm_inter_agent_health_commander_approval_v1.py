#!/usr/bin/env python3
"""Record commander approval for B-track health/hangul domain relax (not Track A bench)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CANDIDATE = ROOT / "docs/final/artifacts/mkm_inter_agent_health_domain_signoff_candidate_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_health_domain_commander_approval_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build(*, approval_note: str = "") -> dict[str, Any]:
    if not CANDIDATE.is_file():
        raise FileNotFoundError(f"missing candidate: {CANDIDATE}")
    cand = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    variant = str(cand.get("proposed_variant_id") or "health_hangul_relaxed_cap_0.50")
    run_cfg = cand.get("proposed_run_config")
    if not isinstance(run_cfg, dict):
        run_cfg = {"domain_relaxed_max_saving_overrides": {"health": 0.5, "hangul": 0.5}}

    return {
        "schema": "mkm_inter_agent_health_domain_commander_approval_v1",
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "hypothesis_tier": "B",
        "commander_approved": True,
        "approved_at_utc": _utc_now(),
        "approval_scope": "b_track_inter_agent_v2_routing_only",
        "track_a_bench_promotion_approved": False,
        "does_not_replace_track_a_active": True,
        "candidate_pointer": (
            CANDIDATE.relative_to(ROOT).as_posix()
            if CANDIDATE.is_relative_to(ROOT)
            else str(CANDIDATE)
        ),
        "approved_variant_id": variant,
        "approved_run_config": run_cfg,
        "sweep_evidence": cand.get("sweep_evidence"),
        "bench_promotion_eligible_without_human": bool(
            cand.get("bench_promotion_eligible_without_human")
        ),
        "boundary_ack": (
            "Commander approved B-track inter-agent use of health/hangul relaxed caps only. "
            "Track A frozen bench (~47%) and multilens signoff top5 remain unchanged. "
            "No production SLA or lossless claim."
        ),
        "approval_note": (approval_note or "").strip() or None,
        "routing_profile_wired": "b_track_domain_relax",
        "v2_compress_field": "routing_profile",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--note", default="", help="Optional one-line approval note.")
    args = ap.parse_args()
    doc = build(approval_note=args.note)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out_json), "approved_variant_id": doc["approved_variant_id"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
