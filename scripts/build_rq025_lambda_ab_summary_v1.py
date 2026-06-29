#!/usr/bin/env python3
"""[HYPO] Freeze Oracle RQ-025 lambda 3-arm A/B table for internal meeting SSOT."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
THREE_ARM = ROOT / "reports/rq025_lambda_source_three_arm_compare_v1_latest.json"
AUTO = ROOT / "reports/rq025_upstream_csv_auto_resolve_v1_latest.json"
DISCOVERY = ROOT / "reports/rq025_upstream_csv_discovery_v1_latest.json"
DEFAULT_OUT_JSON = ROOT / "reports/rq025_lambda_ab_summary_v1_latest.json"
DEFAULT_OUT_MD = ROOT / "reports/rq025_lambda_ab_summary_v1_latest.md"
SCHEMA = "rq025_lambda_ab_summary_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _pct(x: Any) -> str:
    try:
        return f"{float(x) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _pp(x: Any) -> str:
    try:
        return f"{float(x) * 100:+.1f}pp"
    except (TypeError, ValueError):
        return "—"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--three-arm-json", type=Path, default=THREE_ARM)
    ap.add_argument("--auto-json", type=Path, default=AUTO)
    ap.add_argument("--discovery-json", type=Path, default=DISCOVERY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--output-md", type=Path, default=DEFAULT_OUT_MD)
    args = ap.parse_args(argv)

    three = _load(args.three_arm_json if args.three_arm_json.is_absolute() else ROOT / args.three_arm_json)
    if not three:
        raise SystemExit(f"missing three-arm json: {args.three_arm_json}")
    auto = _load(args.auto_json if args.auto_json.is_absolute() else ROOT / args.auto_json)
    discovery = _load(args.discovery_json if args.discovery_json.is_absolute() else ROOT / args.discovery_json)

    arms_out: list[dict[str, Any]] = []
    for a in three.get("arms") or []:
        if not isinstance(a, dict):
            continue
        arms_out.append(
            {
                "arm_id": a.get("arm_id"),
                "label": a.get("label"),
                "holdout_l5": a.get("holdout_ensemble_test"),
                "holdout_l5_pct": _pct(a.get("holdout_ensemble_test")),
                "vs_majority_pp": a.get("holdout_delta_minus_majority"),
                "vs_majority_pp_fmt": _pp(a.get("holdout_delta_minus_majority")),
                "upstream_production_batch": a.get("upstream_production_batch"),
                "status": a.get("status"),
            }
        )

    pairwise = three.get("pairwise_delta_holdout_ensemble_test") or {}
    resolved = auto.get("resolved") or {}

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "rq_id": "RQ-025",
        "frozen_at_utc": three.get("generated_at_utc"),
        "arms": arms_out,
        "pairwise_holdout_delta": {
            "merged_minus_proxy_pp": pairwise.get("merged_minus_proxy"),
            "upstream_minus_proxy_pp": pairwise.get("upstream_minus_proxy"),
            "upstream_minus_merged_pp": pairwise.get("upstream_minus_merged"),
        },
        "verdict": three.get("verdict") or {},
        "upstream_resolve": {
            "source_kind": resolved.get("source_kind"),
            "upstream_production_batch": resolved.get("upstream_production_batch"),
            "boundary_ack": auto.get("boundary_ack"),
        },
        "discovery": {
            "n_candidates": (discovery.get("verdict") or {}).get("n_candidates"),
            "n_production_meta": (discovery.get("verdict") or {}).get("n_production_meta"),
            "n_schema_ok": (discovery.get("verdict") or {}).get("n_schema_ok"),
            "n_schema_fail": (discovery.get("verdict") or {}).get("n_schema_fail"),
            "schema_validated": (discovery.get("verdict") or {}).get("schema_validated"),
            "recommended_next": (discovery.get("verdict") or {}).get("recommended_next"),
        },
        "sources": {
            "three_arm": str(args.three_arm_json),
            "auto": str(args.auto_json) if auto else None,
            "discovery": str(args.discovery_json) if discovery else None,
        },
        "track_wall": {
            "track_a_auto_merge": False,
            "oracle_promotion": False,
            "live_trading": False,
        },
    }

    lines = [
        "# Oracle RQ-025 — λ source A/B summary (internal · frozen)",
        "",
        f"_Generated: {_utc_now()} · `[HYPO]` · `research_only` · SEND **HOLD**_",
        "",
        "| arm | holdout L5 | vs majority | production batch |",
        "|-----|------------|-------------|------------------|",
    ]
    for a in arms_out:
        lines.append(
            f"| **{a.get('arm_id')}** | {a.get('holdout_l5_pct')} | {a.get('vs_majority_pp_fmt')} | {a.get('upstream_production_batch')} |"
        )
    lines.extend(
        [
            "",
            f"- best arm: **{(three.get('verdict') or {}).get('best_arm_by_holdout')}**",
            f"- upstream − proxy: **{_pp(pairwise.get('upstream_minus_proxy'))}**",
            f"- resolve source: `{resolved.get('source_kind', '—')}` · production meta: **{resolved.get('upstream_production_batch', False)}**",
            f"- discovery: **{(discovery.get('verdict') or {}).get('n_candidates', '—')}** candidates · production meta **{(discovery.get('verdict') or {}).get('n_production_meta', '—')}** · schema ok **{(discovery.get('verdict') or {}).get('n_schema_ok', '—')}**",
            "",
            "Track A · live · MS headline: **HOLD** — not promotion evidence.",
            "",
        ]
    )

    out_json = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_md = args.output_md if args.output_md.is_absolute() else ROOT / args.output_md
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"WROTE: {out_json} WROTE: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
