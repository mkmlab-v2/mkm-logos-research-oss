#!/usr/bin/env python3
"""Batch FSM eval over WTT pilot session JSONL ([HYPO] · stress report)."""
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

DEFAULT_POLICY = ROOT / "docs/final/artifacts/warmth_trigger_dialog_risk_policy_v1.json"
DEFAULT_LEXICON = ROOT / "docs/final/artifacts/warmth_trigger_text_overload_lexicon_v1.json"
DEFAULT_PROFILE = ROOT / "docs/final/schemas/warmth_trigger_profile_v1.example.json"
DEFAULT_JSONL = ROOT / "data/wtt/examples/wtt_spicy_masked_sessions_v1.example.jsonl"
DEFAULT_OUT = ROOT / "reports/wtt_spicy_corpus_fsm_batch_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel_to_root(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def run_batch(
    jsonl_path: Path,
    *,
    policy_path: Path = DEFAULT_POLICY,
    lexicon_path: Path = DEFAULT_LEXICON,
    profile_path: Path = DEFAULT_PROFILE,
) -> dict[str, Any]:
    policy = _load_json(policy_path)
    lexicon = _load_json(lexicon_path)
    profile = _load_json(profile_path)

    rows: list[dict[str, Any]] = []
    fsm_states: Counter[str] = Counter()
    mitigations: Counter[str] = Counter()
    expected_hits: Counter[str] = Counter()

    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        session = json.loads(line)
        sid = session["session_id"]
        report = run_fsm(
            turns=session["turns"],
            policy=policy,
            lexicon=lexicon,
            profile=profile,
            session_id=sid,
            cooldown_enabled=True,
        )
        fsm_states[report["fsm_state"]] += 1
        mitigations[report["mitigation_action"]] += 1
        expected = set(session.get("expected_stress") or [])
        if "human_gate" in expected and report["mitigation_action"] == "human_handoff":
            expected_hits["human_gate"] += 1
        if "role_drift" in expected and any(t.get("role_drift_hit") for t in report["turns"]):
            expected_hits["role_drift"] += 1
        if "overload" in expected and report["cumulative_risk_score"] >= 0.35:
            expected_hits["overload"] += 1
        if "baseline" in expected and report["fsm_state"] == "normal":
            expected_hits["baseline"] += 1
        rows.append(
            {
                "session_id": sid,
                "fsm_state": report["fsm_state"],
                "mitigation_action": report["mitigation_action"],
                "cumulative_risk_score": report["cumulative_risk_score"],
                "expected_stress": list(expected),
            }
        )

    n = len(rows)
    return {
        "schema": "wtt_spicy_corpus_fsm_batch_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "jsonl_path": _rel_to_root(jsonl_path),
        "session_count": n,
        "fsm_state_counts": dict(fsm_states),
        "mitigation_counts": dict(mitigations),
        "expected_stress_hits": dict(expected_hits),
        "sessions": rows,
        "disclaimer_ko": "합성 코퍼스 FSM 배치 — 과탐/미탐 튜닝용; 고객 실측 아님",
        "policy_path": _rel_to_root(policy_path),
        "lexicon_path": _rel_to_root(lexicon_path),
        "provenance": {"source": "run_wtt_spicy_corpus_fsm_batch_v1"},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON)
    ap.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    report = run_batch(
        args.jsonl.resolve(),
        policy_path=args.policy.resolve(),
        lexicon_path=args.lexicon.resolve(),
        profile_path=args.profile.resolve(),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "sessions": report["session_count"],
                "fsm_state_counts": report["fsm_state_counts"],
                "out": str(args.out.resolve()),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
