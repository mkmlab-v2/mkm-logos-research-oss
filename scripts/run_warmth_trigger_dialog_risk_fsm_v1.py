#!/usr/bin/env python3
"""Cumulative dialog risk FSM — text-level reset/inject/handoff ([HYPO] · RQ-027/028)."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_POLICY = ROOT / "docs/final/artifacts/warmth_trigger_dialog_risk_policy_v1.json"
DEFAULT_LEXICON = ROOT / "docs/final/artifacts/warmth_trigger_text_overload_lexicon_v1.json"
DEFAULT_PROFILE = ROOT / "docs/final/schemas/warmth_trigger_profile_v1.example.json"
DEFAULT_OUT = ROOT / "reports/warmth_trigger_dialog_risk_fsm_v1_latest.json"

from scripts.scan_warmth_trigger_text_overload_v1 import (  # noqa: E402
    _load_json,
    scan_text,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _role_drift_increment(text: str, policy: dict[str, Any]) -> tuple[float, bool]:
    rd = policy.get("role_drift") or {}
    normalized = _normalize(text)
    hit = False
    for token in rd.get("tokens_ko") or []:
        if token.lower() in normalized:
            hit = True
            break
    if not hit:
        return 0.0, False
    inc = float(rd.get("increment", 0.2))
    cap = float(rd.get("max_contribution", 0.5))
    return min(inc, cap), True


def _pick_mitigation(
    *,
    cumulative: float,
    overload_risk: str,
    policy: dict[str, Any],
    cooldown_enabled: bool,
) -> tuple[str, str, str | None]:
    """Return (fsm_state, mitigation_action, inject_reminder_text)."""
    th = policy.get("thresholds") or {}
    reminder = policy.get("reminder_snippet_ko")

    if overload_risk == "human_gate_hold" or cumulative >= float(th.get("human_handoff", 0.82)):
        return "human_queue", "human_handoff", reminder

    if cumulative >= float(th.get("reset_context", 0.58)):
        return "cooldown", "reset_context", reminder

    if cooldown_enabled and cumulative >= float(th.get("cooldown_arm", 0.35)):
        if overload_risk in ("high", "medium"):
            return "cooldown", "warm_only_cooldown", reminder

    if cumulative >= float(th.get("inject_reminder", 0.42)):
        return "elevated", "inject_reminder", reminder

    return "normal", "none", None


def run_fsm(
    *,
    turns: list[dict[str, str]],
    policy: dict[str, Any],
    lexicon: dict[str, Any],
    profile: dict[str, Any] | None,
    session_id: str,
    cooldown_enabled: bool = True,
) -> dict[str, Any]:
    decay = float(policy.get("turn_decay_per_message", 0.88))
    increments = policy.get("overload_risk_increment") or {}

    cumulative = 0.0
    role_drift_total = 0.0
    turn_rows: list[dict[str, Any]] = []
    final_state = "normal"
    final_action = "none"
    inject_text: str | None = None

    for idx, turn in enumerate(turns):
        role = turn.get("role", "user")
        text = turn.get("text", "")
        if role != "user" or not text.strip():
            turn_rows.append(
                {
                    "turn_index": idx,
                    "role": role,
                    "text_len": len(text),
                    "overload_risk": "skipped_non_user",
                    "turn_increment": 0.0,
                    "cumulative_after": round(cumulative, 6),
                    "mitigation_triggered": "none",
                }
            )
            continue

        cumulative *= decay
        scan = scan_text(text=text, lexicon=lexicon, profile=profile)
        risk_label = scan["overload_risk"]
        base_inc = float(increments.get(risk_label, 0.1))
        drift_inc, drift_hit = _role_drift_increment(text, policy)
        role_drift_total = min(1.0, role_drift_total + drift_inc)
        turn_inc = base_inc + drift_inc
        cumulative = min(1.5, cumulative + turn_inc)

        fsm_state, mitigation, reminder = _pick_mitigation(
            cumulative=cumulative,
            overload_risk=risk_label,
            policy=policy,
            cooldown_enabled=cooldown_enabled,
        )
        final_state = fsm_state
        final_action = mitigation
        inject_text = reminder if mitigation in ("inject_reminder", "reset_context") else inject_text

        if mitigation == "reset_context":
            cumulative = 0.0
            role_drift_total = 0.0

        turn_rows.append(
            {
                "turn_index": idx,
                "role": role,
                "text_len": len(text),
                "overload_risk": risk_label,
                "suggested_arm": scan.get("suggested_arm"),
                "role_drift_hit": drift_hit,
                "turn_increment": round(turn_inc, 6),
                "cumulative_after": round(cumulative, 6),
                "mitigation_triggered": mitigation,
            }
        )

    user_turns = sum(1 for t in turns if t.get("role") == "user" and t.get("text", "").strip())
    return {
        "schema": "warmth_trigger_dialog_risk_fsm_v1",
        "version": "1.0.0",
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "generated_at_utc": _utc_now(),
        "session_id": session_id,
        "turn_count": user_turns,
        "cumulative_risk_score": round(cumulative, 6),
        "role_drift_score": round(role_drift_total, 6),
        "fsm_state": final_state,
        "mitigation_action": final_action,
        "warm_only_cooldown_enabled": cooldown_enabled,
        "inject_reminder_text": inject_text,
        "policy_ref": "docs/final/artifacts/warmth_trigger_dialog_risk_policy_v1.json",
        "turns": turn_rows,
        "metaphor_notices": [
            "text_level_fsm_not_l_opt_hidden_state",
            "human_handoff_is_queue_stub_not_live_ops",
            "reset_context_clears_risk_counter_only_not_llm_kv_cache",
        ],
        "provenance": {
            "source": "run_warmth_trigger_dialog_risk_fsm_v1",
            "experiment_id": policy.get("provenance", {}).get("experiment_id", "wtt_dialog_risk_fsm_v1"),
        },
    }


def _load_turns_jsonl(path: Path) -> list[dict[str, str]]:
    turns: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        turns.append({"role": row.get("role", "user"), "text": row.get("text", row.get("content", ""))})
    return turns


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--session-id", default="demo_session_01")
    ap.add_argument("--turns-jsonl", type=Path, help="JSONL lines: {role, text}")
    ap.add_argument("--text", action="append", default=[], help="User utterance (repeatable)")
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--lexicon-json", type=Path, default=DEFAULT_LEXICON)
    ap.add_argument("--profile-json", type=Path, default=DEFAULT_PROFILE)
    ap.add_argument("--no-profile", action="store_true")
    ap.add_argument("--no-cooldown-arm", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.turns_jsonl:
        turns = _load_turns_jsonl(args.turns_jsonl)
    elif args.text:
        turns = [{"role": "user", "text": t} for t in args.text]
    else:
        ap.error("Provide --turns-jsonl or at least one --text")

    policy = _load_json(args.policy_json)
    lexicon = _load_json(args.lexicon_json)
    profile = None if args.no_profile else _load_json(args.profile_json)

    report = run_fsm(
        turns=turns,
        policy=policy,
        lexicon=lexicon,
        profile=profile,
        session_id=args.session_id,
        cooldown_enabled=not args.no_cooldown_arm,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "fsm_state": report["fsm_state"],
                "mitigation_action": report["mitigation_action"],
                "cumulative_risk_score": report["cumulative_risk_score"],
                "out": str(args.out.resolve()),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
