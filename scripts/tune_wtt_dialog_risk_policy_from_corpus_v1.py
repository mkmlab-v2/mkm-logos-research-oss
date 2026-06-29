#!/usr/bin/env python3
"""Tune WTT dialog risk policy/lexicon from labeled synthetic corpus ([HYPO])."""
from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_warmth_trigger_dialog_risk_fsm_v1 import run_fsm  # noqa: E402
from scripts.scan_warmth_trigger_text_overload_v1 import _load_json  # noqa: E402

DEFAULT_JSONL = ROOT / "data/wtt/examples/wtt_spicy_masked_sessions_v1.example.jsonl"
DEFAULT_POLICY = ROOT / "docs/final/artifacts/warmth_trigger_dialog_risk_policy_v1.json"
DEFAULT_LEXICON = ROOT / "docs/final/artifacts/warmth_trigger_text_overload_lexicon_v1.json"
DEFAULT_PROFILE = ROOT / "docs/final/schemas/warmth_trigger_profile_v1.example.json"
DEFAULT_OUT = ROOT / "reports/wtt_dialog_risk_policy_tune_v1_latest.json"
CANDIDATE_POLICY = ROOT / "docs/final/artifacts/warmth_trigger_dialog_risk_policy_v1_tuned_candidate.json"
CANDIDATE_LEXICON = ROOT / "docs/final/artifacts/warmth_trigger_text_overload_lexicon_v1_tuned_candidate.json"
CANDIDATE_V2_POLICY = ROOT / "docs/final/artifacts/warmth_trigger_dialog_risk_policy_v1_tuned_v2_candidate.json"
CANDIDATE_V2_LEXICON = ROOT / "docs/final/artifacts/warmth_trigger_text_overload_lexicon_v1_tuned_v2_candidate.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel_to_root(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _eval_session(
    session: dict[str, Any],
    *,
    policy: dict[str, Any],
    lexicon: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    report = run_fsm(
        turns=session["turns"],
        policy=policy,
        lexicon=lexicon,
        profile=profile,
        session_id=session["session_id"],
        cooldown_enabled=True,
    )
    expected = set(session.get("expected_stress") or [])
    role_drift_hit = any(t.get("role_drift_hit") for t in report["turns"])
    cumulative = float(report["cumulative_risk_score"])
    mitigation = report["mitigation_action"]
    state = report["fsm_state"]

    checks: dict[str, bool] = {}
    if "overload" in expected:
        checks["overload"] = cumulative >= float(policy["thresholds"]["cooldown_arm"]) or mitigation != "none"
    if "role_drift" in expected:
        checks["role_drift"] = role_drift_hit or mitigation in ("inject_reminder", "reset_context", "human_handoff")
    if "human_gate" in expected:
        checks["human_gate"] = mitigation == "human_handoff"
    if "baseline" in expected:
        checks["baseline"] = state == "normal" and mitigation == "none"
    if "cooldown" in expected:
        checks["cooldown"] = mitigation in ("warm_only_cooldown", "reset_context") or state == "cooldown"
    if "noise" in expected:
        checks["noise"] = state in ("normal", "elevated") and mitigation in ("none", "inject_reminder")
    if "privacy" in expected:
        checks["privacy"] = True

    misses = [k for k, ok in checks.items() if not ok]
    return {
        "session_id": session["session_id"],
        "expected_stress": sorted(expected),
        "fsm_state": state,
        "mitigation_action": mitigation,
        "cumulative_risk_score": cumulative,
        "role_drift_hit": role_drift_hit,
        "checks": checks,
        "misses": misses,
    }


