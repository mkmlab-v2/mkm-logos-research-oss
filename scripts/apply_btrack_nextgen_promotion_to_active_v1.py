#!/usr/bin/env python3
"""Apply Next-Gen Golden-40 eval report to Track A ACTIVE (human gate only).

Requires promotion packet export_prep_ready and --human-approve-promotion.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PACKET = ROOT / "reports/btrack_nextgen_promotion_candidate_packet_v1_latest.json"
SIGNOFF = ROOT / "reports/btrack_nextgen_promotion_signoff_v1_latest.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--packet-json", type=Path, default=PACKET)
    ap.add_argument("--human-approve-promotion", action="store_true")
    ap.add_argument("--reviewer", default="commander")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.human_approve_promotion:
        print("ABORT: --human-approve-promotion required for ACTIVE replacement.")
        return 2

    if not args.packet_json.is_file():
        print(f"ABORT: missing packet {args.packet_json}", file=sys.stderr)
        return 1

    packet = _load(args.packet_json)
    if not packet.get("export_prep_ready"):
        print(
            json.dumps(
                {
                    "abort": True,
                    "reason": "export_prep_ready false",
                    "next_action": packet.get("next_action"),
                },
                ensure_ascii=False,
            )
        )
        return 3

    selected = packet.get("selected_arm_active_parity") or packet.get("selected_arm")
    if packet.get("active_apply_recommended") is False and not args.dry_run:
        print(
            json.dumps(
                {
                    "abort": True,
                    "reason": "active_apply_recommended false (frozen tie or no strict 41k ON beat)",
                    "selected_arm_active_parity": packet.get("selected_arm_active_parity"),
                    "selected_arm_research_uplift": packet.get(
                        "selected_arm_research_uplift"
                    ),
                    "hint": "Keep research uplift in B-track packet; do not overwrite ACTIVE.",
                },
                ensure_ascii=False,
            )
        )
        return 6
    cand = next((c for c in packet.get("candidates") or [] if c.get("arm_id") == selected), None)
    if not cand or not cand.get("gates", {}).get("auto_track_a_promotion_allowed"):
        print("ABORT: selected arm missing or gates not satisfied", file=sys.stderr)
        return 4

    eval_path = ROOT / str(cand["evidence_path"]).replace("/", "\\")
    report_path = eval_path.with_suffix(".report.json")
    if not report_path.is_file():
        print(f"ABORT: missing eval report {report_path}", file=sys.stderr)
        return 1

    report = _load(report_path)
    rc = report.get("run_config") or {}
    if rc.get("use_master_codebook_lexicon_v1") is not True:
        print(
            json.dumps(
                {
                    "abort": True,
                    "reason": "candidate_report_is_41k_off_experimental",
                    "hint": "Charter: legacy_41k_disconnect_allowed false until commander "
                    "releases TRACK_A_STRICT_LOCK. Keep beat evidence in B-track packet only.",
                    "run_config_use_master_codebook": rc.get(
                        "use_master_codebook_lexicon_v1"
                    ),
                },
                ensure_ascii=False,
            )
        )
        return 5

    signoff = {
        "schema": "btrack_nextgen_promotion_signoff_v1_apply",
        "approved_at_utc": _utc(),
        "reviewer": args.reviewer,
        "selected_arm": selected,
        "packet_pointer": str(args.packet_json.relative_to(ROOT)).replace("\\", "/"),
        "beat_check": cand.get("beat_check"),
    }

    if args.dry_run:
        print(json.dumps({"dry_run": True, "signoff": signoff}, ensure_ascii=False))
        return 0

    backup = ACTIVE.with_suffix(".json.pre_nextgen_promotion_backup")
    if ACTIVE.is_file():
        shutil.copy2(ACTIVE, backup)
        print(f"BACKUP: {backup.relative_to(ROOT)}")

    promoted = dict(report)
    profile = promoted.setdefault("active_profile", {})
    if isinstance(profile, dict):
        profile["sla_track"] = "nextgen_research_promotion"
        profile["promoted_from"] = selected
        profile["promoted_at_utc"] = _utc()
        profile["promotion_signoff"] = str(SIGNOFF.relative_to(ROOT)).replace("\\", "/")

    ACTIVE.write_text(json.dumps(promoted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SIGNOFF.write_text(json.dumps(signoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"applied": str(ACTIVE), "selected_arm": selected}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
