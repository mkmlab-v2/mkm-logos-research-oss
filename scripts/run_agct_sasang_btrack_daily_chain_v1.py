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


def _read_json_safe(path: Path) -> dict:
    """Read JSON robustly; tolerate accidental concatenated objects."""
    raw = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not raw:
        raise RuntimeError(f"empty_json:{path}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback for cases like '{"a":1}\n{"b":2}' -> parse first object.
        dec = json.JSONDecoder()
        obj, _idx = dec.raw_decode(raw)
        if not isinstance(obj, dict):
            raise RuntimeError(f"invalid_json_object:{path}")
        return obj


def _time_split_eval(root: Path, weights: Path, cohort: Path, geno: Path, out_json: Path) -> dict:
    outdir = root / "tmp" / "agct_daily_time_split_v1"
    outdir.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(cohort.open("r", encoding="utf-8", newline="")))
    ids = [r["sample_id"] for r in rows if r.get("sample_id")]
    split = int(round(len(ids) * 0.7))
    splits = [("train", set(ids[:split])), ("test", set(ids[split:]))]
    proj = root / "scripts" / "run_agct_sasang_composition_projection_v1.py"
    for tag, keep in splits:
        c_out = outdir / f"{tag}_cohort.csv"
        g_out = outdir / f"{tag}_geno.csv"
        c_rows = [r for r in rows if r.get("sample_id") in keep]
        with c_out.open("w", encoding="utf-8", newline="") as f:
            wri = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            wri.writeheader()
            wri.writerows(c_rows)
        g_all = list(csv.DictReader(geno.open("r", encoding="utf-8", newline="")))
        g_rows = [r for r in g_all if r.get("sample_id") in keep]
        with g_out.open("w", encoding="utf-8", newline="") as f:
            fields = list(g_rows[0].keys()) if g_rows else ["sample_id", "rsid", "genotype"]
            wri = csv.DictWriter(f, fieldnames=fields)
            wri.writeheader()
            wri.writerows(g_rows)
        p_out = outdir / f"{tag}_projection.json"
        _run(
            [
                sys.executable,
                str(proj),
                "--genotype-csv",
                str(g_out),
                "--cohort-csv",
                str(c_out),
                "--axis-weights-json",
                str(weights),
                "--output-json",
                str(p_out),
            ]
        )
    tr = _read_json_safe(outdir / "train_projection.json")
    te = _read_json_safe(outdir / "test_projection.json")
    axes = ("TY", "SY", "TE", "SE")

    def obj(d: dict) -> tuple[float, float, float]:
        s = d["summary"]["axis_summary"]
        r = d["risk_axis_correlations"]
        gap = max(v["mean_projection"] for v in s.values()) - min(v["mean_projection"] for v in s.values())
        risk = sum(abs((r.get(a, {}) or {}).get("pearson_corr_with_risk") or 0.0) for a in axes)
        return risk - gap, gap, risk

    o_tr, g_tr, r_tr = obj(tr)
    o_te, g_te, r_te = obj(te)
    rep = {
        "schema": "agct_sasang_composition_time_split_eval_v1",
        "track": "B_TRACK",
        "train": {"objective_score": o_tr, "axis_balance_gap": g_tr, "risk_signal_score": r_tr},
        "test": {"objective_score": o_te, "axis_balance_gap": g_te, "risk_signal_score": r_te},
        "generalization_gap_abs": abs(o_tr - o_te),
    }
    out_json.write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rep


