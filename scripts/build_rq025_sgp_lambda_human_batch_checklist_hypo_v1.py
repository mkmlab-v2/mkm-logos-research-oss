#!/usr/bin/env python3
"""[HYPO] Human-only checklist for Vault sgp lambda batch recompute — no Vault writes."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/rq025_sgp_lambda_human_batch_checklist_hypo_v1_latest.json"
READINESS = ROOT / "reports/rq025_sgp_lambda_recompute_pipeline_readiness_hypo_v1_latest.json"
SCHEMA = "rq025_sgp_lambda_human_batch_checklist_hypo_v1"
VAULT_MACRO = Path(r"G:\공유 드라이브\MKM_DATA_VAULT\data\macro_alerts\sgp_history_master_real.csv")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    readiness = _load(READINESS) if READINESS.is_file() else {}
    steps = [
        {
            "step": 1,
            "actor": "human",
            "action": "Run upstream Vault sgp/lambda batch to extend sgp_history_master_real.csv",
            "blocked_for_agent": True,
            "vault_path": str(VAULT_MACRO),
        },
        {
            "step": 2,
            "actor": "human",
            "action": "Verify Vault max_date >= eval window tail (no carry-forward overlay)",
            "verify_cmd": "py scripts/build_rq025_macro_fred_freshness_probe_v1.py",
        },
        {
            "step": 3,
            "actor": "agent",
            "action": "Re-pin vault-only eval (no --macro-csv-overlay)",
            "verify_cmd": "py scripts/build_rq025_vault_only_eval_pin_hypo_v1.py",
        },
        {
            "step": 4,
            "actor": "agent",
            "action": "Re-run layer-3 Chronos stub on refreshed vault_observed wide join",
            "verify_cmd": "py scripts/build_rq025_chronos_layer3_poc_v1.py",
        },
    ]

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "rq_id": "RQ-025",
        "status": "batch_proxy_applied_awaiting_upstream_certification",
        "readiness_pointer": str(READINESS.relative_to(ROOT)).replace("\\", "/")
        if READINESS.is_file()
        else None,
        "vault_stale": readiness.get("vault_stale_vs_target"),
        "gap_days": readiness.get("gap_days_vault_to_target"),
        "human_steps": steps,
        "agent_may_not": [
            "overwrite G: Vault sgp_history_master_real.csv",
            "claim lambda recompute complete without Vault max_date refresh",
        ],
        "track_wall": {
            "track_a_auto_merge": False,
            "oracle_promotion": False,
            "live_trading": False,
        },
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path} status={payload['status']} vault_stale={payload.get('vault_stale')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
