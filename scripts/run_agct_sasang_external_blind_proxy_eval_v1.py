#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.9, L:0.86, K:0.67, M:0.46}
# Balance: 89
# Purpose: Build literature-prior proxy external cohort and run blind evaluation for active AGCT-Sasang profile.
# Keywords: agct, sasang, external, blind, proxy, literature, btrack

from __future__ import annotations

import argparse
import csv
import json
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

LABELS = ("TY", "SY", "TE", "SE")
RSIDS = ("rs10937331", "rs12431592", "rs7180547", "rs7193144")
GENOTYPES = ("AA", "AC", "AG", "AT", "CC", "CG", "CT", "GG", "GT", "TT")

# Literature-proxy priors (illustrative B-track priors, not clinical truth)
PRIORS_NEUTRAL: dict[str, dict[str, list[tuple[str, float]]]] = {
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
        "rs7193144": [("AA", 0.15), ("AT", 0.35), ("TT", 0.50)],  # inverse obesity-risk proxy
    },
}

PRIORS_CONSERVATIVE: dict[str, dict[str, list[tuple[str, float]]]] = {
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

PRIORS_AGGRESSIVE: dict[str, dict[str, list[tuple[str, float]]]] = {
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

PRIOR_PROFILES = {
    "neutral": PRIORS_NEUTRAL,
    "conservative": PRIORS_CONSERVATIVE,
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


def _safe_corr(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    dx = sum((a - mx) ** 2 for a in xs)
    dy = sum((b - my) ** 2 for b in ys)
    den = (dx * dy) ** 0.5
    if den <= 0:
        return None
    return num / den


def _normalize(v: dict[str, float]) -> dict[str, float]:
    s = sum(v.values())
    if s <= 0:
        return {k: 0.0 for k in v}
    return {k: (x / s) for k, x in v.items()}


def main() -> int:
    ap = argparse.ArgumentParser(description="External blind proxy eval from literature priors (B-track).")
    ap.add_argument("--n-samples", type=int, default=800)
    ap.add_argument("--seed", type=int, default=20260505)
    ap.add_argument("--prior-profile", choices=("neutral", "conservative", "aggressive"), default="neutral")
    ap.add_argument("--sample-prefix", type=str, default="ext_blind")
    ap.add_argument("--active-weights-json", type=Path, required=True)
    ap.add_argument("--projection-script", type=Path, default=Path("scripts/run_agct_sasang_composition_projection_v1.py"))
    ap.add_argument("--work-dir", type=Path, default=Path("tmp/agct_external_blind_proxy_v1"))
    ap.add_argument("--output-json", type=Path, default=Path("reports/agct_sasang_external_blind_proxy_eval_v1_latest.json"))
    ns = ap.parse_args()

    rng = random.Random(ns.seed)
    ns.work_dir.mkdir(parents=True, exist_ok=True)
    cohort_csv = ns.work_dir / "external_blind_cohort.csv"
    geno_csv = ns.work_dir / "external_blind_genotype_long.csv"
    projection_json = ns.work_dir / "external_blind_projection.json"

    cohort_rows: list[dict[str, str]] = []
    geno_rows: list[dict[str, str]] = []

    label_counts = {k: 0 for k in LABELS}
    label_risk_map = {"TY": 0.30, "SY": 0.70, "TE": 0.45, "SE": 0.55}
    priors = PRIOR_PROFILES[ns.prior_profile]
    for i in range(ns.n_samples):
        sid = f"{ns.sample_prefix}_{i+1:05d}"
        label = rng.choice(LABELS)
        label_counts[label] += 1
        risk = max(0.0, min(1.0, label_risk_map[label] + rng.uniform(-0.08, 0.08)))
        cohort_rows.append(
            {
                "sample_id": sid,
                "expected_parent": label,
                "risk_score": f"{risk:.6f}",
                "cohort_origin": "literature_proxy_external_blind",
            }
        )
        for rsid in RSIDS:
            g = _choice_weighted(rng, priors[label][rsid])
            if g not in GENOTYPES:
                g = "AA"
            geno_rows.append({"sample_id": sid, "rsid": rsid, "genotype": g})

    with cohort_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sample_id", "expected_parent", "risk_score", "cohort_origin"])
        w.writeheader()
        w.writerows(cohort_rows)
    with geno_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sample_id", "rsid", "genotype"])
        w.writeheader()
        w.writerows(geno_rows)

    cmd = [
        sys.executable,
        str(ns.projection_script),
        "--genotype-csv",
        str(geno_csv),
        "--cohort-csv",
        str(cohort_csv),
        "--axis-weights-json",
        str(ns.active_weights_json),
        "--output-json",
        str(projection_json),
    ]
    run = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if run.returncode != 0:
        raise SystemExit(run.stderr or run.stdout)

    proj = json.loads(projection_json.read_text(encoding="utf-8"))
    # Evaluate on all generated samples (do not rely on preview truncation).
    weights = json.loads(ns.active_weights_json.read_text(encoding="utf-8"))
    counts_by_sid: dict[str, dict[str, int]] = {}
    for row in geno_rows:
        sid = row["sample_id"]
        g = row["genotype"]
        c = counts_by_sid.setdefault(sid, {"A": 0, "C": 0, "G": 0, "T": 0})
        for ch in g:
            if ch in c:
                c[ch] += 1
    pred_map: dict[str, str] = {}
    for sid, cnt in counts_by_sid.items():
        total = sum(cnt.values()) or 1
        ratios = {b: cnt[b] / total for b in ("A", "C", "G", "T")}
        raw = {
            ax: sum(ratios[b] * float(weights[b][ax]) for b in ("A", "C", "G", "T"))
            for ax in ("TY", "SY", "TE", "SE")
        }
        proj_axis = _normalize(raw)
        top = sorted(proj_axis.items(), key=lambda kv: (-kv[1], LABELS.index(kv[0])))[0][0]
        pred_map[sid] = top
    truth_map = {r["sample_id"]: r["expected_parent"] for r in cohort_rows}
    overlap_ids = sorted(set(pred_map.keys()) & set(truth_map.keys()))

    correct = sum(1 for sid in overlap_ids if pred_map.get(sid) == truth_map.get(sid))
    acc = (correct / len(overlap_ids)) if overlap_ids else 0.0

    risk_truth: list[float] = []
    risk_pred: list[float] = []
    proxy_risk = {"TY": 0.30, "SY": 0.70, "TE": 0.45, "SE": 0.55}
    for sid in overlap_ids:
        risk_truth.append(float(next(r["risk_score"] for r in cohort_rows if r["sample_id"] == sid)))
        risk_pred.append(float(proxy_risk.get(pred_map[sid], 0.5)))
    risk_corr = _safe_corr(risk_truth, risk_pred)

    payload = {
        "schema": "agct_sasang_external_blind_proxy_eval_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "governance": {"research_only": True, "non_gating": True, "human_review_required": True},
        "inputs": {
            "n_samples": int(ns.n_samples),
            "seed": int(ns.seed),
            "prior_profile": ns.prior_profile,
            "active_weights_json": str(ns.active_weights_json.resolve()),
            "cohort_csv": str(cohort_csv.resolve()),
            "genotype_csv": str(geno_csv.resolve()),
            "projection_json": str(projection_json.resolve()),
            "literature_rsids": list(RSIDS),
        },
        "summary": {
            "label_distribution": label_counts,
            "blind_eval_overlap_n": len(overlap_ids),
            "top_axis_accuracy_vs_proxy_label": acc,
            "predicted_risk_corr_with_proxy_risk": risk_corr,
        },
        "notes": [
            "External cohort is literature-prior proxy, not clinical raw cohort.",
            "Use for B-track stress/robustness only.",
        ],
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {ns.output_json.resolve()} "
        f"acc={acc:.4f} risk_corr={risk_corr}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