def main() -> int:
    ap = argparse.ArgumentParser(description="Daily B-track AGCT-Sasang chain with thresholds and decision.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--active-weights-json", type=Path, default=root / "tmp" / "agct_sasang_axis_weights_active_btrack_v1.json")
    ap.add_argument(
        "--shadow-weights-json",
        type=Path,
        default=root / "tmp" / "agct_sasang_axis_weights_active_robust_candidate_v1.json",
    )
    ap.add_argument("--cohort-csv", type=Path, default=root / "tmp" / "bio_real_cohort_merged_with_sidecar_v1.csv")
    ap.add_argument("--genotype-csv", type=Path, default=root / "tmp" / "bio_genotype_long_v1.csv")
    ap.add_argument(
        "--thresholds-json",
        type=Path,
        default=root / "docs" / "final" / "artifacts" / "agct_sasang_btrack_daily_thresholds_v1.json",
    )
    ap.add_argument("--external-n-samples", type=int, default=1200)
    ap.add_argument("--robustness-n-samples", type=int, default=800)
    ap.add_argument("--seed", type=int, default=20260505)
    ap.add_argument(
        "--output-json",
        type=Path,
        default=root / "reports" / "agct_sasang_btrack_daily_chain_v1_latest.json",
    )
    ns = ap.parse_args()

    tdoc = _read_json_safe(ns.thresholds_json)
    thresholds = tdoc["thresholds"]
    decision_profile = str(tdoc.get("decision_profile") or "aggressive").strip().lower()
    if decision_profile not in ("conservative", "neutral", "aggressive"):
        decision_profile = "aggressive"
    ext_script = root / "scripts" / "run_agct_sasang_external_blind_proxy_eval_v1.py"
    st_script = root / "scripts" / "run_agct_sasang_composition_profile_stability_v1.py"
    robust_script = root / "scripts" / "run_agct_adversarial_profile_grid_v1.py"

    external_results: dict[str, dict] = {}
    for profile in ("conservative", "neutral", "aggressive"):
        out = root / "tmp" / f"agct_daily_external_{profile}.json"
        _run(
            [
                sys.executable,
                str(ext_script),
                "--prior-profile",
                profile,
                "--n-samples",
                str(ns.external_n_samples),
                "--seed",
                str(ns.seed),
                "--active-weights-json",
                str(ns.active_weights_json),
                "--output-json",
                str(out),
            ]
        )
        external_results[profile] = _read_json_safe(out)

    stability_out = root / "reports" / "agct_sasang_composition_profile_stability_daily_latest.json"
    _run(
        [
            sys.executable,
            str(st_script),
            "--genotype-csv",
            str(ns.genotype_csv),
            "--cohort-csv",
            str(ns.cohort_csv),
            "--axis-weights-json",
            str(ns.active_weights_json),
            "--rounds",
            "30",
            "--sample-ratio",
            "0.7",
            "--seed",
            str(ns.seed),
            "--output-json",
            str(stability_out),
        ]
    )
    stability = _read_json_safe(stability_out)

    time_split_out = root / "reports" / "agct_sasang_composition_time_split_daily_latest.json"
    time_split = _time_split_eval(root, ns.active_weights_json, ns.cohort_csv, ns.genotype_csv, time_split_out)

    active_robust_out = root / "reports" / "agct_adversarial_profile_grid_daily_active_latest.json"
    _run(
        [
            sys.executable,
            str(robust_script),
            "--weights-json",
            str(ns.active_weights_json),
            "--n-samples",
            str(ns.robustness_n_samples),
            "--seed",
            str(ns.seed),
            "--output-json",
            str(active_robust_out),
        ]
    )
    active_robust = _read_json_safe(active_robust_out)
    active_robust_score = float(active_robust["summary"]["avg_robustness_score"])

    shadow_robust_score = None
    shadow_robust_out = root / "reports" / "agct_adversarial_profile_grid_daily_shadow_latest.json"
    if ns.shadow_weights_json.exists():
        _run(
            [
                sys.executable,
                str(robust_script),
                "--weights-json",
                str(ns.shadow_weights_json),
                "--n-samples",
                str(ns.robustness_n_samples),
                "--seed",
                str(ns.seed + 17),
                "--output-json",
                str(shadow_robust_out),
            ]
        )
        shadow_robust = _read_json_safe(shadow_robust_out)
        shadow_robust_score = float(shadow_robust["summary"]["avg_robustness_score"])

    chosen = external_results[decision_profile]["summary"]
    ext_acc = float(chosen["top_axis_accuracy_vs_proxy_label"])
    ext_corr = float(chosen["predicted_risk_corr_with_proxy_risk"] or 0.0)
    st_std = stability["summary"]["objective_score_std"]
    ts_gap = time_split["generalization_gap_abs"]
    robust_min = float(thresholds.get("robustness_min", 0.0))

    checks = {
        "external_accuracy_min_ok": ext_acc >= float(thresholds["external_accuracy_min"]),
        "external_risk_corr_min_ok": ext_corr >= float(thresholds["external_risk_corr_min"]),
        "stability_std_ok": st_std <= float(thresholds["stability_std_max"]),
        "time_split_gap_ok": ts_gap <= float(thresholds["time_split_gap_max"]),
        "robustness_min_ok": active_robust_score >= robust_min,
    }
    decision = "GO_BTRACK" if all(checks.values()) else "REVIEW_REQUIRED"

    payload = {
        "schema": "agct_sasang_btrack_daily_chain_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "decision": decision,
        "thresholds_json": str(ns.thresholds_json.resolve()),
        "checks": checks,
        "metrics": {
            "decision_profile": decision_profile,
            "external_accuracy_observed": ext_acc,
            "external_risk_corr_observed": ext_corr,
            "stability_std_observed": st_std,
            "time_split_gap_observed": ts_gap,
            "robustness_observed": active_robust_score,
            "robustness_threshold": robust_min,
            "shadow_robustness_observed": shadow_robust_score,
        },
        "external_profiles": {
            k: {
                "accuracy": v["summary"]["top_axis_accuracy_vs_proxy_label"],
                "risk_corr": v["summary"]["predicted_risk_corr_with_proxy_risk"],
            }
            for k, v in external_results.items()
        },
        "outputs": {
            "stability_report": str(stability_out.resolve()),
            "time_split_report": str(time_split_out.resolve()),
            "active_robustness_report": str(active_robust_out.resolve()),
            "shadow_robustness_report": str(shadow_robust_out.resolve()) if ns.shadow_weights_json.exists() else None,
        },
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} decision={decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
