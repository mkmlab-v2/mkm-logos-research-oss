#!/usr/bin/env python3
"""B-track research promotion gate for symbolic→audio pipeline (§3.9).

Runs the consolidated pytest bundle for M0–M5. Exit 0 iff pytest passes.
Writes JSON artifact; decision GO is **research lane only** — Track A commercial audio and
Track C primary GTM remain blocked until separate human + metric gates (see track_wall).

Payload includes ``emotion_va_overlay_ack`` for §3.10 traceability (same pytest bundle covers
``--emotion-mapping-json``); it does **not** add a separate GO/HOLD criterion beyond M0–M5 green.

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

PYTEST_MODULES = [
    "tests/test_sasang_music_mapping_schema_v1.py",
    "tests/test_sasang_emotion_mapping_schema_v1.py",
    "tests/test_run_lens_music_gematria_v1.py",
    "tests/test_lens_music_gate_chain_v1.py",
    "tests/test_lens_music_internal_eval_schema_v1.py",
    "tests/test_validate_lens_music_internal_eval_jsonl_v1.py",
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


def build_payload(pytest_exit_code: int, log_tail: str) -> dict[str, Any]:
    ok = pytest_exit_code == 0
    decision = "B_TRACK_RESEARCH_PROMOTION_READY" if ok else "HOLD_PYTEST_FAILED"
    out: dict[str, Any] = {
        "schema": "lens_music_symbolic_audio_promotion_gate_v1",
        "generated_at_utc": _utc_now(),
        "pytest_modules": PYTEST_MODULES,
        "pytest_exit_code": pytest_exit_code,
        "pytest_pass": ok,
        "pytest_log_tail": log_tail,
        "decision": decision,
        "track_wall": {
            "promotion_to_a_track_commercial_audio": False,
            "promotion_to_track_c_primary_gtm": False,
            "human_review_required_for_any_public_claim": True,
            "note": (
                "B_TRACK_RESEARCH_PROMOTION_READY = CI bundle green for §3.9 M0–M5 only. "
                "Not compression Track A §9; not automatic product claims."
            ),
        },
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
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    code, tail = run_pytest_bundle()
    payload = build_payload(code, tail)
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
