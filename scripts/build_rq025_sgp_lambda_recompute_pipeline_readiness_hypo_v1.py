#!/usr/bin/env python3
"""[HYPO] Readiness probe for Vault sgp_history lambda recompute — does not mutate Vault."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/rq025_sgp_lambda_recompute_pipeline_readiness_hypo_v1_latest.json"
SCHEMA = "rq025_sgp_lambda_recompute_pipeline_readiness_hypo_v1"
FRESHNESS_SCRIPT = ROOT / "scripts/build_rq025_macro_fred_freshness_probe_v1.py"
MERGED_META = ROOT / "reports/rq025_sgp_history_merged_hypo_v1_latest.json"
VAULT_MACRO = Path("G:/공유 드라이브/MKM_DATA_VAULT/data/macro_alerts/sgp_history_master_real.csv")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    freshness_path = ROOT / "reports/rq025_macro_fred_freshness_probe_v1_latest.json"
    proc = subprocess.run(
        [sys.executable, str(FRESHNESS_SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    freshness = _load(freshness_path) if freshness_path.is_file() else {}
    merged = _load(MERGED_META)

    pointers = [
        "scripts/join_btrack_session_panel_fred_lambda_hypo_v1.py",
        "scripts/build_rq025_sgp_history_merged_hypo_v1.py",
        "scripts/build_macro_fragility_inputs_v1.py",
        "scripts/report_cee_lambda_top5.py",
        "scripts/build_rq025_macro_fred_freshness_probe_v1.py",
    ]
    present = {p: (ROOT / p).is_file() for p in pointers}

    vault_stale = bool(freshness.get("vault_stale_vs_target"))
    auto_recompute_in_repo = False

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "rq_id": "RQ-025",
        "freshness_probe_exit_code": proc.returncode,
        "freshness_pointer": str(freshness_path.relative_to(ROOT)).replace("\\", "/"),
        "vault_macro_csv": str(VAULT_MACRO),
        "vault_present": VAULT_MACRO.is_file(),
        "vault_max_date": (freshness.get("vault_macro") or {}).get("max_date"),
        "vault_stale_vs_target": vault_stale,
        "gap_days_vault_to_target": freshness.get("gap_days_vault_to_target"),
        "fred_api_max_date": (freshness.get("fred_live_probe") or {}).get("fred_max_obs_date"),
        "local_merged_hypo": merged,
        "script_pointers_present": present,
        "auto_recompute_in_repo": auto_recompute_in_repo,
        "readiness": {
            "vault_lambda_batch_recompute": "human_required",
            "local_carry_forward_substitute": "reports/rq025_sgp_history_merged_hypo_v1.csv",
            "blocked_reason": (
                "No repo script appends recomputed lambda rows to G: Vault; "
                "FRED API probe is not sgp_history schema."
                if vault_stale
                else "Vault tail within target window."
            ),
            "recommended_human_chain": [
                "Re-run upstream sgp/lambda batch (off-repo or Vault pipeline) to extend sgp_history_master_real.csv",
                "py scripts/build_rq025_macro_fred_freshness_probe_v1.py",
                "py scripts/build_rq025_flow_fred_wide_join_hypo_v1.py (drop --macro-csv-overlay for observed-only arm)",
            ],
        },
        "track_wall": {
            "track_a_auto_merge": False,
            "oracle_promotion": False,
            "live_trading": False,
        },
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {out_path} vault_stale={vault_stale} "
        f"batch={payload['readiness']['vault_lambda_batch_recompute']}"
    )
    return 0 if proc.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
