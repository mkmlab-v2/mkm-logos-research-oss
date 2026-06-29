#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge envelope backtest + frozen MKM kospi KPI [HYPO][research_only]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_envelope_smct_hypo_lib_v1 import kospi_metrics_from_frozen_score  # noqa: E402

DEFAULT_ENVELOPE = ROOT / "reports/btrack_envelope_ma60_6_kospi_backtest_hypo_v1_latest.json"
DEFAULT_SCORE = ROOT / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_envelope_vs_prophecy_dual_report_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _delta_pp(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return round((a - b) * 100.0, 3)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--envelope-json", type=Path, default=DEFAULT_ENVELOPE)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.envelope_json.is_file():
        print(f"missing envelope json: {args.envelope_json}", file=sys.stderr)
        return 1
    if not args.score_json.is_file():
        print(f"missing score json: {args.score_json}", file=sys.stderr)
        return 1

    env_doc = json.loads(args.envelope_json.read_text(encoding="utf-8"))
    mkm_raw = kospi_metrics_from_frozen_score(args.score_json)

    comparison_rows: list[dict] = []
    scope_map = (
        ("full_180d", "full_window"),
        ("smct_subset_legacy_light_medium", "smct_subset_legacy_light_medium"),
        ("envelope_trend_gate_v1", "envelope_trend_gate_v1"),
    )
    for arm_id, arm in (env_doc.get("arms") or {}).items():
        for scope_label, block_key in scope_map:
            block = arm.get(block_key) or arm.get("smct_subset") if block_key == "smct_subset_legacy_light_medium" else arm.get(block_key) or {}
            if block_key == "smct_subset_legacy_light_medium" and not arm.get(block_key):
                block = arm.get("smct_subset") or {}
            env_hit = block.get("directional_hit_rate_raw")
            comparison_rows.append(
                {
                    "arm_id": arm_id,
                    "scope": scope_label,
                    "envelope": {
                        "raw": {
                            "directional_hit_rate": env_hit,
                            "n_entry_signals": block.get("n_entry_signals"),
                            "n_directional_next_day": block.get("n_directional_next_day"),
                            "signal_coverage": block.get("signal_coverage"),
                            "n_signals_gated_out_by_subset": block.get("n_signals_gated_out_by_subset"),
                        },
                        "repair_v2": None,
                    },
                    "mkm_kospi_frozen": {
                        "raw": {
                            "directional_hit_rate": mkm_raw.get("directional_hit_rate_raw"),
                            "n_evaluated": mkm_raw.get("n_evaluated"),
                        },
                        "repair_v2": None,
                    },
                    "delta": {
                        "directional_hit_rate_pp_envelope_minus_mkm": _delta_pp(env_hit, mkm_raw.get("directional_hit_rate_raw")),
                    },
                    "note": "KPI definitions differ: envelope=next-day bull after entry; MKM=per-date direction match",
                }
            )

    out = {
        "schema": "btrack_envelope_vs_prophecy_dual_report_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "combined_all_passed": False,
        "track_a_auto_promote": False,
        "required_output_block_raw_repair": {
            "raw": "directional_hit_rate + row counts (envelope entry-next-day vs MKM per-date)",
            "repair_v2": "not_applicable_envelope_path",
            "delta": "envelope_minus_mkm_pp where comparable headline only",
        },
        "eval_window": env_doc.get("eval_window"),
        "mkm_frozen_kospi_leg": mkm_raw,
        "envelope_arms_vs_mkm": comparison_rows,
        "verdict_ko": "research_only — 우열 단정 금지; signal 정의·표본수 상이. oper score SSOT 미갱신.",
        "disallowed_claims": [
            "envelope beats MKM on returns or oper promotion",
            "repair_v2 uplift as Track A proof",
            "SMCT subset alone clears combined gate",
        ],
        "sources": {
            "envelope_backtest": str(args.envelope_json.relative_to(ROOT)),
            "oper_score_ssot_read_only": str(args.score_json.relative_to(ROOT)),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK rows={len(comparison_rows)} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
