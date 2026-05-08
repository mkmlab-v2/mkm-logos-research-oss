#!/usr/bin/env python3
"""Record commander human approval for Logos S1_SHADOW KPI review (audit trail only).

Does not enable live trading, A-track automation, or promotion_to_a_track.
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

DEFAULT_KPI = ART / "logos_shadow_promotion_kpi_progress_latest.json"
DEFAULT_OUT = ART / "logos_s1_shadow_promotion_human_approval_latest.json"
DEFAULT_APPROVAL_LOG = REPORTS / "logos_s1_shadow_promotion_approval_log_v1.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--kpi-progress-json",
        type=Path,
        default=DEFAULT_KPI,
        help="KPI progress artifact (must exist unless --skip-kpi-gate).",
    )
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--approval-log-jsonl", type=Path, default=DEFAULT_APPROVAL_LOG)
    ap.add_argument(
        "--decision",
        type=str,
        default="ACK_NEXT_STAGE_PLANNING",
        help="Recorded decision label (planning only; not live/A-track).",
    )
    ap.add_argument(
        "--reviewer",
        type=str,
        default="commander_delegated_chat",
        help="Reviewer label for audit (no PII).",
    )
    ap.add_argument("--notes", type=str, default="Commander approved via chat instruction; automation recorded evidence only.")
    ap.add_argument(
        "--skip-kpi-gate",
        action="store_true",
        help="Allow recording even if KPI contract is not passed (requires explicit human risk acceptance).",
    )
    ap.add_argument("--skip-agent-decision-log", action="store_true")
    args = ap.parse_args()

    kpi_path = args.kpi_progress_json if args.kpi_progress_json.is_absolute() else ROOT / args.kpi_progress_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    log_path = args.approval_log_jsonl if args.approval_log_jsonl.is_absolute() else ROOT / args.approval_log_jsonl

    if not kpi_path.is_file():
        raise SystemExit(f"Missing KPI progress file: {kpi_path}")

    kpi = _read_json(kpi_path)
    kpi_ok = bool(kpi.get("passed")) and str(kpi.get("status") or "") == "READY_FOR_REVIEW"
    if not kpi_ok and not args.skip_kpi_gate:
        raise SystemExit(
            "KPI contract not satisfied for automatic approval record; "
            "fix gates or pass --skip-kpi-gate with human acceptance of risk."
        )

    payload: dict[str, Any] = {
        "schema": "logos_s1_shadow_promotion_human_approval_v1",
        "generated_at_utc": _now(),
        "decision": str(args.decision),
        "reviewer_label": str(args.reviewer),
        "notes": str(args.notes),
        "kpi_progress_snapshot": {
            "status": kpi.get("status"),
            "passed": kpi.get("passed"),
            "checks": kpi.get("checks"),
            "consecutive_strict_go_windows": kpi.get("consecutive_strict_go_windows"),
        },
        "track_wall": {
            "shadow_only": True,
            "promotion_to_a_track_allowed": False,
            "auto_trade_enable": False,
            "live_trading_enabled_by_this_artifact": False,
        },
        "limitations": (
            "This artifact records human acknowledgment for next-stage planning only. "
            "It does not modify exchange credentials, order routers, or A-track gates."
        ),
        "evidence_paths": {
            "kpi_progress_json": str(kpi_path.resolve()),
            "human_approval_json": str(out_path.resolve()),
        },
        "kpi_gate_bypassed": bool(args.skip_kpi_gate),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    log_row = {
        "generated_at_utc": payload["generated_at_utc"],
        "decision": payload["decision"],
        "reviewer_label": payload["reviewer_label"],
        "kpi_passed_at_record": bool(kpi.get("passed")),
        "kpi_status_at_record": kpi.get("status"),
        "kpi_gate_bypassed": payload["kpi_gate_bypassed"],
        "human_approval_json": str(out_path.resolve()),
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(log_row, ensure_ascii=False) + "\n")

    if not args.skip_agent_decision_log:
        ld = ROOT / "scripts" / "log_agent_decision.py"
        if ld.is_file():
            subprocess.run(
                [
                    sys.executable,
                    str(ld),
                    "--mission-id",
                    "logos_s1_shadow_promotion_review",
                    "--stage",
                    "human_approval_recorded",
                    "--decision",
                    str(args.decision),
                    "--evidence-path",
                    str(out_path.resolve()),
                    "--actor",
                    str(args.reviewer),
                    "--note",
                    "Logos S1_SHADOW KPI review; planning-stage acknowledgment only.",
                ],
                cwd=str(ROOT),
                check=False,
            )

    print(json.dumps({"ok": True, "out": str(out_path), "decision": payload["decision"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
