#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
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


def _safe_float(v: object, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _sample_overlap_stats(cohort_csv: Path, genotype_csv: Path) -> dict[str, int]:
    cohort_ids: set[str] = set()
    genotype_ids: set[str] = set()
    if cohort_csv.is_file():
        with cohort_csv.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                sid = str(row.get("sample_id") or "").strip()
                if sid:
                    cohort_ids.add(sid)
    if genotype_csv.is_file():
        with genotype_csv.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                sid = str(row.get("sample_id") or "").strip()
                if sid:
                    genotype_ids.add(sid)
    overlap_n = len(cohort_ids & genotype_ids)
    return {
        "cohort_sample_n": len(cohort_ids),
        "genotype_sample_n": len(genotype_ids),
        "overlap_sample_n": overlap_n,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Adversarial robustness sweep for AGCT-Sasang engine.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--weights-json", type=Path, default=root / "tmp" / "agct_sasang_axis_weights_active_btrack_v1.json")
    ap.add_argument("--n-samples", type=int, default=1200)
    ap.add_argument("--seed", type=int, default=20260505)
    ap.add_argument("--prior-profile", choices=("conservative", "neutral", "aggressive"), default="neutral")
    ap.add_argument(
        "--noise-grid",
        type=str,
        default="0.1,0.2,0.35,0.5,0.7",
        help="Comma-separated noise levels.",
    )
    ap.add_argument("--output-json", type=Path, default=root / "reports" / "agct_adversarial_robustness_sweep_v1_latest.json")
    ns = ap.parse_args()

    gen_script = root / "scripts" / "gen_adversarial_bio_noise_v1.py"
    eval_script = root / "scripts" / "run_agct_biovalidity_clinical_proxy_eval_v1.py"
    noise_levels = [float(x.strip()) for x in ns.noise_grid.split(",") if x.strip()]

    rows = []
    failed_levels = 0
    for i, nl in enumerate(noise_levels):
        tag = f"{ns.prior_profile}_nl{str(nl).replace('.','_')}"
        cohort = root / "tmp" / f"bio_adversarial_noise_cohort_{tag}.csv"
        geno = root / "tmp" / f"bio_adversarial_noise_geno_{tag}.csv"
        build_report = root / "reports" / f"bio_adversarial_noise_build_{tag}.json"
        eval_report = root / "reports" / f"agct_adversarial_eval_{tag}.json"

        _run(
            [
                sys.executable,
                str(gen_script),
                "--n-samples",
                str(ns.n_samples),
                "--seed",
                str(ns.seed + i),
                "--noise-level",
                str(nl),
                "--prior-profile",
                ns.prior_profile,
                "--cohort-out-csv",
                str(cohort),
                "--genotype-out-csv",
                str(geno),
                "--report-out-json",
                str(build_report),
            ]
        )
        overlap = _sample_overlap_stats(cohort, geno)
        try:
            _run(
                [
                    sys.executable,
                    str(eval_script),
                    "--cohort-csv",
                    str(cohort),
                    "--genotype-csv",
                    str(geno),
                    "--weights-json",
                    str(ns.weights_json),
                    "--output-json",
                    str(eval_report),
                ]
            )
            s = json.loads(eval_report.read_text(encoding="utf-8"))["summary"]
            rows.append(
                {
                    "noise_level": nl,
                    "ok": True,
                    "accuracy": _safe_float(s.get("classification_accuracy")),
                    "macro_f1": _safe_float(s.get("classification_macro_f1")),
                    "risk_corr": _safe_float(s.get("risk_corr_proxy")),
                    "risk_mae": _safe_float(s.get("risk_mae_proxy")),
                    "sample_overlap": overlap,
                    "eval_report": str(eval_report.resolve()),
                }
            )
        except Exception as e:  # noqa: BLE001
            failed_levels += 1
            rows.append(
                {
                    "noise_level": nl,
                    "ok": False,
                    "error": str(e),
                    "accuracy": None,
                    "macro_f1": None,
                    "risk_corr": None,
                    "risk_mae": None,
                    "sample_overlap": overlap,
                    "eval_report": str(eval_report.resolve()),
                }
            )

    # Simple robustness index: area-like mean of normalized scores over noise grid
    valid_rows = [r for r in rows if r.get("ok")]
    robust_score = (
        sum((_safe_float(r.get("accuracy")) + max(0.0, _safe_float(r.get("risk_corr")))) / 2.0 for r in valid_rows)
        / len(valid_rows)
        if valid_rows
        else 0.0
    )
    payload = {
        "schema": "agct_adversarial_robustness_sweep_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "inputs": {
            "weights_json": str(ns.weights_json.resolve()),
            "n_samples": ns.n_samples,
            "prior_profile": ns.prior_profile,
            "noise_levels": noise_levels,
        },
        "summary": {
            "robustness_score": robust_score,
            "n_levels": len(rows),
            "n_valid_levels": len(valid_rows),
            "n_failed_levels": failed_levels,
            "worst_case_risk_corr": min(_safe_float(r.get("risk_corr")) for r in valid_rows) if valid_rows else None,
            "worst_case_accuracy": min(_safe_float(r.get("accuracy")) for r in valid_rows) if valid_rows else None,
        },
        "levels": rows,
        "notes": [
            "Adversarial sweep is stress-test only (B-track).",
            "Use independent real cohort blind tests for real-world claims.",
        ],
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} robustness_score={robust_score:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
