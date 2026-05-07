#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"

DEFAULT_GATE = ART / "logos_shadow_weekly_gate_latest.json"
DEFAULT_TREND = ART / "logos_shadow_weekly_trend_report_latest.json"
DEFAULT_ALERT = ART / "logos_shadow_alert_decision_latest.json"
DEFAULT_HISTORY = REPORTS / "logos_shadow_weekly_gate_history_v1.jsonl"
DEFAULT_OUT = ART / "logos_shadow_promotion_kpi_progress_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _f(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Build KPI progress snapshot for Logos shadow promotion contract.")
    ap.add_argument("--weekly-gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--weekly-trend-json", type=Path, default=DEFAULT_TREND)
    ap.add_argument("--alert-json", type=Path, default=DEFAULT_ALERT)
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    gate_path = args.weekly_gate_json if args.weekly_gate_json.is_absolute() else ROOT / args.weekly_gate_json
    trend_path = args.weekly_trend_json if args.weekly_trend_json.is_absolute() else ROOT / args.weekly_trend_json
    alert_path = args.alert_json if args.alert_json.is_absolute() else ROOT / args.alert_json
    history_path = args.history_jsonl if args.history_jsonl.is_absolute() else ROOT / args.history_jsonl
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    for p in (gate_path, trend_path, alert_path):
        if not p.is_file():
            raise SystemExit(f"Missing required json: {p}")

    gate = _read_json(gate_path)
    trend = _read_json(trend_path)
    alert = _read_json(alert_path)

    # Append strict gate snapshots for consecutive GO tracking.
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_rows = _read_jsonl(history_path)
    snapshot = {
        "generated_at_utc": _now(),
        "window_end_utc": gate.get("window_end_utc"),
        "decision": gate.get("decision"),
        "samples": ((gate.get("metrics") or {}).get("samples")),
    }
    if history_rows:
        last = history_rows[-1]
        same_window = str(last.get("window_end_utc") or "") == str(snapshot.get("window_end_utc") or "")
        if same_window:
            history_rows[-1] = snapshot
        else:
            history_rows.append(snapshot)
    else:
        history_rows.append(snapshot)
    history_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in history_rows) + "\n", encoding="utf-8")

    consecutive_go = 0
    for row in reversed(history_rows):
        if str(row.get("decision")) == "GO":
            consecutive_go += 1
        else:
            break

    checks = {
        "strict_go_consecutive_2w": consecutive_go >= 2,
        "strict_samples_ge_7": int(((gate.get("metrics") or {}).get("samples") or 0)) >= 7,
        "trend_mean_top1_cosine_ge_0_10": _f((trend.get("summary") or {}).get("mean_top1_cosine_7d_avg"), 0.0) >= 0.10,
        "trend_query_error_rate_le_0_05": _f((trend.get("summary") or {}).get("query_error_rate_7d_aggregate"), 1.0) <= 0.05,
        "trend_low_conf_rate_le_0_30": _f((trend.get("summary") or {}).get("low_conf_rate_7d_avg"), 1.0) <= 0.30,
        "alert_should_alert_false": ((alert.get("alert") or {}).get("should_alert") is False),
    }
    passed = all(checks.values())
    out = {
        "schema": "logos_shadow_promotion_kpi_progress_v1",
        "generated_at_utc": _now(),
        "status": "READY_FOR_REVIEW" if passed else "IN_PROGRESS",
        "passed": passed,
        "consecutive_strict_go_windows": consecutive_go,
        "required_consecutive_strict_go_windows": 2,
        "checks": checks,
        "track_wall": {"shadow_only": True, "promotion_to_a_track_allowed": False, "auto_trade_enable": False},
        "evidence_paths": {
            "weekly_gate_json": str(gate_path.resolve()),
            "weekly_trend_json": str(trend_path.resolve()),
            "alert_json": str(alert_path.resolve()),
            "history_jsonl": str(history_path.resolve()),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "status": out["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

