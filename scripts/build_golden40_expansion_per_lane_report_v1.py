#!/usr/bin/env python3
"""B-track: golden_core + per-lane blended report (headline uses golden_core only)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ISOLATION = ROOT / "reports/golden40_expansion_lane_isolation_summary_v1_latest.json"
DEFAULT_COOC = ROOT / "reports/other_cooc_cartesian_routing_poc_v2_latest.json"
DEFAULT_OUT = ROOT / "reports/golden40_expansion_per_lane_report_v1_latest.json"

HEADLINE_POLICY = ROOT / "reports/compression_track_a_headline_policy_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _render_section(title: str, lines: list[str]) -> str:
    body = "\n".join(f"- {line}" for line in lines)
    return f"## {title}\n\n{body}\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Golden40 per-lane report v1")
    ap.add_argument("--isolation-json", type=Path, default=DEFAULT_ISOLATION)
    ap.add_argument("--cooc-json", type=Path, default=DEFAULT_COOC)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.isolation_json.is_file():
        print(f"missing: {args.isolation_json}", file=sys.stderr)
        return 2

    iso = _load(args.isolation_json)
    cooc = _load(args.cooc_json) if args.cooc_json.is_file() else {}
    gc = iso.get("golden_core_baseline_n400") or {}

    lane_rows: list[dict[str, Any]] = []
    md_lines: list[str] = []
    for mode, pool in (iso.get("pools") or {}).items():
        if not isinstance(pool, dict) or pool.get("missing"):
            continue
        n400 = pool.get("n400") or {}
        row = {
            "pool_mode": mode,
            "blended_jaccard_n400": n400.get("blended_jaccard"),
            "golden_core_jaccard_n400": n400.get("golden_core_jaccard"),
            "delta_jaccard_pp": n400.get("delta_jaccard_pp"),
            "blended_floor_ok": n400.get("blended_floor_ok"),
            "golden_core_floor_ok": n400.get("golden_core_floor_ok"),
            "expansion_dilution": n400.get("expansion_dilution"),
            "actual_cases": n400.get("actual"),
            "max_pool": n400.get("max_pool"),
        }
        lane_rows.append(row)
        md_lines.append(
            f"**{mode}**: blended={n400.get('blended_jaccard')} gc={n400.get('golden_core_jaccard')} "
            f"Δ={n400.get('delta_jaccard_pp')}pp dilution={n400.get('expansion_dilution')}"
        )

    headline_hold = "HOLD"
    if HEADLINE_POLICY.is_file():
        headline_hold = str(_load(HEADLINE_POLICY).get("headline_kpi_update") or "HOLD")

    cooc_proceed = bool(cooc.get("proceed_to_bench_hook"))
    sections_md = [
        _render_section(
            "Headline KPI (Track A policy)",
            [
                f"Use **golden_core only** for headline: Jaccard **{gc.get('golden_core_jaccard')}** (FAIL-COMP-004).",
                f"headline_kpi_update: **{headline_hold}** — do not use blended N400 aggregate.",
                "Frozen MS paste 47.5%/0.890 remains reference-only, not disk remeasure.",
            ],
        ),
        _render_section("Per-lane N=400 (blended vs golden_core)", md_lines),
        _render_section(
            "other:: cooc routing (prefix-gated v2)",
            [
                f"proceed_to_bench_hook: **{cooc_proceed}**",
                f"isolate_high count: {(cooc.get('tiers') or {}).get('isolate_high', {}).get('count')}",
                f"policy: {(cooc.get('routing_policy_draft') or {}).get('isolate_when', 'n/a')}",
                "Non-gating; does not change compression KPI.",
            ],
        ),
        _render_section(
            "Promotion",
            [
                "p4_gate_candidate: **false** (blended N400 floors fail).",
                "MS lane: **excluded** until commander resumes.",
                "B-track [HYPO] / research_only.",
            ],
        ),
    ]

    doc: dict[str, Any] = {
        "schema": "golden40_expansion_per_lane_report_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "headline_kpi": {
            "source": "golden_core_only",
            "jaccard": gc.get("golden_core_jaccard"),
            "headline_kpi_update": headline_hold,
            "fail_comp_004": "Blended expansion aggregates must not replace headline.",
        },
        "golden_core_baseline_n400": gc,
        "per_lane_n400": lane_rows,
        "cooc_routing_v2": {
            "path": str(args.cooc_json.relative_to(ROOT)).replace("\\", "/") if args.cooc_json.is_file() else None,
            "proceed_to_bench_hook": cooc_proceed,
            "routing_policy_draft": cooc.get("routing_policy_draft"),
        },
        "verdict": {
            "promotion_recommendation": "HOLD",
            "p4_gate_candidate": False,
            "news_readiness": False,
            "would_change_active": False,
        },
        "report_body_markdown": "\n".join(sections_md),
        "pointers": {
            "isolation_summary": str(args.isolation_json.relative_to(ROOT)).replace("\\", "/"),
            "wave4": "reports/rq021_compression_lane_wave4_v1_latest.json",
        },
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {args.out_json} lanes={len(lane_rows)} cooc_proceed={cooc_proceed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
