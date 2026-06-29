#!/usr/bin/env python3
"""[HYPO] Ordered chain: upstream λ cert (optional apply) → vault-direct wide/causal/WF/L5/holdout refresh."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CERT_SCRIPT = ROOT / "scripts/apply_rq025_upstream_lambda_certification_v1.py"
FRESHNESS_SCRIPT = ROOT / "scripts/build_rq025_macro_fred_freshness_probe_v1.py"
VAULT_DIRECT_SCRIPT = ROOT / "scripts/build_rq025_vault_macro_direct_wide_join_poc_v1.py"
L5_SCRIPT = ROOT / "scripts/build_rq025_layer5_ensemble_poc_v1.py"
HOLDOUT_SCRIPT = ROOT / "scripts/build_rq025_holdout_2025h2_blind_revalidation_v1.py"
OVERFIT_SCRIPT = ROOT / "scripts/build_rq025_layer5_ensemble_overfit_audit_v1.py"
RECOMPARE_SCRIPT = ROOT / "scripts/build_rq025_holdout_overfit_recompare_v1.py"
CERT_OUT = ROOT / "reports/rq025_upstream_lambda_certification_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/rq025_post_cert_vault_direct_repin_chain_v1_latest.json"
SCHEMA = "rq025_post_cert_vault_direct_repin_chain_v1"
INBOX = ROOT / "reports/inbox/rq025_upstream_sgp_lambda_certified_v1.csv"
PRIOR_PIN = ROOT / "reports/rq025_vault_macro_direct_wide_join_poc_v1_latest.json"


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
    ap.add_argument("--certified-csv", type=Path, default=INBOX)
    ap.add_argument("--apply-vault", action="store_true", help="Replace proxy tail when certified csv present")
    ap.add_argument("--skip-repin", action="store_true", help="Cert gate only; skip wide/causal refresh")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    INBOX.parent.mkdir(parents=True, exist_ok=True)
    prior = _load(PRIOR_PIN)

    cert_cmd = [sys.executable, str(CERT_SCRIPT), "--certified-csv", str(args.certified_csv)]
    if args.apply_vault:
        cert_cmd.append("--apply-vault")
    _run(cert_cmd)
    cert = _load(CERT_OUT)

    repin: dict[str, Any] = {"skipped": True}
    if not args.skip_repin:
        certified_applied = bool((cert.get("apply") or {}).get("applied"))
        proxy_only = not certified_applied
        if FRESHNESS_SCRIPT.is_file():
            _run([sys.executable, str(FRESHNESS_SCRIPT)])
        _run([sys.executable, str(VAULT_DIRECT_SCRIPT)])
        _run([sys.executable, str(L5_SCRIPT)])
        _run([sys.executable, str(HOLDOUT_SCRIPT)])
        _run([sys.executable, str(OVERFIT_SCRIPT)])
        recompare_doc: dict[str, Any] = {}
        if RECOMPARE_SCRIPT.is_file():
            _run([sys.executable, str(RECOMPARE_SCRIPT), "--skip-cert-gate"])
            recompare_doc = _load(ROOT / "reports/rq025_holdout_overfit_recompare_v1_latest.json")
        pin = _load(PRIOR_PIN)
        holdout = _load(ROOT / "reports/rq025_holdout_2025h2_blind_revalidation_v1_latest.json")
        overfit = _load(ROOT / "reports/rq025_layer5_ensemble_overfit_audit_v1_latest.json")
        l5 = _load(ROOT / "reports/rq025_layer5_ensemble_poc_v1_latest.json")
        ens = (holdout.get("full_ensemble") or {})
        repin = {
            "skipped": False,
            "lambda_state": "certified_applied" if certified_applied else "proxy_tail_uncertified",
            "vault_direct_pin": str(PRIOR_PIN.relative_to(ROOT)).replace("\\", "/"),
            "macro_join_rate": pin.get("hybrid_macro_join_rate"),
            "wf_mean_test_accuracy": pin.get("mean_test_accuracy"),
            "wf_delta_minus_majority": pin.get("delta_minus_majority"),
            "l5_mean_test_accuracy": (l5.get("full_ensemble_stack") or {}).get("mean_test_accuracy"),
            "holdout_ensemble_test": ens.get("test_accuracy"),
            "holdout_delta_minus_majority": ens.get("delta_minus_majority"),
            "overfit_suspected": (overfit.get("verdict") or {}).get("overfit_suspected"),
            "p_over_n": overfit.get("p_over_n"),
            "delta_vs_prior_pin": {
                "macro_join_rate": _delta(prior.get("hybrid_macro_join_rate"), pin.get("hybrid_macro_join_rate")),
                "wf_mean_test_accuracy": _delta(prior.get("mean_test_accuracy"), pin.get("mean_test_accuracy")),
            },
            "holdout_overfit_recompare": recompare_doc.get("delta_current_minus_baseline"),
        }

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "rq_id": "RQ-025",
        "certification": cert,
        "repin": repin,
        "verdict": {
            "certified_lambda_applied": bool((cert.get("apply") or {}).get("applied")),
            "repin_completed": not repin.get("skipped"),
            "track_a_promotion": False,
        },
        "human_remainder": (
            None
            if (cert.get("apply") or {}).get("applied")
            else f"Drop certified CSV at {INBOX} then re-run with --apply-vault"
        ),
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
        f"WROTE: {out_path} cert={cert.get('status')} repin={not repin.get('skipped')} "
        f"holdout={repin.get('holdout_ensemble_test')}"
    )
    return 0


def _delta(old: Any, new: Any) -> float | None:
    try:
        if old is None or new is None:
            return None
        return round(float(new) - float(old), 6)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    raise SystemExit(main())
