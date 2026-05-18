#!/usr/bin/env python3
"""Post-commander-approval bundle: health B-track wired ops evidence (INTERNAL)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

APPROVAL = ROOT / "docs/final/artifacts/mkm_inter_agent_health_domain_commander_approval_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_post_commander_approval_bundle_latest.json"
DIALOGUE_SUMMARY = ROOT / "docs/final/artifacts/mkm_inter_agent_dialogue_health_approved_latest.json"
STATUS = ROOT / "docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build(*, dialogue_turns: int = 4) -> dict[str, Any]:
    if not APPROVAL.is_file():
        raise FileNotFoundError(f"missing approval: {APPROVAL}")
    approval = _load(APPROVAL)
    if not approval.get("commander_approved"):
        raise ValueError("commander_approved is not true")

    from scripts.run_mkm_inter_agent_dialogue_mock_v1 import run_dialogue

    dialogue = run_dialogue(
        turns=dialogue_turns,
        routing_profile="b_track_domain_relax",
        scenario="health",
    )
    DIALOGUE_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    DIALOGUE_SUMMARY.write_text(
        json.dumps(dialogue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    status_doc: dict[str, Any] | None = _load(STATUS) if STATUS.is_file() else None
    ratios: list[float] = []
    for row in dialogue.get("transcript") or []:
        if not isinstance(row, dict):
            continue
        m = (row.get("compress") or {}).get("compression_metrics") or {}
        if m.get("savings_ratio") is not None:
            ratios.append(float(m["savings_ratio"]))
    avg_savings = round(sum(ratios) / len(ratios), 6) if ratios else None

    return {
        "schema": "mkm_inter_agent_post_commander_approval_bundle_v1",
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "hypothesis_tier": "B",
        "commander_approved": True,
        "approval_pointer": APPROVAL.relative_to(ROOT).as_posix(),
        "approved_variant_id": approval.get("approved_variant_id"),
        "track_a_bench_promotion_approved": approval.get("track_a_bench_promotion_approved"),
        "rq_019_external_closed": False,
        "legal_signoff_required_for_rq019_closed": True,
        "ops_ready": {
            "b_track_health_dialogue": dialogue.get("all_expand_packet_only") is True
            and dialogue.get("all_expand_ok") is True,
            "routing_profile": "b_track_domain_relax",
            "dialogue_summary": DIALOGUE_SUMMARY.relative_to(ROOT).as_posix(),
            "avg_savings_ratio": avg_savings,
        },
        "encoding_status": {
            "rq_019_milestones_core_ready": status_doc.get("rq_019_milestones_core_ready")
            if status_doc
            else None,
            "health_domain_commander_approved": status_doc.get("health_domain_commander_approved")
            if status_doc
            else None,
        },
        "boundary_ack": (
            "Commander approved B-track inter-agent health caps only. "
            "Track A frozen bench unchanged. RQ-019 stays OPEN until legal on external copy."
        ),
        "recommended_next": [
            "Legal review: mkm_inter_agent_ir_snippet_v1.md + PUBLIC_FACING v1.7",
            "Optional: live HTTP demo for internal stakeholders (stub port 8011)",
            "Do not promote health_hangul_relaxed_cap_0.50 to Track A without 0.47 floor re-sweep",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dialogue-turns", type=int, default=4)
    ap.add_argument("--refresh-status", action="store_true")
    args = ap.parse_args()

    if args.refresh_status:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_mkm_inter_agent_encoding_status_v1.py"), "--skip-pytest"],
            cwd=str(ROOT),
        )
        if proc.returncode != 0:
            return int(proc.returncode)

    doc = build(dialogue_turns=args.dialogue_turns)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out_json), "ops_ready": doc["ops_ready"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
