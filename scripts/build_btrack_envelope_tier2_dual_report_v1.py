#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tier-2 equity envelope pooled vs MKM kospi frozen (narrative) [HYPO]."""
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

DEFAULT_EQUITY = ROOT / "reports/btrack_envelope_equity_basket_backtest_hypo_v1_latest.json"
DEFAULT_SCORE = ROOT / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_envelope_tier2_dual_report_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _delta_pp(a, b):
    if a is None or b is None:
        return None
    return round((float(a) - float(b)) * 100.0, 3)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--equity-json", type=Path, default=DEFAULT_EQUITY)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.equity_json.is_file():
        print(f"missing equity json: {args.equity_json}", file=sys.stderr)
        return 1

    eq = json.loads(args.equity_json.read_text(encoding="utf-8"))
    mkm = kospi_metrics_from_frozen_score(args.score_json)

    rows = []
    scope_map = (
        ("pooled_full", "full_window"),
        ("pooled_smct_subset_legacy", "smct_subset_legacy_light_medium"),
        ("pooled_envelope_trend_gate_v1", "envelope_trend_gate_v1"),
    )
    for arm_id, arm in (eq.get("arms") or {}).items():
        for scope_label, block_key in scope_map:
            block = arm.get(block_key) or {}
            if block_key == "smct_subset_legacy_light_medium" and not block:
                block = arm.get("smct_subset") or {}
            pooled = block.get("pooled") if isinstance(block, dict) and "pooled" in block else block
            env_hit = pooled.get("directional_hit_rate_raw")
            rows.append(
                {
                    "arm_id": arm_id,
                    "scope": scope_label,
                    "envelope_pooled": {
                        "raw": {
                            "directional_hit_rate": env_hit,
                            "n_entry_signals": pooled.get("n_entry_signals"),
                            "n_directional_next_day": pooled.get("n_directional_next_day"),
                            "n_symbols": pooled.get("n_symbols"),
                            "n_signals_gated_out_by_subset": pooled.get("n_signals_gated_out_by_subset"),
                        },
                        "repair_v2": None,
                    },
                    "mkm_kospi_frozen_reference": {
                        "raw": {"directional_hit_rate": mkm.get("directional_hit_rate_raw"), "n_evaluated": mkm.get("n_evaluated")},
                        "repair_v2": None,
                    },
                    "delta_pp_envelope_minus_mkm": _delta_pp(env_hit, mkm.get("directional_hit_rate_raw")),
                    "note": "weak fairness — universe mismatch; no oper promotion",
                }
            )

    out = {
        "schema": "btrack_envelope_tier2_dual_report_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "combined_all_passed": False,
        "required_output_block_raw_repair": {
            "raw": "envelope pooled entry-next-day vs MKM kospi per-date (reference only)",
            "repair_v2": None,
            "delta": "pp where headline shown",
        },
        "mkm_frozen_kospi_leg": mkm,
        "envelope_equity_pooled_vs_mkm": rows,
        "verdict_ko": "Tier-2 narrative only; MKM kospi leg is index prophecy — not stock picker.",
        "sources": {
            "equity_backtest": str(args.equity_json.relative_to(ROOT)),
            "oper_score_ssot_read_only": str(args.score_json.relative_to(ROOT)),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK rows={len(rows)} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
