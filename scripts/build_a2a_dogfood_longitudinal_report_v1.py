#!/usr/bin/env python3
"""A2A Cursor dogfood longitudinal report — Tier2 shadow + Tier3 handoff + L1L2 chain logs.

  py scripts/build_a2a_dogfood_longitudinal_report_v1.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/a2a_dogfood_longitudinal_report_v1_latest.json"
DEFAULT_MD = ROOT / "docs/final/artifacts/a2a_dogfood_longitudinal_report_v1_latest.md"

LOGS = {
    "l2_shadow": ROOT / "docs/final/artifacts/a2a_l2_shadow_log.jsonl",
    "tier3_handoff": ROOT / "docs/final/artifacts/a2a_tier3_cursor_wire_handoff_log.jsonl",
    "l1_l2_chain": ROOT / "docs/final/artifacts/a2a_l1_l2_chain_pilot_log.jsonl",
    "tp01_ops": ROOT / "docs/final/artifacts/a2a_tp01_ops_measurement_log.jsonl",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _series_stats(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    vals = [float(r[key]) for r in rows if r.get(key) is not None]
    if not vals:
        return {"count": 0, "latest": None, "mean": None, "min": None, "max": None}
    return {
        "count": len(vals),
        "latest": vals[-1],
        "mean": round(mean(vals), 6),
        "min": min(vals),
        "max": max(vals),
    }


def _nested_series_stats(rows: list[dict[str, Any]], nested_key: str, value_key: str) -> dict[str, Any]:
    vals: list[float] = []
    for r in rows:
        block = r.get(nested_key) or {}
        if isinstance(block, dict) and block.get(value_key) is not None:
            vals.append(float(block[value_key]))
    if not vals:
        return {"count": 0, "latest": None, "mean": None, "min": None, "max": None}
    return {
        "count": len(vals),
        "latest": vals[-1],
        "mean": round(mean(vals), 6),
        "min": min(vals),
        "max": max(vals),
    }


def _drift_flag(latest: float | None, baseline: float | None, *, drop_threshold: float = 0.10) -> bool:
    if latest is None or baseline is None or baseline <= 0:
        return False
    return latest < baseline * (1.0 - drop_threshold)


def _series_stats_by_lane(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    by_lane: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        lane = row.get("lane") or "unknown"
        by_lane.setdefault(str(lane), []).append(row)
    return {lane: _series_stats(lane_rows, key) for lane, lane_rows in sorted(by_lane.items())}


def _tier3_jaccard_alerts(rows: list[dict[str, Any]], *, drop_delta: float = 0.15) -> list[str]:
    alerts: list[str] = []
    by_lane = _series_stats_by_lane(rows, "expand_jaccard")
    for lane, stats in by_lane.items():
        latest = stats.get("latest")
        mean_val = stats.get("mean")
        if latest is not None and mean_val is not None and latest < mean_val - drop_delta:
            alerts.append(f"tier3_expand_jaccard_drop_vs_mean:{lane}")
    return alerts


def build_report(root: Path) -> dict[str, Any]:
    streams = {name: _read_jsonl(path) for name, path in LOGS.items()}
    l2 = streams["l2_shadow"]
    tier3 = streams["tier3_handoff"]
    l1l2 = streams["l1_l2_chain"]
    tp01 = streams["tp01_ops"]

    l2_savings = _series_stats(l2, "l2_savings_ratio")
    tier3_savings = _series_stats(tier3, "wire_savings_ratio")
    tier3_j = _series_stats(tier3, "expand_jaccard")
    tier3_j_by_lane = _series_stats_by_lane(tier3, "expand_jaccard")
    l1l2_e2e = _nested_series_stats(l1l2, "aggregate", "mean_end_to_end_savings_vs_naive")
    tp01_savings = _series_stats(tp01, "tp01_savings_ratio")

    alerts: list[str] = []
    if _drift_flag(l2_savings.get("latest"), l2_savings.get("mean")):
        alerts.append("l2_shadow_savings_drop_vs_mean")
    if _drift_flag(tier3_savings.get("latest"), tier3_savings.get("mean")):
        alerts.append("tier3_wire_savings_drop_vs_mean")
    alerts.extend(_tier3_jaccard_alerts(tier3))

    ok = len(l2) >= 1 and len(l1l2) >= 1

    return {
        "schema": "a2a_dogfood_longitudinal_report_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "report_ok": ok,
        "alerts": alerts,
        "log_row_counts": {k: len(v) for k, v in streams.items()},
        "metrics": {
            "l2_shadow_savings": l2_savings,
            "tier3_wire_savings": tier3_savings,
            "tier3_expand_jaccard": tier3_j,
            "tier3_expand_jaccard_by_lane": tier3_j_by_lane,
            "l1_l2_e2e_savings": l1l2_e2e,
            "tp01_savings": tp01_savings,
        },
        "latest_artifacts": {
            "l2_shadow": "docs/final/artifacts/a2a_l2_shadow_measurement_v1_latest.json",
            "tier3_lane_index": "docs/final/artifacts/a2a_tier3_cursor_wire_handoff_lane_index_v1_latest.json",
            "commander_brief": "docs/final/artifacts/a2a_commander_stack_brief_corrected_v1.md",
        },
        "boundary_ack": "[HYPO] Dogfood observability only. Alerts are research signals — not SEND or Track A gates.",
        "repro_command": "py scripts/build_a2a_dogfood_longitudinal_report_v1.py",
    }


def render_md(doc: dict[str, Any]) -> str:
    m = doc.get("metrics") or {}
    l2 = m.get("l2_shadow_savings") or {}
    t3 = m.get("tier3_wire_savings") or {}
    t3j = m.get("tier3_expand_jaccard") or {}
    t3j_lane = m.get("tier3_expand_jaccard_by_lane") or {}
    alerts = doc.get("alerts") or []
    counts = doc.get("log_row_counts") or {}
    alert_line = ", ".join(alerts) if alerts else "none"
    lane_lines = []
    for lane, row in sorted(t3j_lane.items()):
        lane_lines.append(
            f"| {lane} | {row.get('latest')} | {row.get('mean')} | {row.get('min')} | {row.get('max')} |"
        )
    lane_table = "\n".join(lane_lines) if lane_lines else "| (no tier3 rows) | | | | |"
    return f"""# A2A Cursor dogfood — longitudinal report [HYPO]

