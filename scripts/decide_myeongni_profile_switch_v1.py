#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_SUMMARY = ART / "mkm_myeongni_package_b_chain_summary_latest.json"
DEFAULT_POLICY = ART / "mkm_myeongni_profile_switch_policy_v1.json"
DEFAULT_OUT = ART / "mkm_myeongni_profile_switch_recommendation_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _f(v: Any, default: float = 0.0) -> float:
    return float(v) if isinstance(v, (int, float)) else default


def main() -> int:
    ap = argparse.ArgumentParser(description="Decide balanced/attack recommendation from package_b summary margins.")
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    summary_path = args.summary_json if args.summary_json.is_absolute() else ROOT / args.summary_json
    policy_path = args.policy_json if args.policy_json.is_absolute() else ROOT / args.policy_json
    summary = _read_json(summary_path)
    policy = _read_json(policy_path)

    margins = summary.get("margins") if isinstance(summary.get("margins"), dict) else {}
    m_bal = margins.get("balanced") if isinstance(margins.get("balanced"), dict) else {}
    m_atk = margins.get("attack") if isinstance(margins.get("attack"), dict) else {}
    snap = summary.get("snapshot") if isinstance(summary.get("snapshot"), dict) else {}

    current_profile = str((policy.get("defaults") or {}).get("current_profile") or "balanced")
    fallback_profile = str((policy.get("defaults") or {}).get("target_profile_on_tie") or current_profile)

    promote = policy.get("promote_to_attack_if") if isinstance(policy.get("promote_to_attack_if"), dict) else {}
    demote = policy.get("demote_to_balanced_if") if isinstance(policy.get("demote_to_balanced_if"), dict) else {}

    atk_dir = _f(m_atk.get("direction_minus_reduce_cut"), -999.0)
    atk_conf = _f(m_atk.get("confidence_minus_reduce_cut"), -999.0)
    atk_dec = str(snap.get("decision_attack") or "")
    bal_dec = str(snap.get("decision_balanced") or "")

    promote_ok = (
        atk_dir >= _f(promote.get("attack_direction_margin_gte"), 0.0)
        and atk_conf >= _f(promote.get("attack_confidence_margin_gte"), 0.0)
        and (
            not str(promote.get("require_attack_decision") or "")
            or atk_dec == str(promote.get("require_attack_decision"))
        )
        and (
            not bool(promote.get("require_balanced_not_reduce"))
            or bal_dec != "REDUCE"
        )
    )

    demote_by_margin = (
        atk_dir < _f(demote.get("attack_direction_margin_lt"), -0.01)
        or atk_conf < _f(demote.get("attack_confidence_margin_lt"), -0.01)
    )
    demote_by_decision = bool(demote.get("or_attack_decision_not_reduce")) and atk_dec and atk_dec != "REDUCE"
    demote_ok = demote_by_margin or demote_by_decision

    if promote_ok and not demote_ok:
        recommended = "attack"
        action = "PROMOTE_TO_ATTACK"
    elif demote_ok and not promote_ok:
        recommended = "balanced"
        action = "DEMOTE_TO_BALANCED"
    else:
        recommended = fallback_profile
        action = "STAY_OR_TIE"

    out = {
        "schema": "mkm_myeongni_profile_switch_recommendation_v1",
        "generated_at_utc": _now(),
        "inputs": {
            "summary_json": str(summary_path),
            "policy_json": str(policy_path),
            "summary_mode": summary.get("mode"),
        },
        "state": {
            "current_profile": current_profile,
            "recommended_profile": recommended,
            "action": action,
        },
        "evidence": {
            "decision_balanced": bal_dec or None,
            "decision_attack": atk_dec or None,
            "balanced_margins": m_bal or None,
            "attack_margins": m_atk or None,
            "promote_condition_met": promote_ok,
            "demote_condition_met": demote_ok,
        },
        "governance": {
            "auto_apply": False,
            "research_only": True,
            "human_signoff_required": True,
        },
    }
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "recommended_profile": recommended, "action": action}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
