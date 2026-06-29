#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aggregate Swarm×Sasang Stage 0 + 4-agent protocol ablation into one closure report.

Read-only over existing artifacts. Does not promote Track A, fusion, oracle, or live.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/btrack_swarm_sasang_stage0_closure_v1_latest.json"
SWARM_EVAL = ROOT / "reports/btrack_swarm_sasang_correlation_v1_latest.json"
ABLATION = ROOT / "reports/sasang_4agent_protocol_ablation_v1_latest.json"
SWARM_REGISTER = ROOT / "docs/final/artifacts/btrack_swarm_sasang_hypothesis_register_v1.json"
ABLATION_REGISTER = ROOT / "docs/final/artifacts/sasang_4agent_protocol_ablation_register_v1.json"
STAGE1_HOLD = ROOT / "reports/btrack_swarm_sasang_stage1_hold_v1_latest.json"
REAL_JSONL = ROOT / "data/btrack/swarm_sentiment_real_pit_v1.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def _run_tier_a_prereqs(min_krx: int) -> dict[str, Any]:
    mod_path = ROOT / "scripts/check_btrack_swarm_tier_a_prereqs_v1.py"
    spec = importlib.util.spec_from_file_location("swarm_tier_a_prereqs", mod_path)
    if spec is None or spec.loader is None:
        return {"error": "cannot_import_prereqs"}
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod.build_report(
        candidates=[p.resolve() for p in mod.DEFAULT_CANDIDATES],
        min_krx_weekdays=min_krx,
    )


def build(*, min_krx_weekdays: int = 30) -> dict[str, Any]:
    swarm = _load(SWARM_EVAL)
    ablation = _load(ABLATION)
    tier_a = _run_tier_a_prereqs(min_krx_weekdays)
    stage1_hold = _load(STAGE1_HOLD)
    real_ingest_meta = _load(REAL_JSONL.with_suffix(".meta.json"))

    swarm_verdict = swarm.get("verdict") if isinstance(swarm.get("verdict"), dict) else {}
    swarm_label = swarm_verdict.get("stage_label") or swarm.get("verdict")
    ablation_verdict = ablation.get("verdict")

    stage0_swarm_null = swarm_label == "null_under_preregistered_gates" or (
        swarm_verdict.get("n_significance_pass_preregistered") == 0
    )
    stage0_ablation_null = ablation_verdict == "null_under_preregistered_gates"

    stage0_complete = bool(swarm) and bool(ablation) and stage0_swarm_null and stage0_ablation_null

    stages = [
        {
            "stage": 0,
            "label": "Swarm×Sasang tier_b + 4-agent synthetic ablation",
            "status": "DONE" if stage0_complete else "PARTIAL",
            "gate": "null_under_preregistered_gates on both axes",
            "fusion_code_add_allowed": False,
        },
        {
            "stage": 1,
            "label": "tier_a real Swarm PIT 30+ KRX weekdays",
            "status": (
                "READY_TO_RERUN"
                if tier_a.get("tier_a_ready")
                else ("PARTIAL_INGEST" if tier_a.get("best_real_pit_rows") else "HOLD")
            ),
            "gate": f"real_pit_rows>={min_krx_weekdays}",
            "action": "py scripts/run_btrack_swarm_sasang_stage1_bundle_v1.py",
            "real_pit_rows": tier_a.get("best_real_pit_rows"),
        },
        {
            "stage": 2,
            "label": "Stage 1 null → permanent fusion barrier",
            "status": "HOLD",
            "gate": "Stage 1 exit 0 + null FDR",
            "action": "CENTRAL one-line barrier; no fusion merge",
        },
    ]

    return {
        "schema": "btrack_swarm_sasang_stage0_closure_v1",
        "generated_at_utc": _utc(),
        "mode": "research_only",
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "send_gate": "HOLD",
        "active_stage": 0 if not tier_a.get("tier_a_ready") else 1,
        "stage0_complete": stage0_complete,
        "usefulness_vs_forecast": "null eval does not block B-track reflection UX; does not promote Track A",
        "evidence": {
            "swarm_sasang_correlation": str(SWARM_EVAL).replace("\\", "/"),
            "sasang_4agent_protocol_ablation": str(ABLATION).replace("\\", "/"),
            "swarm_register": str(SWARM_REGISTER).replace("\\", "/"),
            "ablation_register": str(ABLATION_REGISTER).replace("\\", "/"),
        },
        "swarm_axis": {
            "verdict": swarm_label,
            "n_significance_pass": swarm_verdict.get("n_significance_pass_preregistered"),
            "min_pairs_met": (swarm.get("params") or {}).get("min_pairs"),
            "data_tier": "tier_b_synthetic" if not tier_a.get("tier_a_ready") else "mixed",
        },
        "protocol_ablation_axis": {
            "verdict": ablation_verdict,
            "n_exploratory_pass": ablation.get("n_exploratory_pass"),
            "n_variants": ablation.get("n_variants"),
            "data_mode": (ablation.get("experiment") or {}).get("data_mode"),
        },
        "tier_a_prereqs": tier_a,
        "stage1_ingest": {
            "real_jsonl": str(REAL_JSONL).replace("\\", "/"),
            "meta": real_ingest_meta if real_ingest_meta else None,
            "hold_report": str(STAGE1_HOLD).replace("\\", "/") if stage1_hold else None,
            "hold_status": stage1_hold.get("status") if stage1_hold else None,
        },
        "stages": stages,
        "track_wall": {
            "fusion_pipeline_merge_allowed": False,
            "track_a_promotion": False,
            "oracle_promotion": False,
            "live_trading": False,
            "personadiary_merge": False,
        },
        "repro": {
            "swarm_chain": (
                "py scripts/run_btrack_session_panel_swarm_corr_chain_v1.py "
                "--date-from 2026-04-01 --date-to 2026-06-12 "
                "--swarm-jsonl data/btrack/swarm_sentiment_synthetic_krx_hypo_v1.jsonl "
                "--ohlcv-csv research/market_data/kospi_daily_external_yf.csv --min-pairs 30"
            ),
            "protocol_ablation": "py scripts/run_sasang_4agent_protocol_ablation_v1.py",
            "closure": "py scripts/build_btrack_swarm_sasang_stage0_closure_v1.py",
            "stage1_bundle": "py scripts/run_btrack_swarm_sasang_stage1_bundle_v1.py",
            "atproto_ingest": "py scripts/build_swarm_sentiment_from_atproto_v1.py",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-krx-weekdays", type=int, default=30)
    args = ap.parse_args()

    payload = build(min_krx_weekdays=max(1, args.min_krx_weekdays))
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out_json.resolve()))
    print(f"stage0_complete={payload['stage0_complete']} active_stage={payload['active_stage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
