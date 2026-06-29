#!/usr/bin/env python3
"""[HYPO] Free ($0) cinematic v2 bundle — all shots ffmpeg+Edge-TTS + optional master concat."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs/final/artifacts"
DEFAULT_SHOT_PLAN = ART / "director_agent_v2_shot_plan_latest.json"
DEFAULT_OUT = ART / "cinematic_v2_free_animatic_bundle_v1_latest.json"

_CIN = Path(__file__).resolve().parent
if str(_CIN) not in sys.path:
    sys.path.insert(0, str(_CIN))
from cinematic_v2_free_animatic_lib_v1 import now_utc, run_free_animatic_shots  # noqa: E402


def _filter_shots(shots: list[dict], start: int, end: int, shot_id: str) -> list[dict]:
    if shot_id:
        out = [s for s in shots if s.get("shot_id") == shot_id]
        if not out:
            raise SystemExit(f"shot not found: {shot_id}")
        return out
    return [s for i, s in enumerate(shots, start=1) if start <= i <= end]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--shot-plan-json", type=Path, default=DEFAULT_SHOT_PLAN)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--shot-id", default="", help="Single shot e.g. SHOT_02")
    ap.add_argument("--start-shot", type=int, default=1)
    ap.add_argument("--end-shot", type=int, default=8)
    ap.add_argument("--skip-narration", action="store_true")
    ap.add_argument("--skip-bootstrap", action="store_true")
    ap.add_argument("--skip-handoff", action="store_true")
    ap.add_argument("--skip-concat", action="store_true")
    args = ap.parse_args()

    shot_plan_path = args.shot_plan_json if args.shot_plan_json.is_absolute() else (ROOT / args.shot_plan_json)
    if not shot_plan_path.is_file():
        print(json.dumps({"ok": False, "error": f"shot plan missing: {shot_plan_path}"}))
        return 1

    doc = json.loads(shot_plan_path.read_text(encoding="utf-8"))
    all_shots = list(doc.get("shots") or [])
    shots = _filter_shots(all_shots, args.start_shot, args.end_shot, args.shot_id)

    try:
        result = run_free_animatic_shots(
            shots,
            skip_narration=args.skip_narration,
            skip_bootstrap=args.skip_bootstrap,
            skip_handoff=args.skip_handoff,
            skip_concat=args.skip_concat or len(shots) == 1,
        )
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1

    payload = {
        "schema": "cinematic_v2_free_animatic_bundle_v1",
        "generated_at_utc": now_utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "promotion": "research_only",
        "cost_usd": 0.0,
        "veo_api_called": False,
        "flow_ui_required": False,
        "delivery_mode": "free_animatic_local_ffmpeg",
        "shot_count": len(shots),
        "shots_ok": sum(1 for s in result["shots"] if s.get("ok")),
        **result,
        "repro_one_shot": "py scripts/cinematic/run_cinematic_v2_free_animatic_bundle_v1.py",
    }

    out_json = args.out_json if args.out_json.is_absolute() else (ROOT / args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": payload["ok"],
                "out_json": str(out_json),
                "shots_ok": payload["shots_ok"],
                "shot_count": payload["shot_count"],
                "master_mp4": payload.get("master_mp4"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
