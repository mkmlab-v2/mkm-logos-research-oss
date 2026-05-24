#!/usr/bin/env python3
"""[HYPO] One-shot: per-date directions with logos-off v1 weights + min_conf (parallel lane)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG_SRC = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
OUT_REPORT = ROOT / "reports/btrack_logos_off_perdate_parallel_v1_latest.json"
WORK = ROOT / "reports/btrack_logos_off_perdate_parallel_work"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"


def main() -> int:
    min_conf = float(os.environ.get("MKM_BTRACK_MIN_DIRECTION_CONFIDENCE", "0.35"))
    cfg = json.loads(CFG_SRC.read_text(encoding="utf-8"))
    cfg["weights"] = {"price": 0.0, "macro": 0.0, "news": 0.0, "myeongni_sasang": 1.0}
    rules = cfg.get("rules") if isinstance(cfg.get("rules"), dict) else {}
    rules["ensemble_mode"] = "v1"
    rules["min_direction_confidence"] = min_conf
    rules["drop_logos_on_conflict"] = True
    cfg["rules"] = rules

    WORK.mkdir(parents=True, exist_ok=True)
    cfg_path = WORK / "ensemble_logos_off.json"
    per_date = WORK / "per_date.json"
    score = WORK / "score.json"
    eval_out = WORK / "eval.json"
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    env = os.environ.copy()
    env["MKM_BTRACK_MIN_DIRECTION_CONFIDENCE"] = str(min_conf)

    steps = [
        [
            sys.executable,
            "scripts/build_btrack_ensemble_per_date_directions_v1.py",
            "--recent-trading-days",
            "30",
            "--ensemble-config",
            str(cfg_path),
            "--output",
            str(per_date),
        ],
        [
            sys.executable,
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--recent-trading-days",
            "30",
            "--force-dual-leg-panel",
            "--btc-csv",
            str(BTC),
            "--kospi-csv",
            str(KOSPI),
            "--per-date-direction-json",
            str(per_date),
            "--output",
            str(score),
        ],
        [
            sys.executable,
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            str(score),
            "--output",
            str(eval_out),
        ],
    ]
    for cmd in steps:
        p = subprocess.run(cmd, cwd=str(ROOT), env=env)
        if p.returncode != 0:
            return int(p.returncode)

    ev = json.loads(eval_out.read_text(encoding="utf-8"))
    m = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
    report = {
        "schema": "btrack_logos_off_perdate_parallel_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "min_direction_confidence": min_conf,
        "weights": cfg["weights"],
        "artifacts": {
            "per_date_json": str(per_date.relative_to(ROOT)),
            "score_json": str(score.relative_to(ROOT)),
            "eval_json": str(eval_out.relative_to(ROOT)),
        },
        "metrics": m,
    }
    OUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT_REPORT.resolve()}")
    print(
        f"BTC headline: all-rows={m.get('price_directional_hit_rate')} "
        f"dir-only={m.get('price_hit_rate_on_directional_calls')} "
        f"calls={m.get('n_directional_calls')} n={m.get('n_evaluated')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
