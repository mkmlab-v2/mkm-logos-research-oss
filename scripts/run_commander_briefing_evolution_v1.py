#!/usr/bin/env python3
"""Briefing evolution v1 — aggregate evening scores → propose rule deltas (dry-run)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo("Asia/Seoul")
LOG_DIR = ROOT / "reports" / "briefing_log"
RULES_PATH = ROOT / "data" / "commander" / "briefing_evolution_rules_v1.json"
DEFAULT_OUT = ROOT / "reports" / "commander_briefing_evolution_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_recent_scores(days: int = 7) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not LOG_DIR.is_dir():
        return out
    for p in sorted(LOG_DIR.glob("*_evening_score_v1.json"), reverse=True)[:days]:
        doc = _read_json(p)
        if doc.get("schema") == "commander_evening_briefing_score_v1":
            out.append(doc)
    return out


def _aggregate_branch_outcomes(scores: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    agg: Dict[str, Dict[str, int]] = {}
    for sc in scores:
        for pred in sc.get("prediction_scores") or []:
            pid = str(pred.get("prediction_id") or "")
            if not pid.startswith("branch:"):
                continue
            bid = pid.split(":", 1)[1]
            agg.setdefault(bid, {})
            o = pred.get("outcome") or "neutral"
            agg[bid][o] = agg[bid].get(o, 0) + 1
    return agg


def run_evolution(*, dry_run: bool = True, lookback_days: int = 7) -> Dict[str, Any]:
    scores = _load_recent_scores(lookback_days)
    rules = _read_json(RULES_PATH)
    branch_agg = _aggregate_branch_outcomes(scores)

    proposals: List[Dict[str, Any]] = []
    for bid, counts in branch_agg.items():
        aligned = counts.get("aligned", 0)
        partial = counts.get("partial", 0)
        reject = counts.get("reject", 0)
        total = aligned + partial + reject + counts.get("neutral", 0)
        if total < 2:
            continue
        soft = (aligned + 0.5 * partial) / total if total else 0
        action = "hold"
        delta = 0.0
        if soft >= 0.55:
            action, delta = "boost_confidence_cap", 0.05
        elif soft <= 0.35:
            action, delta = "demote_confidence_cap", -0.05

        if action != "hold":
            proposals.append(
                {
                    "branch_id": bid,
                    "action": action,
                    "proposed_delta": delta if not dry_run else 0.0,
                    "soft_rate": round(soft, 3),
                    "counts": counts,
                    "dry_run_note": "v1 does not write rules file without --apply-human-approved",
                }
            )

    soft_rates = [s.get("summary", {}).get("soft_hit_rate") for s in scores if s.get("summary")]
    soft_rates = [x for x in soft_rates if x is not None]
    avg_soft = sum(soft_rates) / len(soft_rates) if soft_rates else None

    return {
        "schema": "commander_briefing_evolution_v1",
        "hypothesis_tier": "B",
        "dry_run": dry_run,
        "generated_at_utc": _utc_now(),
        "lookback_days": lookback_days,
        "n_evening_scores": len(scores),
        "avg_soft_hit_rate": round(avg_soft, 4) if avg_soft is not None else None,
        "branch_aggregate": branch_agg,
        "proposals": proposals,
        "rules_path": str(RULES_PATH),
        "risk_ack": [
            "No auto-apply to Track A or live trading",
            "Rule file mutation requires explicit human approval flag",
            "Low sample → hold",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lookback-days", type=int, default=7)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = run_evolution(dry_run=True, lookback_days=args.lookback_days)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json} proposals={len(doc.get('proposals') or [])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
