#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                rows.append(obj)
        except Exception:
            continue
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Alert when top symbol drifts too frequently.")
    ap.add_argument("--survivability-json", default="docs/final/artifacts/multi_symbol_walkforward_survivability_latest.json")
    ap.add_argument("--history-jsonl", default="docs/final/artifacts/multi_symbol_top_drift_history_latest.jsonl")
    ap.add_argument("--output-json", default="docs/final/artifacts/multi_symbol_top_drift_alert_latest.json")
    ap.add_argument("--window-size", type=int, default=7)
    ap.add_argument("--max-switches", type=int, default=3)
    args = ap.parse_args()

    sp = resolve(args.survivability_json)
    hp = resolve(args.history_jsonl)
    op = resolve(args.output_json)
    if not sp.is_file():
        raise SystemExit(f"missing survivability json: {sp}")

    survivability = load(sp)
    summary = survivability.get("summary") if isinstance(survivability.get("summary"), dict) else {}
    top_symbol = str(summary.get("top_symbol_by_survivability") or "unknown")
    now_utc = now()

    history = read_jsonl(hp)
    history.append({"at_utc": now_utc, "top_symbol": top_symbol})
    hp.parent.mkdir(parents=True, exist_ok=True)
    hp.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in history) + "\n", encoding="utf-8")

    window_size = max(int(args.window_size), 2)
    window = history[-window_size:]
    switches = 0
    prev = None
    for row in window:
        sym = str(row.get("top_symbol") or "unknown")
        if prev is not None and sym != prev:
            switches += 1
        prev = sym

    should_alert = switches > int(args.max_switches)
    out = {
        "schema": "multi_symbol_top_drift_alert_v1",
        "generated_at_utc": now_utc,
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "inputs": {
            "survivability_json": str(sp),
            "history_jsonl": str(hp),
            "window_size": window_size,
            "max_switches": int(args.max_switches),
        },
        "window_stats": {
            "rows_in_window": len(window),
            "switch_count": switches,
            "current_top_symbol": top_symbol,
            "window_top_symbols": [str(r.get("top_symbol") or "unknown") for r in window],
        },
        "gate_eval": {
            "should_alert": should_alert,
            "severity": "warning" if should_alert else "none",
            "promotion_hold": should_alert,
            "reasons": ["top_symbol_drift_exceeds_threshold"] if should_alert else [],
        },
    }
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

