#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise RuntimeError(r.stderr or r.stdout)


def main() -> int:
    ap = argparse.ArgumentParser(description="One-command final blind evaluation gate (B-track).")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--cohort-csv", type=Path, required=True)
    ap.add_argument("--genotype-csv", type=Path, required=True)
    ap.add_argument("--weights-json", type=Path, default=root / "tmp" / "agct_sasang_axis_weights_active_btrack_v1.json")
    ap.add_argument(
        "--thresholds-json",
        type=Path,
        default=root / "docs" / "final" / "artifacts" / "agct_sasang_btrack_daily_thresholds_v1.json",
    )
    ap.add_argument(
        "--output-json",
        type=Path,
        default=root / "reports" / "agct_final_blind_button_v1_latest.json",
    )
    ns = ap.parse_args()

    eval_script = root / "scripts" / "run_agct_biovalidity_clinical_proxy_eval_v1.py"
    tmp_eval = root / "tmp" / "agct_final_blind_button_eval_tmp.json"
    _run(
        [
            sys.executable,
            str(eval_script),
            "--cohort-csv",
            str(ns.cohort_csv),
            "--genotype-csv",
            str(ns.genotype_csv),
            "--weights-json",
            str(ns.weights_json),
            "--output-json",
            str(tmp_eval),
        ]
    )
    ev = json.loads(tmp_eval.read_text(encoding="utf-8"))["summary"]
    th = json.loads(ns.thresholds_json.read_text(encoding="utf-8"))["thresholds"]

    acc = float(ev["classification_accuracy"])
    risk_corr = float(ev["risk_corr_proxy"] or 0.0)
    checks = {
        "external_accuracy_ok": acc >= float(th["external_accuracy_min"]),
        "external_risk_corr_ok": risk_corr >= float(th["external_risk_corr_min"]),
    }
    decision = "GO_BTRACK" if all(checks.values()) else "REVIEW_REQUIRED"
    payload = {
        "schema": "agct_final_blind_button_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "decision": decision,
        "checks": checks,
        "metrics": {
            "classification_accuracy": acc,
            "classification_macro_f1": float(ev["classification_macro_f1"]),
            "risk_corr_proxy": risk_corr,
            "risk_mae_proxy": float(ev["risk_mae_proxy"] or 0.0),
        },
        "inputs": {
            "cohort_csv": str(ns.cohort_csv.resolve()),
            "genotype_csv": str(ns.genotype_csv.resolve()),
            "weights_json": str(ns.weights_json.resolve()),
            "thresholds_json": str(ns.thresholds_json.resolve()),
        },
        "notes": [
            "One-command final blind gate for independent cohort input.",
            "B-track decision only; no automatic A-track promotion.",
        ],
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} decision={decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
