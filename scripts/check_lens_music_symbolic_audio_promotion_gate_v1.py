#!/usr/bin/env python3
"""B-track research promotion gate for symbolic→audio pipeline (§3.9).

Runs the consolidated pytest bundle (M0–M5 schema/gematria/gate chain/internal-eval plus M31
hormone trend webhook dispatch smoke). Exit 0 iff pytest passes.
Writes JSON artifact; decision GO is **research lane only** — Track A commercial audio and
Track C primary GTM remain blocked until separate human + metric gates (see track_wall).

Payload includes ``emotion_va_overlay_ack`` for §3.10 traceability (same pytest bundle covers
``--emotion-mapping-json``); it does **not** add a separate GO/HOLD criterion beyond the pytest bundle green.

Does not replace COMPRESSION §9 Track A promotion for the compression API lane.
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

DEFAULT_OUT = ROOT / "reports" / "lens_music_symbolic_audio_promotion_gate_latest.json"
DEFAULT_HORMONE_TREND = ROOT / "docs" / "final" / "artifacts" / "lens_music_hormone_trend_latest.json"
DEFAULT_HUMAN_SIGNOFF = ROOT / "reports" / "lens_music_human_signoff_record_latest.json"

PYTEST_MODULES = [
    "tests/test_sasang_music_mapping_schema_v1.py",
    "tests/test_sasang_emotion_mapping_schema_v1.py",
    "tests/test_run_lens_music_gematria_v1.py",
    "tests/test_lens_music_gate_chain_v1.py",
    "tests/test_lens_music_internal_eval_schema_v1.py",
    "tests/test_validate_lens_music_internal_eval_jsonl_v1.py",
    "tests/test_dispatch_lens_music_hormone_trend_webhook_v1.py",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_pytest_bundle() -> tuple[int, str]:
    cmd = [sys.executable, "-m", "pytest", *PYTEST_MODULES, "-q", "--tb=line"]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = ((r.stdout or "") + "\n" + (r.stderr or "")).strip()
    if len(tail) > 12000:
        tail = tail[-12000:]
    return r.returncode, tail


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _compute_m31_guard(
    *,
    hormone_trend: dict[str, Any],
    max_high_stress_rate: float,
    max_consecutive_high_stress: int,
    require_input: bool,
) -> tuple[bool, dict[str, Any]]:
    input_present = bool(hormone_trend and str(hormone_trend.get("schema") or "").strip())
    hs_rate = hormone_trend.get("high_stress_rate")
    hs_consecutive = hormone_trend.get("max_consecutive_high_stress")
    trend_state = str(hormone_trend.get("state") or "UNKNOWN").strip().upper()

    if not input_present:
        passed = not require_input
        detail = {
            "input_present": False,
            "guard_mode": "required" if require_input else "soft",
            "passed": passed,
            "reason": "missing_hormone_trend_input",
            "trend_state": "UNKNOWN",
            "high_stress_rate": None,
            "max_consecutive_high_stress": None,
            "thresholds": {
                "max_high_stress_rate": float(max_high_stress_rate),
                "max_consecutive_high_stress": int(max_consecutive_high_stress),
            },
            "non_biological_notice": "metaphor_only_advisory_controller",
        }
        return passed, detail

    try:
        hs_rate_f = float(hs_rate)
    except (TypeError, ValueError):
        hs_rate_f = 0.0
    try:
        hs_cons_i = int(hs_consecutive)
    except (TypeError, ValueError):
        hs_cons_i = 0
    rate_pass = hs_rate_f <= float(max_high_stress_rate)
    consecutive_pass = hs_cons_i <= int(max_consecutive_high_stress)
    trend_state_pass = trend_state != "WATCH"
    passed = bool(rate_pass and consecutive_pass and trend_state_pass)

    detail = {
        "input_present": True,
        "guard_mode": "required" if require_input else "soft",
        "passed": passed,
        "reason": "ok" if passed else "hormone_trend_watch_or_threshold_exceeded",
        "trend_state": trend_state,
        "high_stress_rate": hs_rate_f,
        "max_consecutive_high_stress": hs_cons_i,
        "checks": {
            "rate_pass": rate_pass,
            "consecutive_pass": consecutive_pass,
            "trend_state_pass": trend_state_pass,
        },
        "thresholds": {
            "max_high_stress_rate": float(max_high_stress_rate),
            "max_consecutive_high_stress": int(max_consecutive_high_stress),
        },
        "non_biological_notice": str(
            hormone_trend.get("non_biological_notice") or "metaphor_only_advisory_controller"
        ),
    }
    return passed, detail


def _compute_commercial_unlock(
    *,
    signoff: dict[str, Any],
    allow_unlock: bool,
) -> dict[str, Any]:
    scope = signoff.get("scope") if isinstance(signoff, dict) else {}
    basis = signoff.get("basis") if isinstance(signoff, dict) else {}
    decision = str(signoff.get("decision") or "").strip().upper() if isinstance(signoff, dict) else ""
    approved_by = str(signoff.get("approved_by") or "").strip() if isinstance(signoff, dict) else ""
    scope_track_a = bool(isinstance(scope, dict) and scope.get("track_a_commercial_audio"))
    scope_track_c = bool(isinstance(scope, dict) and scope.get("track_c_primary_gtm"))
    basis_ready = bool(isinstance(basis, dict) and basis.get("research_promotion_ready"))
    has_signoff = bool(signoff)
    valid_signoff = bool(
        has_signoff
        and decision in {"APPROVED_WITH_HUMAN_SIGNOFF", "APPROVED"}
        and approved_by
        and basis_ready
        and scope_track_a
        and scope_track_c
    )
    unlocked = bool(allow_unlock and valid_signoff)
    return {
        "unlock_requested": bool(allow_unlock),
        "unlock_applied": unlocked,
        "signoff_path_expected": str(DEFAULT_HUMAN_SIGNOFF),
        "signoff_present": has_signoff,
        "signoff_valid": valid_signoff,
        "checks": {
            "decision_approved": decision in {"APPROVED_WITH_HUMAN_SIGNOFF", "APPROVED"},
            "approved_by_present": bool(approved_by),
            "basis_research_ready": basis_ready,
            "scope_track_a_commercial_audio": scope_track_a,
            "scope_track_c_primary_gtm": scope_track_c,
        },
        "note": (
            "Commercial unlock is opt-in. Requires --allow-commercial-unlock plus a valid "
            "human signoff artifact with both Track A/Track C scopes."
        ),
    }


def build_payload(
    pytest_exit_code: int,
    log_tail: str,
    *,
    hormone_trend: dict[str, Any],
    human_signoff: dict[str, Any],
    allow_commercial_unlock: bool,
    max_high_stress_rate: float,
    max_consecutive_high_stress: int,
    require_m31_input: bool,
) -> dict[str, Any]:
    ok = pytest_exit_code == 0
    m31_pass, m31_detail = _compute_m31_guard(
        hormone_trend=hormone_trend,
        max_high_stress_rate=max_high_stress_rate,
        max_consecutive_high_stress=max_consecutive_high_stress,
        require_input=require_m31_input,
    )
    unlock = _compute_commercial_unlock(signoff=human_signoff, allow_unlock=allow_commercial_unlock)
    if not ok:
        decision = "HOLD_PYTEST_FAILED"
    elif not m31_pass:
        decision = "HOLD_M31_HORMONE_GUARD"
    else:
        decision = "B_TRACK_RESEARCH_PROMOTION_READY"
    out: dict[str, Any] = {
        "schema": "lens_music_symbolic_audio_promotion_gate_v1",
        "generated_at_utc": _utc_now(),
        "pytest_modules": PYTEST_MODULES,
        "pytest_exit_code": pytest_exit_code,
        "pytest_pass": ok,
        "pytest_log_tail": log_tail,
        "decision": decision,
        "track_wall": {
            "promotion_to_a_track_commercial_audio": bool(unlock["unlock_applied"]),
            "promotion_to_track_c_primary_gtm": bool(unlock["unlock_applied"]),
            "human_review_required_for_any_public_claim": True,
            "note": (
                "Default remains B-track research-only. Track wall can be unlocked only when a valid "
                "human signoff artifact exists and --allow-commercial-unlock is explicitly set."
            ),
        },
        "commercial_unlock_gate": unlock,
        "milestones_ack": {
            "M0": True,
            "M1": True,
            "M2": True,
            "M3_schema": True,
            "M4_jsonl_batch": True,
            "M5_emotion_va_overlay": True,
        },
        "references_ssot": {
            "track_c_section": "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md §3.9–3.9.2",
            "compression_playbook_cross_ref": (
                "docs/final/COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md §9"
            ),
            "track_c_section_3_10_emotion_va": (
                "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md §3.10 "
                "(sasang_emotion_mapping_v1 · emotion_va_overlay_v1 overlay only)"
            ),
        },
        "emotion_va_overlay_ack": {
            "pytest_includes_emotion_va_overlay_tests": True,
            "does_not_gate_promotion_decision": True,
            "note": (
                "tests/test_run_lens_music_gematria_v1.py exercises --emotion-mapping-json / "
                "emotion_va_overlay_v1; GO/HOLD stay M0–M5 pytest bundle only (Track Wall unchanged)."
            ),
        },
        "m31_hormone_guard": m31_detail,
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--hormone-trend-json", type=Path, default=DEFAULT_HORMONE_TREND)
    ap.add_argument("--m31-max-high-stress-rate", type=float, default=0.25)
    ap.add_argument("--m31-max-consecutive-high-stress", type=int, default=3)
    ap.add_argument("--require-m31-hormone-input", action="store_true")
    ap.add_argument("--human-signoff-json", type=Path, default=DEFAULT_HUMAN_SIGNOFF)
    ap.add_argument("--allow-commercial-unlock", action="store_true")
    args = ap.parse_args()

    code, tail = run_pytest_bundle()
    hormone_trend = _read_json(args.hormone_trend_json)
    human_signoff = _read_json(args.human_signoff_json)
    payload = build_payload(
        code,
        tail,
        hormone_trend=hormone_trend,
        human_signoff=human_signoff,
        allow_commercial_unlock=bool(args.allow_commercial_unlock),
        max_high_stress_rate=float(args.m31_max_high_stress_rate),
        max_consecutive_high_stress=int(args.m31_max_consecutive_high_stress),
        require_m31_input=bool(args.require_m31_hormone_input),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": code == 0, "decision": payload["decision"], "report": str(args.out.resolve())},
            ensure_ascii=False,
        )
    )
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
