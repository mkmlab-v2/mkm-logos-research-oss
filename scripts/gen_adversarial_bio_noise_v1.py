#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import datetime, timezone
from pathlib import Path

LABELS = ("TY", "SY", "TE", "SE")
RSIDS = ("rs10937331", "rs12431592", "rs7180547", "rs7193144")
GENO = ("AA", "AG", "GG", "CC", "CT", "TT", "AT", "CG", "GT", "AC")
PROFILES = ("conservative", "neutral", "aggressive")

BASE_RISK_BY_PROFILE = {
    "conservative": {"TY": 0.42, "SY": 0.58, "TE": 0.47, "SE": 0.53},
    "neutral": {"TY": 0.30, "SY": 0.70, "TE": 0.45, "SE": 0.55},
    "aggressive": {"TY": 0.20, "SY": 0.80, "TE": 0.35, "SE": 0.65},
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate adversarial bio-noise proxy cohort/genotype.")
    ap.add_argument("--n-samples", type=int, default=1200)
    ap.add_argument("--seed", type=int, default=20260505)
    ap.add_argument("--noise-level", type=float, default=0.35, help="0..1, larger means more adversarial corruption")
    ap.add_argument("--prior-profile", choices=PROFILES, default="neutral")
    ap.add_argument("--cohort-out-csv", type=Path, default=Path("tmp/bio_adversarial_noise_cohort_v1.csv"))
    ap.add_argument("--genotype-out-csv", type=Path, default=Path("tmp/bio_adversarial_noise_genotype_long_v1.csv"))
    ap.add_argument("--report-out-json", type=Path, default=Path("reports/bio_adversarial_noise_build_v1_latest.json"))
    ns = ap.parse_args()

    rng = random.Random(ns.seed)
    noise = max(0.0, min(1.0, ns.noise_level))

    # base label-risk prior (profile-conditioned)
    base_risk = BASE_RISK_BY_PROFILE[ns.prior_profile]

    cohort_rows = []
    geno_rows = []
    corrupt_count = 0
    for i in range(ns.n_samples):
        sid = f"adv_{i+1:05d}"
        label = rng.choice(LABELS)
        risk = max(0.0, min(1.0, base_risk[label] + rng.uniform(-0.1, 0.1)))
        # adversarial flip: break label-risk consistency
        if rng.random() < noise:
            corrupt_count += 1
            risk = 1.0 - risk
            # occasional label perturbation
            if rng.random() < 0.5:
                label = rng.choice([x for x in LABELS if x != label])

        cohort_rows.append(
            {
                "sample_id": sid,
                "expected_parent": label,
                "risk_score": f"{risk:.6f}",
                "cohort_origin": "adversarial_noise_proxy",
            }
        )

        for rsid in RSIDS:
            g = rng.choice(GENO)
            # additional adversarial genotype corruption
            if rng.random() < noise:
                g = rng.choice(GENO)
            geno_rows.append({"sample_id": sid, "rsid": rsid, "genotype": g})

    ns.cohort_out_csv.parent.mkdir(parents=True, exist_ok=True)
    ns.genotype_out_csv.parent.mkdir(parents=True, exist_ok=True)
    ns.report_out_json.parent.mkdir(parents=True, exist_ok=True)
    with ns.cohort_out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sample_id", "expected_parent", "risk_score", "cohort_origin"])
        w.writeheader()
        w.writerows(cohort_rows)
    with ns.genotype_out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sample_id", "rsid", "genotype"])
        w.writeheader()
        w.writerows(geno_rows)

    rep = {
        "schema": "bio_adversarial_noise_build_v1",
        "generated_at_utc": _utc_now(),
        "summary": {
            "n_samples": ns.n_samples,
            "genotype_rows": len(geno_rows),
            "noise_level": noise,
            "prior_profile": ns.prior_profile,
            "corrupt_rows": corrupt_count,
            "corrupt_ratio": corrupt_count / ns.n_samples if ns.n_samples else 0.0,
        },
        "outputs": {
            "cohort_csv": str(ns.cohort_out_csv.resolve()),
            "genotype_csv": str(ns.genotype_out_csv.resolve()),
        },
    }
    ns.report_out_json.write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.report_out_json.resolve()} corrupt_ratio={rep['summary']['corrupt_ratio']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
