#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def safe_load(path: Path) -> tuple[bool, dict[str, Any] | None]:
    if not path.is_file():
        return False, None
    try:
        return True, load_json(path)
    except Exception:
        return False, None


def main() -> int:
    ap = argparse.ArgumentParser(description="Build MKM model-mix cost/latency report artifact.")
    ap.add_argument("--workspace-root", default="C:/workspace")
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/mkm_model_mix_cost_latency_latest.json",
    )
    ap.add_argument(
        "--output-md",
        default="docs/final/artifacts/mkm_model_mix_cost_latency_latest.md",
    )
    args = ap.parse_args()

    root = resolve(args.workspace_root)
    out_json = resolve(args.output_json)
    out_md = resolve(args.output_md)

    p_meter_sum = root / "docs/final/artifacts/track_a_metering_summary_latest.json"
    p_meter_week = root / "docs/final/artifacts/track_a_metering_weekly_report_latest.json"
    p_latency = root / "docs/final/artifacts/pointerguard_latency_benchmark_latest.json"
    p_cost = root / "docs/final/artifacts/cost_watch_monitor_latest.json"
    p_status = root / "docs/final/artifacts/mkm_ai_status_pointer_latest.json"

    ok_meter_sum, meter_sum = safe_load(p_meter_sum)
    ok_meter_week, meter_week = safe_load(p_meter_week)
    ok_latency, latency = safe_load(p_latency)
    ok_cost, cost = safe_load(p_cost)
    ok_status, status = safe_load(p_status)

    tracka_events = meter_week.get("events_in_window") if ok_meter_week else None
    tracka_hit = meter_week.get("target_band_hit_rate") if ok_meter_week else None
    billing_cost = (cost or {}).get("billing", {}).get("api_cost_usd") if ok_cost else None
    token_saving = (cost or {}).get("compression", {}).get("global_token_saving_rate") if ok_cost else None
    latency_cases = (latency or {}).get("cases", []) if ok_latency else []
    best_case = None
    if isinstance(latency_cases, list) and latency_cases:
        sorted_cases = sorted(
            [c for c in latency_cases if isinstance(c, dict)],
            key=lambda x: float(((x.get("latency_ms") or {}).get("p50")) or 10**9),
        )
        if sorted_cases:
            best_case = {
                "name": sorted_cases[0].get("name"),
                "p50_ms": (sorted_cases[0].get("latency_ms") or {}).get("p50"),
                "p95_ms": (sorted_cases[0].get("latency_ms") or {}).get("p95"),
                "throughput_rps": sorted_cases[0].get("throughput_rps"),
            }

    payload = {
        "schema": "mkm_model_mix_cost_latency_report_v1",
        "generated_at_utc": utc_now(),
        "status_context": {
            "system_status": (status or {}).get("status"),
            "promotion_decision": (status or {}).get("decision"),
            "weekly_pass_rate_percent": (status or {}).get("weekly_pass_rate_percent"),
            "weekly_sample_count": (status or {}).get("weekly_sample_count"),
        },
        "sources": {
            "track_a_metering_summary": str(p_meter_sum),
            "track_a_metering_weekly": str(p_meter_week),
            "pointerguard_latency_benchmark": str(p_latency),
            "cost_watch_monitor": str(p_cost),
        },
        "availability": {
            "track_a_metering_summary_ok": ok_meter_sum,
            "track_a_metering_weekly_ok": ok_meter_week,
            "pointerguard_latency_ok": ok_latency,
            "cost_watch_ok": ok_cost,
            "status_pointer_ok": ok_status,
        },
        "kpis": {
            "track_a_events_in_window": tracka_events,
            "track_a_target_band_hit_rate": tracka_hit,
            "billing_api_cost_usd": billing_cost,
            "compression_global_token_saving_rate": token_saving,
            "best_latency_case": best_case,
        },
        "decision_hint": (
            "KEEP_OPTIMIZATION_LOOP_ACTIVE"
            if all([ok_meter_week, ok_latency, ok_cost])
            else "NEEDS_MORE_EVIDENCE"
        ),
        "note": "This report is for BL-006 optimization loop tracking and does not alter governance gates.",
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# MKM Model-Mix Cost/Latency Report",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- decision_hint: `{payload['decision_hint']}`",
        "",
        "## Snapshot",
        f"- system_status: `{payload['status_context']['system_status']}`",
        f"- promotion_decision: `{payload['status_context']['promotion_decision']}`",
        f"- weekly_pass_rate_percent: `{payload['status_context']['weekly_pass_rate_percent']}`",
        f"- weekly_sample_count: `{payload['status_context']['weekly_sample_count']}`",
        "",
        "## KPIs",
        f"- track_a_events_in_window: `{tracka_events}`",
        f"- track_a_target_band_hit_rate: `{tracka_hit}`",
        f"- billing_api_cost_usd: `{billing_cost}`",
        f"- compression_global_token_saving_rate: `{token_saving}`",
        f"- best_latency_case: `{best_case}`",
        "",
        "## Note",
        "- BL-006 tracking artifact only. No automatic gate promotion implied.",
    ]
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"cost/latency report json written: {out_json}")
    print(f"cost/latency report md written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
