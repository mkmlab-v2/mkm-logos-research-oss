#!/usr/bin/env python3
"""Observe FSM/policy on operator panel corpus — no expected_stress labels [HYPO]."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_warmth_trigger_dialog_risk_fsm_v1 import run_fsm  # noqa: E402
from scripts.scan_warmth_trigger_text_overload_v1 import _load_json  # noqa: E402

DEFAULT_JSONL = ROOT / "data/wtt/examples/wtt_operator_panel_sessions_v1.example.jsonl"
DEFAULT_POLICY = ROOT / "docs/final/artifacts/warmth_trigger_dialog_risk_policy_v1.json"
DEFAULT_LEXICON = ROOT / "docs/final/artifacts/warmth_trigger_text_overload_lexicon_v1.json"
DEFAULT_CAND_POLICY = ROOT / "docs/final/artifacts/warmth_trigger_dialog_risk_policy_v1_tuned_v2_candidate.json"
DEFAULT_CAND_LEXICON = ROOT / "docs/final/artifacts/warmth_trigger_text_overload_lexicon_v1_tuned_v2_candidate.json"
DEFAULT_PROFILE = ROOT / "docs/final/schemas/warmth_trigger_profile_v1.example.json"
DEFAULT_OUT = ROOT / "reports/wtt_operator_panel_policy_observe_v1_latest.json"

ESCALATION_HINTS = (
    "환불",
    "소보원",
    "신고",
    "매니저",
    "연결해",
    "불만",
    "이중",
    "콜백",
    "에스컬",
    "프롬프트",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _session_text(session: dict[str, Any]) -> str:
    parts: list[str] = []
    for turn in session.get("turns") or []:
        if turn.get("role") == "user":
            parts.append(str(turn.get("text", "")))
    return " ".join(parts)


def _is_escalation_session(session: dict[str, Any]) -> bool:
    text = _session_text(session)
    return any(h in text for h in ESCALATION_HINTS)


def observe_corpus(
    jsonl_path: Path,
    *,
    policy: dict[str, Any],
    lexicon: dict[str, Any],
    profile: dict[str, Any],
    label: str,
) -> dict[str, Any]:
    fsm_states: Counter[str] = Counter()
    mitigations: Counter[str] = Counter()
    escalation_total = 0
    escalation_mitigated = 0
    risk_scores: list[float] = []

    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        session = json.loads(line)
        report = run_fsm(
            turns=session["turns"],
            policy=policy,
            lexicon=lexicon,
            profile=profile,
            session_id=session["session_id"],
            cooldown_enabled=True,
        )
        fsm_states[report["fsm_state"]] += 1
        mitigations[report["mitigation_action"]] += 1
        risk_scores.append(float(report["cumulative_risk_score"]))
        if _is_escalation_session(session):
            escalation_total += 1
            if report["mitigation_action"] != "none" or report["fsm_state"] != "normal":
                escalation_mitigated += 1

    n = sum(fsm_states.values())
    avg_risk = round(sum(risk_scores) / n, 4) if n else 0.0
    esc_rate = round(escalation_mitigated / escalation_total, 4) if escalation_total else 0.0
    return {
        "label": label,
        "session_count": n,
        "fsm_state_counts": dict(fsm_states),
        "mitigation_counts": dict(mitigations),
        "avg_cumulative_risk_score": avg_risk,
        "escalation_hint_sessions": escalation_total,
        "escalation_hint_mitigated_or_non_normal": escalation_mitigated,
        "escalation_hint_response_rate": esc_rate,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--baseline-policy", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--baseline-lexicon", type=Path, default=DEFAULT_LEXICON)
    ap.add_argument("--candidate-policy", type=Path, default=DEFAULT_CAND_POLICY)
    ap.add_argument("--candidate-lexicon", type=Path, default=DEFAULT_CAND_LEXICON)
    ap.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    jsonl = args.jsonl.resolve()
    if not jsonl.is_file():
        print(json.dumps({"ok": False, "error": f"missing: {jsonl}"}))
        return 1

    profile = _load_json(args.profile)
    baseline_p = _load_json(args.baseline_policy)
    baseline_l = _load_json(args.baseline_lexicon)
    cand_p = _load_json(args.candidate_policy) if args.candidate_policy.is_file() else baseline_p
    cand_l = _load_json(args.candidate_lexicon) if args.candidate_lexicon.is_file() else baseline_l

    baseline = observe_corpus(jsonl, policy=baseline_p, lexicon=baseline_l, profile=profile, label="baseline")
    candidate = observe_corpus(jsonl, policy=cand_p, lexicon=cand_l, profile=profile, label="candidate_v2")

    delta_esc = round(
        candidate["escalation_hint_response_rate"] - baseline["escalation_hint_response_rate"],
        4,
    )
    report = {
        "schema": "wtt_operator_panel_policy_observe_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "panel_lane": "operator_panel",
        "not_eligible_for_send": True,
        "send_gate": "HOLD",
        "jsonl_path": _rel(jsonl),
        "baseline": baseline,
        "candidate_v2": candidate,
        "delta_escalation_hint_response_rate": delta_esc,
        "note_ko": (
            "라벨 없는 operator panel 관측 — escalation 힌트 세션의 non-normal/완화 반응률만 참고. "
            "실고객·SEND 증거 아님."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "sessions": baseline["session_count"],
                "baseline_esc_rate": baseline["escalation_hint_response_rate"],
                "candidate_esc_rate": candidate["escalation_hint_response_rate"],
                "delta": delta_esc,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
