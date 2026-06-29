#!/usr/bin/env python3
"""[HYPO] Restore G: Vault sgp_history to proxy-tail snapshot → repin → 3-arm → train-only."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VAULT = Path("G:/공유 드라이브/MKM_DATA_VAULT/data/macro_alerts/sgp_history_master_real.csv")
PROXY_SNAPSHOT = ROOT / "reports/backups/sgp_history_master_real_pre_cert_20260611T074914Z.csv"
POST_CERT = ROOT / "scripts/build_rq025_post_cert_vault_direct_repin_chain_v1.py"
THREE_ARM = ROOT / "scripts/build_rq025_lambda_source_three_arm_compare_v1.py"
TRAIN_CHAIN = ROOT / "scripts/build_rq025_train_only_causal_holdout_chain_poc_v1.py"
DEFAULT_OUT = ROOT / "reports/rq025_restore_proxy_lambda_vault_v1_latest.json"
SCHEMA = "rq025_restore_proxy_lambda_vault_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise SystemExit(f"failed: {' '.join(cmd)}\n{proc.stderr}\n{proc.stdout}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--proxy-snapshot", type=Path, default=PROXY_SNAPSHOT)
    ap.add_argument("--vault-csv", type=Path, default=VAULT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-three-arm", action="store_true")
    ap.add_argument("--upstream-csv", type=Path, default=None)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    snap = args.proxy_snapshot if args.proxy_snapshot.is_absolute() else ROOT / args.proxy_snapshot
    vault = args.vault_csv
    if not snap.is_file():
        raise SystemExit(f"missing proxy snapshot: {snap}")
    if not vault.is_file() and not args.dry_run:
        raise SystemExit(f"missing vault csv: {vault}")

    backup_path: str | None = None
    restored = False
    if not args.dry_run:
        backup_dir = ROOT / "reports/backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = backup_dir / f"sgp_history_master_real_pre_proxy_restore_{stamp}.csv"
        shutil.copy2(vault, backup)
        backup_path = str(backup.relative_to(ROOT)).replace("\\", "/")
        shutil.copy2(snap, vault)
        restored = True

    _run([sys.executable, str(POST_CERT)])

    three_arm_doc: dict[str, Any] = {}
    if not args.skip_three_arm:
        three_cmd = [sys.executable, str(THREE_ARM)]
        upstream = args.upstream_csv
        if upstream:
            three_cmd.extend(["--upstream-csv", str(upstream)])
        elif os.environ.get("RQ025_UPSTREAM_LAMBDA_CERTIFIED_CSV"):
            three_cmd.extend(["--upstream-csv", os.environ["RQ025_UPSTREAM_LAMBDA_CERTIFIED_CSV"]])
        _run(three_cmd)
        three_arm_doc = _load(ROOT / "reports/rq025_lambda_source_three_arm_compare_v1_latest.json")

    _run([sys.executable, str(TRAIN_CHAIN), "--skip-cert-gate"])
    train_doc = _load(ROOT / "reports/rq025_train_only_causal_holdout_chain_poc_v1_latest.json")
    post_doc = _load(ROOT / "reports/rq025_post_cert_vault_direct_repin_chain_v1_latest.json")
    repin = post_doc.get("repin") or {}

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "rq_id": "RQ-025",
        "restore": {
            "dry_run": args.dry_run,
            "applied": restored,
            "proxy_snapshot": str(snap.relative_to(ROOT)).replace("\\", "/")
            if snap.is_relative_to(ROOT)
            else str(snap),
            "vault_csv": str(vault),
            "backup_before_restore": backup_path,
            "lambda_state": "proxy_kospi_calibrated_tail",
            "upstream_production_batch": False,
        },
        "repin_holdout_ensemble_test": repin.get("holdout_ensemble_test"),
        "repin_wf_mean_test_accuracy": repin.get("wf_mean_test_accuracy"),
        "three_arm": three_arm_doc if three_arm_doc else {"skipped": args.skip_three_arm},
        "train_only": {
            "full_test": (train_doc.get("holdout_full_sample_causal") or {}).get("ensemble_test_accuracy"),
            "train_only_test": (train_doc.get("holdout_train_only_causal") or {}).get("ensemble_test_accuracy"),
            "delta": train_doc.get("delta_train_only_minus_full_test"),
        },
        "verdict": {
            "proxy_restored": restored,
            "track_a_promotion": False,
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
        f"WROTE: {out_path} restored={restored} holdout={repin.get('holdout_ensemble_test')} "
        f"best_arm={((three_arm_doc.get('verdict') or {}).get('best_arm_by_holdout'))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
