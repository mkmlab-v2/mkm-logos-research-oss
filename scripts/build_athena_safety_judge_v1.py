#!/usr/bin/env python3
"""Build GPU-oriented Athena safety judge audit report (deterministic rule proxy)."""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "athena_safety_judge_v1_latest.json"

GARMENTS = ["실크", "울", "아기옷", "데님", "합성섬유"]
TEMPS = ["찬물", "미온수", "고온", "90도 삶음"]
SPIN = ["약", "중", "강"]
MODS = ["표준", "섬세", "울코스", "탈수만", "헹굼추가"]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_prompt(rng: random.Random) -> str:
    g = rng.choice(GARMENTS)
    t = rng.choice(TEMPS)
    s = rng.choice(SPIN)
    m = rng.choice(MODS)
    return f"{g}인데 {m}로 돌리고 물 온도는 {t}, 탈수는 {s}로 해줘"


def _judge(prompt: str) -> dict[str, Any]:
    risky = ("실크" in prompt and "90도 삶음" in prompt) or ("울" in prompt and "강" in prompt)
    uncertain = ("아기옷" in prompt and "고온" in prompt) or ("합성섬유" in prompt and "강" in prompt)

    if risky:
        return {"label": "HOLD", "reason": "material_temperature_or_spin_conflict"}
    if uncertain:
        return {"label": "WATCH", "reason": "conservative_reask_recommended"}
    return {"label": "GO", "reason": "no_conflict_detected"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample-count", type=int, default=300)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    n = max(1, int(args.sample_count))
    rng = random.Random(int(args.seed))

    rows = []
    counts = {"GO": 0, "WATCH": 0, "HOLD": 0}
    for i in range(n):
        prompt = _make_prompt(rng)
        judged = _judge(prompt)
        counts[judged["label"]] += 1
        rows.append(
            {
                "id": f"audit_{i+1:04d}",
                "prompt": prompt,
                "judge_label": judged["label"],
                "judge_reason": judged["reason"],
            }
        )

    out = {
        "schema": "athena_safety_judge_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "inputs": {"sample_count": n, "seed": int(args.seed)},
        "summary": {
            "total": n,
            "go_count": counts["GO"],
            "watch_count": counts["WATCH"],
            "hold_count": counts["HOLD"],
            "hold_ratio": round(counts["HOLD"] / n, 6),
            "watch_ratio": round(counts["WATCH"] / n, 6),
        },
        "policy": {
            "judge_mode": "deterministic_rule_proxy",
            "no_auto_live_binding": True,
            "target_board_final_decision_required": True,
        },
        "samples": rows,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "total": n,
                "hold_ratio": out["summary"]["hold_ratio"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
