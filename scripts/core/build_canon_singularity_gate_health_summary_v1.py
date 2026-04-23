#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _streak(recent: list[dict[str, Any]]) -> dict[str, Any]:
    if not recent:
        return {"result": None, "count": 0}
    latest_result = recent[-1].get("result")
    cnt = 0
    for row in reversed(recent):
        if row.get("result") == latest_result:
            cnt += 1
        else:
            break
    return {"result": latest_result, "count": cnt}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build health summary from canon quality-gate history JSONL.")
    ap.add_argument(
        "--history-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_quality_gate_history_v1.jsonl",
    )
    ap.add_argument("--window", type=int, default=30, help="Recent event window size for summary.")
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_quality_gate_health_summary_v1.json",
    )
    args = ap.parse_args()

    rows = _read_jsonl(Path(args.history_jsonl))
    rows = sorted(rows, key=lambda x: str(x.get("generated_at_utc", "")))
    recent = rows[-int(args.window) :] if rows else []
    pass_count = sum(1 for r in recent if r.get("result") == "pass")
    fail_count = sum(1 for r in recent if r.get("result") == "fail")

    latest = recent[-1] if recent else None
    last_fail = None
    for row in reversed(recent):
        if row.get("result") == "fail":
            last_fail = row
            break

    denom = len(recent)
    pass_rate = (pass_count / denom) if denom > 0 else 0.0
    streak = _streak(recent)
    latest_result = (latest or {}).get("result")
    if latest_result == "fail":
        health_level = "red"
        recommended_action = "Investigate latest failure and re-run canon chain after fixing source artifact mismatch."
    elif fail_count > 0:
        health_level = "yellow"
        recommended_action = "Monitor window failures; if recurring, inspect trends and tighten upstream checks."
    else:
        health_level = "green"
        recommended_action = "No immediate action. Continue scheduled monitoring."

    out = {
        "schema": "original_corpus_regime_singularity_canon_quality_gate_health_summary_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "history_jsonl": str(args.history_jsonl),
            "window": int(args.window),
        },
        "counts": {
            "history_events_total": len(rows),
            "events_in_window": len(recent),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "pass_rate": round(pass_rate, 4),
        },
        "latest_status": {
            "result": (latest or {}).get("result"),
            "generated_at_utc": (latest or {}).get("generated_at_utc"),
            "error": (latest or {}).get("error"),
        },
        "streak": streak,
        "health_level": health_level,
        "recommended_action": recommended_action,
        "last_failure": {
            "generated_at_utc": (last_fail or {}).get("generated_at_utc"),
            "error": (last_fail or {}).get("error"),
        },
        "recent_events": [
            {
                "generated_at_utc": r.get("generated_at_utc"),
                "result": r.get("result"),
                "error": r.get("error"),
            }
            for r in recent
        ],
    }
    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

