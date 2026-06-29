#!/usr/bin/env python3
"""Append one W22 DoD5 row to kospi morning brief action log."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--eval-date", type=str, default=None)
    args = ap.parse_args()

    root = args.workspace_root
    dual = json.loads(
        (root / "docs/final/artifacts/prophecy_hit_rate_dual_leg_comparison_latest.json").read_text(
            encoding="utf-8-sig"
        )
    )
    eval_doc = json.loads(
        (root / "reports/prophecy_hit_rate_eval_daily_operational_latest.json").read_text(encoding="utf-8-sig")
    )
    k = (dual.get("legs") or {}).get("kospi") or {}
    eval_date = args.eval_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = {
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lane": "logos_mvp_w22_dod5",
        "eval_date": eval_date,
        "kospi_hit_rate": k.get("price_directional_hit_rate"),
        "n_evaluated": k.get("n_evaluated"),
        "dual_leg_pooled_hit_rate": (eval_doc.get("metrics") or {}).get("price_directional_hit_rate"),
        "dual_leg_n": (eval_doc.get("metrics") or {}).get("n_evaluated"),
        "final_action_tag": "WATCH",
        "hypothesis_tier": "B",
        "research_only": True,
    }
    log = root / "reports/kospi_morning_brief_action_log.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": True, "lane": row["lane"], "ts_utc": row["ts_utc"], "log": str(log)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
