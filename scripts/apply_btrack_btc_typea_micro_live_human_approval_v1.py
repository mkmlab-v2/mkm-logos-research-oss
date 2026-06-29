#!/usr/bin/env python3
"""Record commander approval for B-track Type-A micro-live experiment ([HYPO])."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs/final/artifacts/btrack_btc_typea_micro_live_policy_v1.json"
TYPEA_APPROVAL = ROOT / "docs/final/artifacts/btrack_btc_typea_guard_human_approval_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/btrack_btc_typea_micro_live_human_approval_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reviewer", default="commander")
    ap.add_argument(
        "--note-ko",
        default="소액 테스트 계좌 Type-A guard micro-live — 통찰·자율진화 실험 (Track A/실매매 자동승격 아님).",
    )
    ap.add_argument("--approval-out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true", help="Overwrite existing approval.")
    args = ap.parse_args(argv)

    if args.approval_out.is_file() and not args.force:
        existing = _load(args.approval_out)
        if str(existing.get("decision") or "") == "APPROVED_BTRACK_TYPEA_MICRO_LIVE_EXPERIMENT":
            print(f"SKIP: already approved at {existing.get('approved_at_utc')}")
            return 0

    typea = _load(TYPEA_APPROVAL)
    if str(typea.get("decision") or "") != "APPROVED_BTC_TYPEA_GUARD_OPERATIONAL_SCORE":
        raise SystemExit(f"typea guard not approved: {TYPEA_APPROVAL}")

    policy = _load(POLICY)
    doc = {
        "schema": "btrack_btc_typea_micro_live_human_approval_v1",
        "approved_at_utc": _now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "decision": "APPROVED_BTRACK_TYPEA_MICRO_LIVE_EXPERIMENT",
        "reviewer": args.reviewer,
        "note_ko": args.note_ko,
        "live_trading_enabled": True,
        "track_a_auto_promote": False,
        "combined_all_passed": False,
        "would_change_active": False,
        "policy_pointer": str(POLICY.relative_to(ROOT)),
        "prerequisites": {
            "typea_guard_approval": str(TYPEA_APPROVAL.relative_to(ROOT)),
            "typea_guard_decision": typea.get("decision"),
        },
        "constraints": {
            "test_account_only": True,
            "auto_scale_up": False,
            "human_reapproval_for_stage_up": True,
        },
        "policy_caps": {
            "size_usd": policy.get("size_usd"),
            "max_position_size": policy.get("max_position_size"),
            "max_daily_loss_pct": policy.get("max_daily_loss_pct"),
            "max_drawdown_pct": policy.get("max_drawdown_pct"),
            "max_trades_per_day": policy.get("max_trades_per_day"),
        },
    }
    args.approval_out.parent.mkdir(parents=True, exist_ok=True)
    args.approval_out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.approval_out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
