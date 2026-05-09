#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import datetime, timezone
from pathlib import Path

LABELS = ("TY", "SY", "TE", "SE")

PRIORS_AGGRESSIVE = {
    "TY": {
        "rs10937331": [("AA", 0.56), ("AG", 0.28), ("GG", 0.16)],
        "rs12431592": [("CC", 0.33), ("CT", 0.43), ("TT", 0.24)],
        "rs7180547": [("CC", 0.24), ("CT", 0.41), ("TT", 0.35)],
        "rs7193144": [("AA", 0.23), ("AT", 0.47), ("TT", 0.30)],
    },
    "SY": {
        "rs10937331": [("AA", 0.22), ("AG", 0.41), ("GG", 0.37)],
        "rs12431592": [("CC", 0.62), ("CT", 0.26), ("TT", 0.12)],
        "rs7180547": [("CC", 0.28), ("CT", 0.46), ("TT", 0.26)],
        "rs7193144": [("AA", 0.37), ("AT", 0.40), ("TT", 0.23)],
    },
    "TE": {
        "rs10937331": [("AA", 0.16), ("AG", 0.33), ("GG", 0.51)],
        "rs12431592": [("CC", 0.29), ("CT", 0.41), ("TT", 0.30)],
        "rs7180547": [("CC", 0.26), ("CT", 0.41), ("TT", 0.33)],
        "rs7193144": [("AA", 0.44), ("AT", 0.33), ("TT", 0.23)],
    },
    "SE": {
        "rs10937331": [("AA", 0.28), ("AG", 0.46), ("GG", 0.26)],
        "rs12431592": [("CC", 0.24), ("CT", 0.47), ("TT", 0.29)],
        "rs7180547": [("CC", 0.66), ("CT", 0.24), ("TT", 0.10)],
        "rs7193144": [("AA", 0.12), ("AT", 0.34), ("TT", 0.54)],
    },
}

PRIORS_CONSERVATIVE = {
    "TY": {
        "rs10937331": [("AA", 0.44), ("AG", 0.33), ("GG", 0.23)],
        "rs12431592": [("CC", 0.36), ("CT", 0.38), ("TT", 0.26)],
        "rs7180547": [("CC", 0.28), ("CT", 0.39), ("TT", 0.33)],
        "rs7193144": [("AA", 0.27), ("AT", 0.41), ("TT", 0.32)],
    },
    "SY": {
        "rs10937331": [("AA", 0.27), ("AG", 0.39), ("GG", 0.34)],
        "rs12431592": [("CC", 0.48), ("CT", 0.33), ("TT", 0.19)],
        "rs7180547": [("CC", 0.32), ("CT", 0.42), ("TT", 0.26)],
        "rs7193144": [("AA", 0.35), ("AT", 0.38), ("TT", 0.27)],
    },
    "TE": {
        "rs10937331": [("AA", 0.23), ("AG", 0.35), ("GG", 0.42)],
        "rs12431592": [("CC", 0.32), ("CT", 0.38), ("TT", 0.30)],
        "rs7180547": [("CC", 0.30), ("CT", 0.38), ("TT", 0.32)],
        "rs7193144": [("AA", 0.38), ("AT", 0.36), ("TT", 0.26)],
    },
    "SE": {
        "rs10937331": [("AA", 0.31), ("AG", 0.42), ("GG", 0.27)],
        "rs12431592": [("CC", 0.27), ("CT", 0.43), ("TT", 0.30)],
        "rs7180547": [("CC", 0.50), ("CT", 0.33), ("TT", 0.17)],
        "rs7193144": [("AA", 0.20), ("AT", 0.35), ("TT", 0.45)],
    },
}

PRIORS_NEUTRAL = {
    "TY": {
        "rs10937331": [("AA", 0.50), ("AG", 0.30), ("GG", 0.20)],
        "rs12431592": [("CC", 0.35), ("CT", 0.40), ("TT", 0.25)],
        "rs7180547": [("CC", 0.25), ("CT", 0.40), ("TT", 0.35)],
        "rs7193144": [("AA", 0.25), ("AT", 0.45), ("TT", 0.30)],
    },
    "SY": {
        "rs10937331": [("AA", 0.25), ("AG", 0.40), ("GG", 0.35)],
        "rs12431592": [("CC", 0.55), ("CT", 0.30), ("TT", 0.15)],
        "rs7180547": [("CC", 0.30), ("CT", 0.45), ("TT", 0.25)],
        "rs7193144": [("AA", 0.35), ("AT", 0.40), ("TT", 0.25)],
    },
    "TE": {
        "rs10937331": [("AA", 0.20), ("AG", 0.35), ("GG", 0.45)],
        "rs12431592": [("CC", 0.30), ("CT", 0.40), ("TT", 0.30)],
        "rs7180547": [("CC", 0.28), ("CT", 0.40), ("TT", 0.32)],
        "rs7193144": [("AA", 0.40), ("AT", 0.35), ("TT", 0.25)],
    },
    "SE": {
        "rs10937331": [("AA", 0.30), ("AG", 0.45), ("GG", 0.25)],
        "rs12431592": [("CC", 0.25), ("CT", 0.45), ("TT", 0.30)],
        "rs7180547": [("CC", 0.58), ("CT", 0.30), ("TT", 0.12)],
        "rs7193144": [("AA", 0.15), ("AT", 0.35), ("TT", 0.50)],
    },
}

