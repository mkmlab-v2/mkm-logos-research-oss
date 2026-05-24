#!/usr/bin/env python3
"""Append one strict-streak history row from current latest WF artifacts (B-track).

Re-evaluates promotion gates against ``prophecy_*_latest.json`` paths using the
legacy streak file so consecutive daily ticks can reach ``strict_streak_required``.
Does not rebuild score/WF unless artifacts are missing.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LENS = ROOT / "docs/final/artifacts/prophecy_per_date_combo_walkforward_v1_latest.json"
DEFAULT_INST = ROOT / "docs/final/artifacts/prophecy_instrument_combo_walkforward_v1_latest.json"
DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_HYPO = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
DEFAULT_STREAK = ROOT / "docs/final/artifacts/prophecy_promotion_strict_streak_legacy_v1.json"
DEFAULT_GATES = ROOT / "docs/final/artifacts/prophecy_promotion_gates_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/prophecy_strict_streak_tick_v1_latest.json"
PUSH_BEST_180D = ROOT / "reports/btrack_promotion_push_work/sweep_180d/nbps_2_0"


def _sync_docs_final_from_push_best_if_present() -> bool:
    """Keep streak eval on nf6 180d dual-leg panel when promotion_push work dir exists."""
    if not (PUSH_BEST_180D / "lens_walkforward.json").is_file():
        return False
    pairs = [
        (PUSH_BEST_180D / "lens_walkforward.json", DEFAULT_LENS),
        (PUSH_BEST_180D / "instrument_walkforward.json", DEFAULT_INST),
        (PUSH_BEST_180D / "score_v1_180d.json", DEFAULT_SCORE),
    ]
    for src, dst in pairs:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return True


def _run(cmd: list[str]) -> int:
    print(f"+ {' '.join(cmd)}", file=sys.stderr)
    cp = subprocess.run(cmd, cwd=str(ROOT))
    return int(cp.returncode)


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticks", type=int, default=1, help="Number of consecutive gate eval appends.")
    ap.add_argument("--lens-walkforward-json", type=Path, default=DEFAULT_LENS)
    ap.add_argument("--instrument-walkforward-json", type=Path, default=DEFAULT_INST)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--hypothesis-json", type=Path, default=DEFAULT_HYPO)
    ap.add_argument("--streak-history-json", type=Path, default=DEFAULT_STREAK)
    ap.add_argument("--gates-out", type=Path, default=DEFAULT_GATES)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--calibration-note",
        default="strict_streak_tick_v1 on latest artifacts",
    )
    ap.add_argument(
        "--no-sync-push-best",
        action="store_true",
        help="Do not copy reports/btrack_promotion_push_work/sweep_180d/nbps_2_0 into docs/final before eval.",
    )
    args = ap.parse_args()
    synced = False
    if not args.no_sync_push_best:
        synced = _sync_docs_final_from_push_best_if_present()
        if synced:
            print(f"SYNC: promotion_push nf6 artifacts -> docs/final ({PUSH_BEST_180D.name})", file=sys.stderr)
    ticks = max(1, int(args.ticks))
    for p in (args.lens_walkforward_json, args.instrument_walkforward_json, args.score_json):
        if not p.is_file():
            raise SystemExit(f"missing required artifact: {p}")

    steps: list[dict[str, Any]] = []
    last_gates: dict[str, Any] = {}
    for i in range(ticks):
        note = f"{args.calibration_note} tick={i + 1}/{ticks}"
        rc = _run(
            [
                sys.executable,
                str(ROOT / "scripts/eval_prophecy_promotion_gates_v1.py"),
                "--promotion-track-mode",
                "dual",
                "--lens-walkforward-json",
                str(args.lens_walkforward_json),
                "--instrument-walkforward-json",
                str(args.instrument_walkforward_json),
                "--score-json",
                str(args.score_json),
                "--hypothesis-json",
                str(args.hypothesis_json),
                "--streak-history-json",
                str(args.streak_history_json),
                "--output",
                str(args.gates_out),
                "--calibration-note",
                note,
            ]
        )
        last_gates = _load(args.gates_out)
        steps.append(
            {
                "tick": i + 1,
                "exit_code": rc,
                "strict_passed": last_gates.get("strict_passed"),
                "strict_pass_streak": last_gates.get("strict_pass_streak"),
                "auto_promote_ready": last_gates.get("auto_promote_ready"),
            }
        )
        if rc != 0:
            break

    out = {
        "schema": "prophecy_strict_streak_tick_v1",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "synced_from_push_best": synced,
        "ticks_requested": ticks,
        "ticks_completed": len(steps),
        "steps": steps,
        "final_gates": {
            "strict_pass_streak": last_gates.get("strict_pass_streak"),
            "strict_passed": last_gates.get("strict_passed"),
            "auto_promote_ready": last_gates.get("auto_promote_ready"),
            "combined_all_passed": last_gates.get("combined_all_passed"),
            "promotion_recommendation": last_gates.get("promotion_recommendation"),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    if last_gates:
        print(
            f"streak={last_gates.get('strict_pass_streak')} "
            f"auto_promote_ready={last_gates.get('auto_promote_ready')}"
        )
    return 0 if steps and steps[-1].get("exit_code") == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
