#!/usr/bin/env python3
"""Apply promotion candidate to Track A active compression report (human gate).

Requires ``MULTILENS_ULTRA_COMPRESSION_PROMOTION_CANDIDATE_V1.json`` from
``run_ultra_compression_promotion_sweep_v1.py``.

Default: abort unless ``--human-approve-promotion`` and gates allow OR
``--accept-min-j-waiver`` with floor + jaccard-drop still passing.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_PROMOTION_CANDIDATE_V1.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
SIGNOFF_DEFAULT = ROOT / "docs/final/artifacts/multilens_ultra_compression_track_a_promotion_signoff_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate-json", type=Path, default=CANDIDATE)
    ap.add_argument("--active-out", type=Path, default=ACTIVE)
    ap.add_argument("--human-approve-promotion", action="store_true")
    ap.add_argument(
        "--accept-min-j-waiver",
        action="store_true",
        help="Allow promotion when floor+jaccard-drop pass but min_j below frozen Track A.",
    )
    ap.add_argument("--reviewer", default="commander")
    ap.add_argument("--note", default="RQ-016 ssot relaxed cap promotion apply")
    ap.add_argument("--signoff-json", type=Path, default=SIGNOFF_DEFAULT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.human_approve_promotion:
        print("ABORT: --human-approve-promotion required for Track A active replacement.")
        return 2

    cand_path = args.candidate_json
    if not cand_path.is_file():
        print(f"ABORT: missing candidate {cand_path}")
        return 1

    doc = _load(cand_path)
    env = doc.get("promotion_candidate_envelope") or {}
    gates = env.get("selected_promotion_gates") or {}
    auto_ok = bool(gates.get("auto_track_a_promotion_allowed"))
    bench_ok = bool(gates.get("bench_promotion_eligible"))
    floor_ok = bool(gates.get("ultra_saving_policy_ok"))
    drop_ok = bool(gates.get("jaccard_drop_within_decision_threshold"))
    min_j_ok = bool(gates.get("min_jaccard_not_below_track_a"))
    waiver_path = bool(args.accept_min_j_waiver and floor_ok and drop_ok and not min_j_ok)

    if not auto_ok and not bench_ok and not waiver_path:
        print(
            json.dumps(
                {
                    "abort": True,
                    "reason": "promotion_gates_not_satisfied",
                    "promotion_gates": gates,
                    "hint": (
                        "Re-run promotion sweep, or pass --accept-min-j-waiver for min-J tradeoff."
                    ),
                },
                ensure_ascii=False,
            )
        )
        return 3

    active_out = args.active_out.resolve()
    backup = active_out.with_suffix(".json.pre_promotion_backup")
    signoff = {
        "schema": "multilens_ultra_compression_track_a_promotion_signoff_v1",
        "approved_at_utc": _utc(),
        "reviewer": args.reviewer,
        "note": args.note,
        "candidate_path": str(cand_path.relative_to(ROOT)).replace("\\", "/"),
        "selected_variant_id": env.get("selected_variant_id"),
        "selected_run_config": env.get("selected_run_config"),
        "promotion_gates_at_apply": gates,
        "human_approval": {
            "commander_approve_promotion": True,
            "accept_min_j_waiver": bool(args.accept_min_j_waiver),
            "auto_track_a_promotion_allowed_at_apply": auto_ok,
        },
        "active_report_path": str(active_out.relative_to(ROOT)).replace("\\", "/"),
    }

    if args.dry_run:
        print(json.dumps({"dry_run": True, "signoff": signoff}, ensure_ascii=False))
        return 0

    if active_out.is_file():
        shutil.copy2(active_out, backup)
        print(f"BACKUP: {backup.relative_to(ROOT)}")

    promoted = dict(doc)
    promoted.pop("promotion_candidate_envelope", None)
    profile = promoted.setdefault("active_profile", {})
    if isinstance(profile, dict):
        profile["sla_track"] = "universal"
        profile["promoted_from_candidate_at_utc"] = _utc()
        profile["promoted_variant_id"] = env.get("selected_variant_id")
        profile["promotion_signoff"] = str(args.signoff_json.relative_to(ROOT)).replace("\\", "/")

    active_out.parent.mkdir(parents=True, exist_ok=True)
    active_out.write_text(json.dumps(promoted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.signoff_json.parent.mkdir(parents=True, exist_ok=True)
    args.signoff_json.write_text(json.dumps(signoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cm = promoted.get("compression_metrics") or {}
    print(
        json.dumps(
            {
                "applied": str(active_out.relative_to(ROOT)).replace("\\", "/"),
                "signoff": str(args.signoff_json.relative_to(ROOT)).replace("\\", "/"),
                "global_token_saving_rate": cm.get("global_token_saving_rate"),
                "min_jaccard": cm.get("min_reconstruction_fidelity_jaccard"),
                "waiver_used": waiver_path,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
