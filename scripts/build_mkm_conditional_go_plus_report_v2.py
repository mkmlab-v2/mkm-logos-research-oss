#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REP = ROOT / "reports"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_s() -> str:
    return _now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _parse_ts(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Conditional GO+ operational report (no target-board needed).")
    ap.add_argument("--window-hours", type=int, default=24)
    ap.add_argument(
        "--window-minutes",
        type=int,
        default=0,
        help="If >0, overrides --window-hours for cycle-log filtering (accelerated burn-in).",
    )
    ap.add_argument(
        "--min-samples-for-ready",
        type=int,
        default=12,
        help="Minimum cycle-log samples in window to allow CONDITIONAL_GO_PLUS_READY.",
    )
    ap.add_argument(
        "--tail-samples",
        type=int,
        default=0,
        help="If >0, after time-window filter keep only the last N cycle-log rows (file order). "
        "Use after accelerated burn-in to exclude older WATCH samples in the same wall-clock window.",
    )
    ap.add_argument("--cycle-log-jsonl", type=Path, default=REP / "mkm_orchestrator_go_cycle_log.jsonl")
    ap.add_argument("--stability-json", type=Path, default=ART / "mkm_global_orchestrator_go_stability_latest.json")
    ap.add_argument("--demotion-json", type=Path, default=ART / "mkm_orchestrator_auto_demotion_latest.json")
    ap.add_argument("--promotion-json", type=Path, default=ART / "mkm_orchestrator_auto_promotion_latest.json")
    ap.add_argument("--latency-json", type=Path, default=ART / "n8n_latency_probe_latest.json")
    ap.add_argument("--readiness-json", type=Path, default=ART / "companion_ecosystem_go_readiness_gate_latest.json")
    ap.add_argument("--output-json", type=Path, default=ART / "companion_ecosystem_conditional_go_plus_report_latest.json")
    args = ap.parse_args()

    log_path = args.cycle_log_jsonl if args.cycle_log_jsonl.is_absolute() else ROOT / args.cycle_log_jsonl
    rows = _read_jsonl(log_path)
    if int(args.window_minutes or 0) > 0:
        cutoff = _now() - timedelta(minutes=max(1, int(args.window_minutes)))
        window_meta = {"kind": "minutes", "value": int(args.window_minutes)}
    else:
        cutoff = _now() - timedelta(hours=max(1, args.window_hours))
        window_meta = {"kind": "hours", "value": int(args.window_hours)}
    rows_w = [r for r in rows if (_parse_ts(str(r.get("ts_utc", ""))) or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff]
    tail_n = int(args.tail_samples or 0)
    if tail_n > 0:
        rows_w = rows_w[-tail_n:]

    total = len(rows_w)
    go_count = sum(1 for r in rows_w if str(r.get("current_decision", "")).upper() == "GO")
    watch_count = sum(1 for r in rows_w if str(r.get("current_decision", "")).upper() == "WATCH")
    hold_count = sum(1 for r in rows_w if str(r.get("current_decision", "")).upper() == "HOLD")
    down_count = sum(1 for r in rows_w if bool(r.get("down_transition_detected", False)))
    go_ratio = (go_count / total) if total > 0 else 0.0

    stability = _read_json(args.stability_json if args.stability_json.is_absolute() else ROOT / args.stability_json)
    demotion = _read_json(args.demotion_json if args.demotion_json.is_absolute() else ROOT / args.demotion_json)
    promotion = _read_json(args.promotion_json if args.promotion_json.is_absolute() else ROOT / args.promotion_json)
    latency = _read_json(args.latency_json if args.latency_json.is_absolute() else ROOT / args.latency_json)
    readiness = _read_json(args.readiness_json if args.readiness_json.is_absolute() else ROOT / args.readiness_json)

    p99 = float(
        ((latency.get("latency_ms") or {}).get("p99"))
        or ((latency.get("metrics") or {}).get("p99_ms"))
        or (latency.get("p99_ms") or 0.0)
    )
    drift_pass = bool(((readiness.get("metrics") or {}).get("drift_pass")))
    pass_p99 = bool(((latency.get("gate") or {}).get("pass_p99_le_500")))

    min_samples = max(1, int(args.min_samples_for_ready))
    integrity_ok = bool(go_ratio >= 0.9 and down_count == 0 and drift_pass and pass_p99 and total >= min_samples)
    grade = "CONDITIONAL_GO_PLUS_READY" if integrity_ok else "CONDITIONAL_GO_PLUS_WATCH"
    report = {
        "schema": "companion_ecosystem_conditional_go_plus_report_v2",
        "generated_at_utc": _now_s(),
        "window": window_meta,
        "window_hours": int(args.window_hours),
        "window_minutes_override": int(args.window_minutes or 0),
        "tail_samples_override": int(tail_n),
        "ops_metrics": {
            "samples": total,
            "go_count": go_count,
            "watch_count": watch_count,
            "hold_count": hold_count,
            "go_ratio": round(go_ratio, 6),
            "down_transition_count": down_count,
        },
        "latest_state": {
            "stability": stability,
            "auto_demotion": demotion,
            "auto_promotion": promotion,
            "latency_p99_ms": p99,
            "latency_pass_p99_le_500": pass_p99,
            "drift_pass": drift_pass,
        },
        "assessment": {
            "grade": grade,
            "min_samples_for_ready": min_samples,
            "integrity_checks": {
                "go_ratio_ge_0_9": bool(go_ratio >= 0.9),
                "down_transition_count_eq_0": bool(down_count == 0),
                "drift_pass": drift_pass,
                "latency_pass_p99_le_500": pass_p99,
                "samples_ge_min": bool(total >= min_samples),
            },
            "note": "Board measurement excluded by design; this report evaluates operational integrity only. Accelerated windows trade wall-clock for sample density; interpret together with cycle_log timestamps. "
            + (
                f"tail_samples={tail_n} applied (last N rows after time filter). "
                if tail_n > 0
                else ""
            ),
        },
        "refs": {
            "cycle_log_jsonl": str(log_path),
            "stability_json": str(args.stability_json),
            "demotion_json": str(args.demotion_json),
            "promotion_json": str(args.promotion_json),
            "latency_json": str(args.latency_json),
            "readiness_json": str(args.readiness_json),
        },
    }
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "grade": grade, "samples": total, "out": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
