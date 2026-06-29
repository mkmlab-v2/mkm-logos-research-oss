#!/usr/bin/env python3
"""Summarize JSONL shadow log into weekly-style report artifacts (research-only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "reports/btrack_31k41k_prophecy_shadow_log_v1.jsonl"
DEFAULT_JSON_OUT = ROOT / "reports/btrack_31k41k_prophecy_shadow_summary_v1_latest.json"
DEFAULT_MD_OUT = ROOT / "reports/btrack_31k41k_prophecy_shadow_summary_v1_latest.md"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            doc = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(doc, dict):
            rows.append(doc)
    return rows


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def summarize(rows: list[dict[str, Any]], *, tail: int) -> dict[str, Any]:
    if tail > 0:
        rows = rows[-tail:]
    n = len(rows)
    if n == 0:
        return {
            "schema": "btrack_31k41k_prophecy_shadow_summary_v1",
            "generated_at_utc": _iso_now(),
            "research_only": True,
            "non_gating": True,
            "row_count": 0,
            "status": "NO_LOG_ROWS",
        }

    deltas = [_f(r.get("delta_hit_rate")) for r in rows]
    decisions = [str(r.get("decision") or "") for r in rows]
    min_n_ok_count = sum(1 for r in rows if r.get("min_n_ok"))
    all_passed_count = sum(1 for r in rows if r.get("all_passed"))
    positive_delta_count = sum(1 for d in deltas if d > 0)

    latest = rows[-1]
    return {
        "schema": "btrack_31k41k_prophecy_shadow_summary_v1",
        "generated_at_utc": _iso_now(),
        "research_only": True,
        "non_gating": True,
        "row_count": n,
        "status": "ok",
        "latest": latest,
        "aggregates": {
            "delta_hit_rate_mean": round(sum(deltas) / n, 6),
            "delta_hit_rate_min": round(min(deltas), 6),
            "delta_hit_rate_max": round(max(deltas), 6),
            "positive_delta_rows": positive_delta_count,
            "min_n_ok_rows": min_n_ok_count,
            "all_passed_rows": all_passed_count,
            "hold_shadow_only_rows": sum(1 for d in decisions if d == "HOLD_SHADOW_ONLY"),
            "candidate_review_rows": sum(1 for d in decisions if d == "CANDIDATE_ALLOWLIST_REVIEW"),
        },
        "operator_lines": [
            "[MKM-31K41K-SHADOW-SUMMARY]",
            "[HYPO] research_only · NON_GATING · Track A/live auto-merge 없음",
            f"- log_rows={n} delta_mean={round(sum(deltas) / n, 6)} positive_delta_rows={positive_delta_count}",
            f"- latest decision={latest.get('decision')} n={latest.get('n_evaluated')} delta={latest.get('delta_hit_rate')}",
        ],
    }


def render_md(summary: dict[str, Any]) -> str:
    lines = [
        "# B-track 31k/41k prophecy shadow summary (research-only)",
        "",
        "Classification: `[HYPO]` · `NON_GATING` · no Track A / live merge.",
        "",
    ]
    if summary.get("status") == "NO_LOG_ROWS":
        lines.append("_No log rows yet. Run eval → gate → append log._")
        return "\n".join(lines) + "\n"

    agg = summary.get("aggregates") if isinstance(summary.get("aggregates"), dict) else {}
    latest = summary.get("latest") if isinstance(summary.get("latest"), dict) else {}
    lines.extend(
        [
            f"- Generated (UTC): `{summary.get('generated_at_utc')}`",
            f"- Log rows summarized: **{summary.get('row_count')}**",
            f"- Delta hit rate (mean / min / max): **{agg.get('delta_hit_rate_mean')}** / {agg.get('delta_hit_rate_min')} / {agg.get('delta_hit_rate_max')}",
            f"- Positive delta rows: **{agg.get('positive_delta_rows')}**",
            f"- Latest: decision=`{latest.get('decision')}` n=`{latest.get('n_evaluated')}` delta=`{latest.get('delta_hit_rate')}`",
            "",
            "## Operator lines",
            "",
        ]
    )
    for op in summary.get("operator_lines") or []:
        lines.append(f"- {op}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_JSON_OUT)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_MD_OUT)
    ap.add_argument("--tail", type=int, default=0, help="If >0, only summarize last N log rows.")
    args = ap.parse_args()

    rows = _read_rows(args.log_jsonl)
    summary = summarize(rows, tail=int(args.tail))

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(render_md(summary), encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    print(f"WROTE: {args.out_md}")
    print(f"status={summary.get('status')} rows={summary.get('row_count')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
