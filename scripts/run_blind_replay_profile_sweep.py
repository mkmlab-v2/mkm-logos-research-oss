# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.9, K:0.8, M:0.5}
# Balance: 90
# Purpose: Run A/B/C blind replay prediction sweep and rank profiles.
# Keywords: blind-replay, sweep, profile, ranking, exploratory_only
#!/usr/bin/env python3
"""Run A/B/C prediction profiles and score each against blind replay answer key."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BLIND_DIR = ROOT / "reports" / "constitution" / "btrack_pilot" / "blind_replay"
SCORE_LATEST = BLIND_DIR / "blind_replay_score_latest.json"
OUT_RANKING = BLIND_DIR / "blind_replay_profile_ranking_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=ROOT, text=True)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Run blind replay A/B/C profile sweep and ranking.")
    ap.add_argument("--public-dataset", type=Path, required=True)
    ap.add_argument("--answer-key", type=Path, required=True)
    ap.add_argument("--profiles", default="A,B,C", help="Comma-separated profiles (e.g. A,B,C or A)")
    ap.add_argument("--out", type=Path, default=OUT_RANKING)
    args = ap.parse_args()

    profiles = [p.strip().upper() for p in str(args.profiles).split(",") if p.strip()]
    if not profiles:
        raise SystemExit("No profiles selected. Use --profiles A,B,C")
    rows: list[dict[str, Any]] = []
    for p in profiles:
        pred_path = BLIND_DIR / f"blind_replay_predictions_12ai_proxy_{p}_latest.jsonl"
        _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "predict_blind_replay_12ai_proxy.py"),
                "--public-dataset",
                str(args.public_dataset),
                "--out",
                str(pred_path),
                "--profile",
                p,
            ]
        )
        _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "score_blind_historical_replay.py"),
                "--answer-key",
                str(args.answer_key),
                "--predictions",
                str(pred_path),
            ]
        )
        score = _read_json(SCORE_LATEST)
        metrics = score.get("metrics") if isinstance(score.get("metrics"), dict) else {}
        counts = score.get("counts") if isinstance(score.get("counts"), dict) else {}
        rows.append(
            {
                "profile": p,
                "hit_rate": float(metrics.get("hit_rate") or 0.0),
                "balanced_accuracy": float(metrics.get("balanced_accuracy") or 0.0),
                "coverage_rate": float(metrics.get("coverage_rate") or 0.0),
                "matched": int(counts.get("matched") or 0),
                "hit": int(counts.get("hit") or 0),
                "prediction_path": str(pred_path.resolve()),
            }
        )

    rows.sort(key=lambda x: (x["balanced_accuracy"], x["hit_rate"]), reverse=True)
    best = rows[0] if rows else None
    doc = {
        "schema": "blind_replay_profile_ranking_v1",
        "generated_at_utc": _utc_now(),
        "exploratory_only": True,
        "a_track_binding_forbidden": True,
        "input": {
            "public_dataset": str(args.public_dataset.resolve()),
            "answer_key": str(args.answer_key.resolve()),
        },
        "profiles": rows,
        "best_profile": best,
        "note": "Profile sweep for B-track blind replay only. No live binding.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out.resolve()}")
    if best:
        print(
            "best_profile={p} balanced_accuracy={ba} hit_rate={hr}".format(
                p=best["profile"], ba=best["balanced_accuracy"], hr=best["hit_rate"]
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