def _score_corpus(
    jsonl_path: Path,
    *,
    policy: dict[str, Any],
    lexicon: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    miss_by_type: dict[str, int] = {}
    hit_by_type: dict[str, int] = {}

    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        session = json.loads(line)
        ev = _eval_session(session, policy=policy, lexicon=lexicon, profile=profile)
        rows.append(ev)
        for stress, ok in ev["checks"].items():
            if ok:
                hit_by_type[stress] = hit_by_type.get(stress, 0) + 1
            else:
                miss_by_type[stress] = miss_by_type.get(stress, 0) + 1

    labeled = sum(len(r["checks"]) for r in rows)
    hits = sum(len(r["checks"]) - len(r["misses"]) for r in rows)
    return {
        "session_count": len(rows),
        "labeled_checks": labeled,
        "hits": hits,
        "misses": labeled - hits,
        "hit_rate": round(hits / labeled, 4) if labeled else 0.0,
        "hit_by_type": hit_by_type,
        "miss_by_type": miss_by_type,
        "sessions": rows,
    }


def _build_candidate(policy: dict[str, Any], lexicon: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    p = copy.deepcopy(policy)
    l = copy.deepcopy(lexicon)
    p["version"] = "1.0.1-tuned-candidate"
    p["thresholds"]["inject_reminder"] = 0.36
    p["thresholds"]["cooldown_arm"] = 0.30
    p["thresholds"]["reset_context"] = 0.54
    inc = p["overload_risk_increment"]
    inc["low"] = 0.10
    inc["medium"] = 0.24
    inc["high"] = 0.42
    p["provenance"]["tune_source"] = "tune_wtt_dialog_risk_policy_from_corpus_v1"

    defaults = l.setdefault("defaults", {})
    defaults["overload_medium_intensity"] = 0.50
    defaults["overload_high_intensity"] = 0.68
    l["version"] = "1.0.1-tuned-candidate"

    signals = list(l.get("signals") or [])
    extra = {
        "signal_id": "cs_escalation_frustration",
        "tokens_ko": ["환불", "신고", "소송", "소보원", "답변 복붙", "상담원 연결"],
        "intensity_delta": 0.18,
        "valence_delta": -0.2,
        "arousal_delta": 0.22,
        "surprisal_delta": 0.1,
        "human_gate": False,
    }
    if not any(s.get("signal_id") == extra["signal_id"] for s in signals):
        signals.append(extra)
    anger = next((s for s in signals if s.get("signal_id") == "anger_spike"), None)
    if anger:
        tokens = list(anger.get("tokens_ko") or [])
        for t in ("빡침", "빡쳐", "개빡"):
            if t not in tokens:
                tokens.append(t)
        anger["tokens_ko"] = tokens
    l["signals"] = signals
    l["provenance"] = l.get("provenance") or {}
    l["provenance"]["tune_source"] = "tune_wtt_dialog_risk_policy_from_corpus_v1"
    return p, l


def _build_candidate_v2(policy: dict[str, Any], lexicon: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Round-2: overload FN on spicy corpus — lexicon medium band + cumulative arm."""
    p, l = _build_candidate(policy, lexicon)
    p["version"] = "1.0.2-tuned-v2-candidate"
    inc = p["overload_risk_increment"]
    inc["low"] = 0.14
    inc["medium"] = 0.28
    th = p["thresholds"]
    th["inject_reminder"] = 0.30
    th["cooldown_arm"] = 0.24
    th["reset_context"] = 0.52
    p["provenance"]["tune_round"] = 2

    defaults = l.setdefault("defaults", {})
    defaults["overload_medium_intensity"] = 0.42
    defaults["overload_high_intensity"] = 0.62
    l["version"] = "1.0.2-tuned-v2-candidate"

    signals = list(l.get("signals") or [])
    for sig in signals:
        if sig.get("signal_id") == "cs_escalation_frustration":
            sig["intensity_delta"] = 0.24
        if sig.get("signal_id") == "anxiety_rumination":
            sig["intensity_delta"] = 0.26
        if sig.get("signal_id") == "guilt_spiral":
            sig["intensity_delta"] = 0.26
        if sig.get("signal_id") == "anger_spike":
            tokens = list(sig.get("tokens_ko") or [])
            for t in ("빡침", "빡쳐", "개빡", "신고함"):
                if t not in tokens:
                    tokens.append(t)
            sig["tokens_ko"] = tokens

    queue = {
        "signal_id": "queue_repeat_frustration",
        "tokens_ko": ["대기", "대기중", "복붙", "답변 복붙", "세번", "번째", "똑같은 말"],
        "intensity_delta": 0.2,
        "valence_delta": -0.18,
        "arousal_delta": 0.2,
        "surprisal_delta": 0.1,
        "human_gate": False,
    }
    if not any(s.get("signal_id") == queue["signal_id"] for s in signals):
        signals.append(queue)
    l["signals"] = signals
    l["provenance"] = l.get("provenance") or {}
    l["provenance"]["tune_source"] = "tune_wtt_dialog_risk_policy_from_corpus_v1"
    l["provenance"]["tune_round"] = 2
    return p, l


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON)
    ap.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--promote", action="store_true", help="Overwrite main policy+lexicon if candidate improves hit_rate.")
    ap.add_argument(
        "--round",
        type=int,
        choices=(1, 2),
        default=1,
        help="Tune round: 1=baseline candidate; 2=overload FN pass on spicy corpus.",
    )
    args = ap.parse_args()

    jsonl = args.jsonl.resolve()
    policy = _load_json(args.policy)
    lexicon = _load_json(args.lexicon)
    profile = _load_json(args.profile)

    baseline = _score_corpus(jsonl, policy=policy, lexicon=lexicon, profile=profile)
    if args.round == 2:
        cand_policy, cand_lexicon = _build_candidate_v2(policy, lexicon)
        cand_policy_path, cand_lexicon_path = CANDIDATE_V2_POLICY, CANDIDATE_V2_LEXICON
    else:
        cand_policy, cand_lexicon = _build_candidate(policy, lexicon)
        cand_policy_path, cand_lexicon_path = CANDIDATE_POLICY, CANDIDATE_LEXICON
    candidate = _score_corpus(jsonl, policy=cand_policy, lexicon=cand_lexicon, profile=profile)

    improved = candidate["hit_rate"] > baseline["hit_rate"]
    cand_policy_path.write_text(json.dumps(cand_policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cand_lexicon_path.write_text(json.dumps(cand_lexicon, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    promoted = False
    if args.promote and improved:
        args.policy.write_text(json.dumps(cand_policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        args.lexicon.write_text(json.dumps(cand_lexicon, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        promoted = True

    report = {
        "schema": "wtt_dialog_risk_policy_tune_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "tune_round": args.round,
        "jsonl_path": _rel_to_root(jsonl),
        "baseline": {
            "policy": _rel_to_root(args.policy),
            "lexicon": _rel_to_root(args.lexicon),
            "hit_rate": baseline["hit_rate"],
            "miss_by_type": baseline["miss_by_type"],
            "hit_by_type": baseline["hit_by_type"],
        },
        "candidate": {
            "policy": _rel_to_root(cand_policy_path),
            "lexicon": _rel_to_root(cand_lexicon_path),
            "hit_rate": candidate["hit_rate"],
            "miss_by_type": candidate["miss_by_type"],
            "hit_by_type": candidate["hit_by_type"],
            "delta_hit_rate": round(candidate["hit_rate"] - baseline["hit_rate"], 4),
        },
        "improved": improved,
        "promoted": promoted,
        "recommendation_ko": (
            "candidate 적용 권장 — synthetic 라벨 hit_rate 상승"
            if improved
            else "baseline 유지 — 추가 라벨·lexicon 검토"
        ),
        "next": (
            f"py scripts/run_wtt_spicy_corpus_fsm_batch_v1.py --policy {_rel_to_root(cand_policy_path)} "
            f"--lexicon {_rel_to_root(cand_lexicon_path)}"
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "baseline_hit_rate": baseline["hit_rate"],
                "candidate_hit_rate": candidate["hit_rate"],
                "improved": improved,
                "promoted": promoted,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