PRIOR_PROFILES = {
    "conservative": PRIORS_CONSERVATIVE,
    "neutral": PRIORS_NEUTRAL,
    "aggressive": PRIORS_AGGRESSIVE,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _choice_weighted(rng: random.Random, items: list[tuple[str, float]]) -> str:
    x = rng.random()
    acc = 0.0
    for g, p in items:
        acc += p
        if x <= acc:
            return g
    return items[-1][0]


def main() -> int:
    ap = argparse.ArgumentParser(description="Build proxy real-collection cohort from required_rsids queue.")
    ap.add_argument("--batch-csv", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=20260505)
    ap.add_argument("--prior-profile", choices=("conservative", "neutral", "aggressive"), default="aggressive")
    ap.add_argument("--max-samples", type=int, default=0, help="Optional cap; 0 means all rows.")
    ap.add_argument("--replicate-factor", type=int, default=1, help="Replicate each source sample N times with suffixed sample_id.")
    ap.add_argument(
        "--default-required-rsids",
        type=str,
        default="rs10937331|rs12431592|rs7180547|rs7193144",
        help="Fallback rsids when input has no required_rsids column/value.",
    )
    ap.add_argument("--cohort-out-csv", type=Path, default=Path("tmp/bio_real_collection_proxy_cohort_v1.csv"))
    ap.add_argument("--genotype-out-csv", type=Path, default=Path("tmp/bio_real_collection_proxy_genotype_long_v1.csv"))
    ap.add_argument("--report-out-json", type=Path, default=Path("reports/bio_real_collection_proxy_build_v1_latest.json"))
    ns = ap.parse_args()

    rng = random.Random(ns.seed)
    with ns.batch_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    default_rsids = [x.strip() for x in str(ns.default_required_rsids).split("|") if x.strip().startswith("rs")]
    priors = PRIOR_PROFILES[str(ns.prior_profile)]
    cohort_rows = []
    geno_rows = []
    label_counts = {k: 0 for k in LABELS}
    risk_map = {"TY": 0.30, "SY": 0.70, "TE": 0.45, "SE": 0.55}
    total_geno_rows = 0
    replicate_factor = max(1, int(ns.replicate_factor))
    consumed = 0
    for row in rows:
        if ns.max_samples and consumed >= int(ns.max_samples):
            break
        sid = str(row.get("sample_id") or "").strip()
        req = str(row.get("required_rsids") or "").strip()
        if not sid:
            continue
        rsids = [x.strip() for x in req.split("|") if x.strip().startswith("rs")] if req else []
        if not rsids:
            rsids = list(default_rsids)
        if not rsids:
            continue
        for rep in range(replicate_factor):
            sid_rep = sid if replicate_factor == 1 else f"{sid}__rep{rep+1:02d}"
            label = rng.choice(LABELS)
            label_counts[label] += 1
            risk = max(0.0, min(1.0, risk_map[label] + rng.uniform(-0.08, 0.08)))
            cohort_rows.append(
                {
                    "sample_id": sid_rep,
                    "expected_parent": label,
                    "risk_score": f"{risk:.6f}",
                    "cohort_origin": "real_collection_proxy",
                    "source_required_rsids": "|".join(rsids),
                }
            )
            for rsid in rsids:
                prior = priors.get(label, {}).get(rsid)
                if prior is None:
                    prior = [("AA", 0.34), ("AG", 0.33), ("GG", 0.33)]
                geno = _choice_weighted(rng, prior)
                geno_rows.append({"sample_id": sid_rep, "rsid": rsid, "genotype": geno})
                total_geno_rows += 1
        consumed += 1

    ns.cohort_out_csv.parent.mkdir(parents=True, exist_ok=True)
    ns.genotype_out_csv.parent.mkdir(parents=True, exist_ok=True)
    ns.report_out_json.parent.mkdir(parents=True, exist_ok=True)
    with ns.cohort_out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["sample_id", "expected_parent", "risk_score", "cohort_origin", "source_required_rsids"],
        )
        w.writeheader()
        w.writerows(cohort_rows)
    with ns.genotype_out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sample_id", "rsid", "genotype"])
        w.writeheader()
        w.writerows(geno_rows)

    report = {
        "schema": "bio_real_collection_proxy_build_v1",
        "generated_at_utc": _utc_now(),
        "inputs": {"batch_csv": str(ns.batch_csv.resolve()), "seed": ns.seed},
        "outputs": {
            "cohort_csv": str(ns.cohort_out_csv.resolve()),
            "genotype_csv": str(ns.genotype_out_csv.resolve()),
        },
        "summary": {
            "cohort_rows": len(cohort_rows),
            "genotype_rows": total_geno_rows,
            "label_distribution": label_counts,
        },
        "note": f"Proxy cohort synthesized from real collection queue + {ns.prior_profile} literature priors (B-track only).",
    }
    ns.report_out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {ns.cohort_out_csv.resolve()} rows={len(cohort_rows)}; "
        f"{ns.genotype_out_csv.resolve()} rows={total_geno_rows}"
    )
    print(f"WROTE: {ns.report_out_json.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
