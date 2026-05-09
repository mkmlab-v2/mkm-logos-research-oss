#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_A_TRACK = ROOT / "docs" / "final" / "artifacts" / "a_track_go_nogo_status_latest.json"
DEFAULT_PROFILE_SWITCH = ROOT / "docs" / "final" / "artifacts" / "mkm_myeongni_profile_switch_recommendation_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "myeongni_conflict_arbitration_auto_lock_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def _f(v: Any, default: float = 0.0) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    return default


def _decide_preset(
    a_track: dict[str, Any] | None,
    profile_switch: dict[str, Any] | None,
    stress_doc: dict[str, Any] | None,
    stress_cut: float,
) -> tuple[str, dict[str, Any]]:
    reasons: list[str] = []
    stress_score = 0.0
    if stress_doc:
        # Supports generic keys to avoid tight coupling.
        stress_score = max(
            _f(stress_doc.get("market_stress_score"), 0.0),
            _f(stress_doc.get("stress_score"), 0.0),
            _f(stress_doc.get("risk_score"), 0.0),
        )
    if stress_score >= stress_cut:
        reasons.append(f"stress_score_gte_cut:{stress_score:.3f}>={stress_cut:.3f}")
        return "conservative", {"reasons": reasons, "stress_score": stress_score}

    overall = ""
    if a_track:
        overall = str(((a_track.get("result") or {}).get("overall_go_no_go")) or "")
    if overall and overall != "GO":
        reasons.append(f"a_track_not_go:{overall}")
        return "conservative", {"reasons": reasons, "stress_score": stress_score}

    rec = ""
    action = ""
    if profile_switch:
        state = profile_switch.get("state") or {}
        rec = str(state.get("recommended_profile") or "")
        action = str(state.get("action") or "")
    if rec == "attack" or action == "PROMOTE_TO_ATTACK":
        reasons.append("profile_switch_attack")
        return "aggressive", {"reasons": reasons, "stress_score": stress_score}

    reasons.append("default_neutral")
    return "neutral", {"reasons": reasons, "stress_score": stress_score}


def main() -> int:
    ap = argparse.ArgumentParser(description="Auto-lock myeongni arbitration preset based on market stress and readiness.")
    ap.add_argument("--a-track-json", type=Path, default=DEFAULT_A_TRACK)
    ap.add_argument("--profile-switch-json", type=Path, default=DEFAULT_PROFILE_SWITCH)
    ap.add_argument("--stress-json", type=Path, default=None, help="Optional stress input JSON with stress_score style keys.")
    ap.add_argument("--stress-cut", type=float, default=0.65)
    ap.add_argument("--apply-script", type=Path, default=ROOT / "scripts" / "apply_myeongni_conflict_arbitration_preset_v1.py")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--actor", default="auto_lock_chain")
    args = ap.parse_args()

    a_track_path = args.a_track_json if args.a_track_json.is_absolute() else ROOT / args.a_track_json
    profile_path = args.profile_switch_json if args.profile_switch_json.is_absolute() else ROOT / args.profile_switch_json
    stress_path = (args.stress_json if args.stress_json.is_absolute() else ROOT / args.stress_json) if args.stress_json else None
    apply_path = args.apply_script if args.apply_script.is_absolute() else ROOT / args.apply_script
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    a_track = _read_json_if_exists(a_track_path)
    profile = _read_json_if_exists(profile_path)
    stress = _read_json_if_exists(stress_path) if stress_path else None

    preset, detail = _decide_preset(a_track, profile, stress, args.stress_cut)
    cmd = [
        sys.executable,
        str(apply_path),
        "--preset",
        preset,
        "--actor",
        args.actor,
    ]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    ok = cp.returncode == 0

    out = {
        "schema": "myeongni_conflict_arbitration_auto_lock_v1",
        "generated_at_utc": _now(),
        "inputs": {
            "a_track_json": str(a_track_path),
            "profile_switch_json": str(profile_path),
            "stress_json": str(stress_path) if stress_path else None,
            "stress_cut": args.stress_cut,
        },
        "decision": {
            "preset": preset,
            "detail": detail,
        },
        "apply": {
            "ok": ok,
            "exit_code": cp.returncode,
            "stdout": cp.stdout.strip(),
            "stderr": cp.stderr.strip(),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "preset": preset, "out": str(out_path)}, ensure_ascii=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
