#!/usr/bin/env python3
"""Commander approval bundle: v1_price_only prod score + refresh Phase3 sidecar.

Track A / live trading remain OFF unless separately approved.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"
DEFAULT_SIGNOFF = ART / "btrack_v1_price_only_human_signoff_v1_latest.json"
DEFAULT_HR = REPORTS / "btrack_v1_price_only_human_review_pack_v1_latest.json"
APPLY_SCORE = ROOT / "scripts/apply_btrack_v1_price_only_prod_score_v1.py"
APPLY_PHASE3 = ROOT / "scripts/apply_btrack_phase3_human_approval_v1.py"
SIDECAR = ROOT / "scripts/build_btrack_prophecy_score_insight_sidecar_stub_v1.py"
EVAL_HIT = ROOT / "scripts/eval_prophecy_hit_rate_v1.py"
DEFAULT_SCORE = ART / "btrack_prophecy_score_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    cp = subprocess.run(cmd, cwd=str(ROOT), check=False)
    if cp.returncode != 0:
        raise SystemExit(cp.returncode)


def _patch_hr(hr_path: Path, signoff_ref: str, reviewer: str, note: str, apply_report: Path) -> None:
    if not hr_path.is_file():
        return
    hr = json.loads(hr_path.read_text(encoding="utf-8-sig"))
    d = hr.setdefault("decision", {})
    if not isinstance(d, dict):
        return
    d["human_commander_override"] = "APPROVED_V1_PRICE_ONLY_PROD"
    d["apply_to_prod_score_json"] = True
    d["track_a_promotion"] = False
    d["auto_promote"] = False
    d["human_decision"] = "APPROVED_PROD_APPLY_COMMANDER_OVERRIDE"
    d["human_approved_at_utc"] = _now()
    d["human_reviewer"] = reviewer
    d["human_note_ko"] = note
    d["prod_apply_report_ref"] = str(apply_report.relative_to(ROOT)).replace("\\", "/")
    hr["human_signoff_ref"] = signoff_ref
    hr_path.write_text(json.dumps(hr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PATCHED: {hr_path.resolve()}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reviewer", default="PRO")
    ap.add_argument(
        "--note",
        default="지휘관 승인: v1_price_only prod score 적용(30d ALERT_1 override); Phase3 aux 유지; Track A OFF.",
    )
    ap.add_argument("--signoff-out", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--hr-pack", type=Path, default=DEFAULT_HR)
    ap.add_argument("--recent-trading-days", type=int, default=30)
    ap.add_argument("--skip-phase3-refresh", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    signoff_ref = str(args.signoff_out.relative_to(ROOT)).replace("\\", "/")
    if args.dry_run:
        print(json.dumps({"dry_run": True, "signoff": signoff_ref}, ensure_ascii=False))
        return 0

    signoff = {
        "schema": "btrack_v1_price_only_human_signoff_v1",
        "recorded_at_utc": _now(),
        "reviewer": args.reviewer,
        "decision": "APPROVED",
        "scope": {
            "prod_score_json_v1_price_only": True,
            "human_override_30d_alert1": True,
            "phase3_aux_sidecar": True,
            "track_a_promotion": False,
            "live_trading": False,
            "shield_direction_gate": False,
        },
        "note": args.note,
    }
    args.signoff_out.parent.mkdir(parents=True, exist_ok=True)
    args.signoff_out.write_text(json.dumps(signoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.signoff_out.resolve()}")

    py = sys.executable
    apply_report = REPORTS / "btrack_v1_price_only_prod_apply_v1_latest.json"
    _run(
        [
            py,
            str(APPLY_SCORE),
            "--reviewer",
            args.reviewer,
            "--recent-trading-days",
            str(args.recent_trading_days),
        ]
    )

    if not args.skip_phase3_refresh and APPLY_PHASE3.is_file():
        _run([py, str(APPLY_PHASE3), "--reviewer", args.reviewer, "--skip-chain-rerun"])

    if SIDECAR.is_file():
        _run([py, str(SIDECAR)])

    _run(
        [
            py,
            str(EVAL_HIT),
            "--run-mode",
            "price",
            "--score-json",
            str(DEFAULT_SCORE),
            "--headline-instrument",
            "btc",
        ]
    )

    _patch_hr(args.hr_pack, signoff_ref, args.reviewer, args.note, apply_report)

    ld = ROOT / "scripts/log_agent_decision.py"
    if ld.is_file():
        subprocess.run(
            [
                py,
                str(ld),
                "--mission-id",
                "btrack_v1_price_only_prod_apply",
                "--stage",
                "applied",
                "--decision",
                "APPROVED_V1_PRICE_ONLY_PROD",
                "--evidence-path",
                str(apply_report.resolve()),
                "--actor",
                args.reviewer,
                "--note",
                args.note[:200],
            ],
            cwd=str(ROOT),
            check=False,
        )

    print("OK v1_price_only prod score applied; Track A / live trading unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