- generated: `{doc.get('generated_at_utc')}`
- report_ok: `{doc.get('report_ok')}`
- alerts: **{alert_line}**

## Log rows

| stream | rows |
|--------|-----:|
| l2_shadow | {counts.get('l2_shadow', 0)} |
| tier3_handoff | {counts.get('tier3_handoff', 0)} |
| l1_l2_chain | {counts.get('l1_l2_chain', 0)} |
| tp01_ops | {counts.get('tp01_ops', 0)} |

## Latest metrics

| metric | latest | mean | min | max |
|--------|-------:|-----:|----:|----:|
| L2 shadow savings | {l2.get('latest')} | {l2.get('mean')} | {l2.get('min')} | {l2.get('max')} |
| Tier3 wire savings | {t3.get('latest')} | {t3.get('mean')} | {t3.get('min')} | {t3.get('max')} |
| Tier3 expand J (all) | {t3j.get('latest')} | {t3j.get('mean')} | {t3j.get('min')} | {t3j.get('max')} |

## Tier3 expand J by lane

| lane | latest | mean | min | max |
|------|-------:|-----:|----:|----:|
{lane_table}

SEND_GATE: HOLD · B-track observability only.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    ap.add_argument("--strict-exit", action="store_true")
    args = ap.parse_args()

    doc = build_report(ROOT)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md_out.write_text(render_md(doc), encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"WROTE: {args.md_out}")
    print(f"report_ok={doc.get('report_ok')} alerts={doc.get('alerts')}")
    if args.strict_exit and not doc.get("report_ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
