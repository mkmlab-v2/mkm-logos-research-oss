#!/usr/bin/env python3
"""Build weekly A/B comparison report for anchor operating actions."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_HISTORY = ART / "external_bible_anchor_promotion_history_log.jsonl"
DEFAULT_PREFLIGHT = ART / "emotion_state_live_preflight_gate_latest.json"
DEFAULT_LAYER5 = ART / "layer5_policy_gate_benchmark_latest.json"
DEFAULT_SUSTAIN = ART / "external_bible_anchor_promotion_sustain_gate_latest.json"
DEFAULT_OUT = ART / "external_bible_anchor_weekly_ab_report_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _pass_rate(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    passed = 0
    for r in rows:
        if str(r.get("regression_status") or "") == "PASS":
            passed += 1
    return round(passed / len(rows), 4)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--preflight-json", type=Path, default=DEFAULT_PREFLIGHT)
    ap.add_argument("--layer5-json", type=Path, default=DEFAULT_LAYER5)
    ap.add_argument("--sustain-json", type=Path, default=DEFAULT_SUSTAIN)
    ap.add_argument("--window", type=int, default=12)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows = _read_jsonl(args.history_jsonl)
    if args.window > 0:
        rows = rows[-int(args.window) :]

    monitor_rows = [r for r in rows if str(r.get("effective_action") or "") == "monitor_only"]
    adopt_rows = [
        r
        for r in rows
        if str(r.get("effective_action") or "") in {"adopt_limited", "adopt_limited_strict"}
    ]

    preflight = _read_json(args.preflight_json)
    layer5 = _read_json(args.layer5_json)
    sustain = _read_json(args.sustain_json)

    monitor_pass_rate = _pass_rate(monitor_rows)
    adopt_pass_rate = _pass_rate(adopt_rows)
    pass_rate_delta = round(adopt_pass_rate - monitor_pass_rate, 4)
    layer5_fpr = float(((layer5.get("metrics") or {}).get("false_positive_rate")) or 0.0)

    status = "PASS" if (len(monitor_rows) > 0 and len(adopt_rows) > 0) else "WARMUP"
    out = {
        "schema": "external_bible_anchor_weekly_ab_report_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "history_jsonl": str(args.history_jsonl).replace("\\", "/"),
            "preflight_json": str(args.preflight_json).replace("\\", "/"),
            "layer5_json": str(args.layer5_json).replace("\\", "/"),
            "sustain_json": str(args.sustain_json).replace("\\", "/"),
            "window": int(args.window),
        },
        "summary": {
            "status": status,
            "window_rows": len(rows),
            "monitor_rows": len(monitor_rows),
            "adopt_rows": len(adopt_rows),
            "monitor_pass_rate": monitor_pass_rate,
            "adopt_pass_rate": adopt_pass_rate,
            "pass_rate_delta_adopt_minus_monitor": pass_rate_delta,
            "layer5_fpr": layer5_fpr,
            "preflight_decision": preflight.get("decision"),
            "sustain_status": sustain.get("status"),
            "sustain_pass_streak": ((sustain.get("current") or {}).get("pass_streak")),
            "sustain_fail_streak": ((sustain.get("current") or {}).get("fail_streak")),
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "status": status, "output_json": str(args.output_json).replace("\\", "/")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
