#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASES = ("A", "C", "G", "T")
AXES = ("TY", "SY", "TE", "SE")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "").strip() or f"exit {r.returncode}")
    return r


def _load_json_when_ready(path: Path, *, attempts: int = 10, sleep_s: float = 0.04) -> dict[str, Any]:
    """Read JSON output; retry for slow FS / transient empty reads (Windows)."""
    last_err: BaseException | None = None
    for i in range(attempts):
        try:
            if path.is_file() and path.stat().st_size > 0:
                txt = path.read_text(encoding="utf-8")
                if txt.strip():
                    return json.loads(txt)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
            last_err = exc
        time.sleep(sleep_s * (i + 1))
    raise RuntimeError(
        f"Missing or invalid JSON at {path.resolve()} after {attempts} attempts (last_err={last_err!r})"
    )


def _safe_float(x: object) -> float:
    try:
        if x is None:
            return 0.0
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _l1_dict(a: dict[str, object], b: dict[str, object]) -> float:
    keys = set(a.keys()) | set(b.keys())
    return sum(abs(_safe_float(a.get(k)) - _safe_float(b.get(k))) for k in keys)


def _minmax_norm(values: list[float]) -> list[float]:
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if hi <= lo:
        return [0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def _quantile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    q = min(1.0, max(0.0, q))
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac


def _build_segment_inputs(
    root: Path,
    cohort_csv: Path,
    genotype_csv: Path,
    work: Path,
) -> dict[str, dict[str, object]]:
    work.mkdir(parents=True, exist_ok=True)

    with cohort_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    risk_vals = []
    for r in rows:
        try:
            risk_vals.append(float(r.get("risk_score", "") or "nan"))
        except ValueError:
            continue
    risk_vals = sorted([x for x in risk_vals if x == x])  # drop NaN
    q25 = _quantile(risk_vals, 0.25)
    q75 = _quantile(risk_vals, 0.75)

    def _write_subset(tag: str, pred) -> tuple[Path, Path, int]:
        subset = [r for r in rows if pred(r)]
        ids = {str(r.get("sample_id") or "").strip() for r in subset}
        c_out = work / f"segment_{tag}_cohort.csv"
        g_out = work / f"segment_{tag}_geno.csv"
        if subset:
            with c_out.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(subset[0].keys()))
                w.writeheader()
                w.writerows(subset)
        else:
            with c_out.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["sample_id", "risk_score"])
                w.writeheader()
        with genotype_csv.open("r", encoding="utf-8", newline="") as f:
            geno_rows = list(csv.DictReader(f))
        g_subset = [r for r in geno_rows if str(r.get("sample_id") or "").strip() in ids]
        if g_subset:
            with g_out.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(g_subset[0].keys()))
                w.writeheader()
                w.writerows(g_subset)
        else:
            with g_out.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["sample_id", "rsid", "genotype"])
                w.writeheader()
        return c_out, g_out, len(ids)

    def _risk_of(r: dict[str, object]) -> float:
        try:
            return float(r.get("risk_score", "") or "nan")
        except ValueError:
            return float("nan")

    c_stress, g_stress, n_stress = _write_subset("stress_tail", lambda r: (_risk_of(r) == _risk_of(r)) and (_risk_of(r) >= q75))
    c_reco, g_reco, n_reco = _write_subset(
        "recovery_stability",
        lambda r: (_risk_of(r) == _risk_of(r)) and (q25 <= _risk_of(r) <= q75),
    )
    return {
        "full": {"cohort_csv": cohort_csv, "genotype_csv": genotype_csv, "n_samples": len({str(r.get("sample_id") or "").strip() for r in rows})},
        "stress_tail": {"cohort_csv": c_stress, "genotype_csv": g_stress, "n_samples": n_stress, "risk_threshold_q75": q75},
        "recovery_stability": {"cohort_csv": c_reco, "genotype_csv": g_reco, "n_samples": n_reco, "risk_band_q25_q75": [q25, q75]},
    }


def _baseline() -> dict[str, dict[str, float]]:
    return {b: {a: 0.25 for a in AXES} for b in BASES}


def _remove_component(
    full_w: dict[str, dict[str, float]],
    mask: dict[str, dict[str, float]],
) -> dict[str, dict[str, float]]:
    base = _baseline()
    out: dict[str, dict[str, float]] = {}
    for b in BASES:
        row = {}
        for a in AXES:
            m = float(mask[b][a])
            # remove masked signal by blending back to baseline
            row[a] = base[b][a] + (float(full_w[b][a]) - base[b][a]) * (1.0 - m)
        # normalize row
        s = sum(row.values())
        out[b] = {k: (v / s if s > 0 else 0.25) for k, v in row.items()}
    return out


def _mask_none() -> dict[str, dict[str, float]]:
    return {b: {a: 0.0 for a in AXES} for b in BASES}


def _build_component_masks() -> dict[str, dict[str, dict[str, float]]]:
    z = _mask_none()
    # Heuristic mapping of Sasang-theory terms to axis influence blocks (B-track only).
    byung = json.loads(json.dumps(z))
    geumhwa = json.loads(json.dumps(z))
    bomyeong = json.loads(json.dumps(z))

    # 병증약리: TE/SE block + weak cross-coupling to TY/SY
    # (more granular than pure TE/SE hard mask)
    byung["A"]["TE"] = 1.0
    byung["A"]["SE"] = 0.7
    byung["A"]["TY"] = 0.15
    byung["A"]["SY"] = 0.10

    byung["C"]["TE"] = 0.7
    byung["C"]["SE"] = 1.0
    byung["C"]["TY"] = 0.10
    byung["C"]["SY"] = 0.15

    byung["G"]["TE"] = 1.0
    byung["G"]["SE"] = 0.7
    byung["G"]["TY"] = 0.10
    byung["G"]["SY"] = 0.15

    byung["T"]["TE"] = 0.7
    byung["T"]["SE"] = 1.0
    byung["T"]["TY"] = 0.15
    byung["T"]["SY"] = 0.10

    # 금화교역: TY/SY dynamic exchange block with base-specific asymmetry
    geumhwa["A"]["TY"] = 1.0
    geumhwa["A"]["SY"] = 0.8
    geumhwa["C"]["TY"] = 0.8
    geumhwa["C"]["SY"] = 1.0
    geumhwa["G"]["TY"] = 0.9
    geumhwa["G"]["SY"] = 1.0
    geumhwa["T"]["TY"] = 1.0
    geumhwa["T"]["SY"] = 0.9

    # 보명지주: stabilizer + axis-balance regularizer with uneven weights
    bomyeong["A"]["TY"] = 0.55
    bomyeong["A"]["SY"] = 0.35
    bomyeong["A"]["TE"] = 0.25
    bomyeong["A"]["SE"] = 0.45

    bomyeong["C"]["TY"] = 0.35
    bomyeong["C"]["SY"] = 0.55
    bomyeong["C"]["TE"] = 0.45
    bomyeong["C"]["SE"] = 0.25

    bomyeong["G"]["TY"] = 0.30
    bomyeong["G"]["SY"] = 0.45
    bomyeong["G"]["TE"] = 0.60
    bomyeong["G"]["SE"] = 0.30

    bomyeong["T"]["TY"] = 0.45
    bomyeong["T"]["SY"] = 0.30
    bomyeong["T"]["TE"] = 0.30
    bomyeong["T"]["SE"] = 0.60

    return {
        "byungjeungyakri": byung,
        "geumhwagyoyeok": geumhwa,
        "bomyeongjiju": bomyeong,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="AGCT->Sasang formula contribution report by component ablation (B-track).")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--cohort-csv", type=Path, default=root / "tmp" / "bio_real_cohort_merged_with_sidecar_v1.csv")
    ap.add_argument("--genotype-csv", type=Path, default=root / "tmp" / "bio_genotype_long_v1.csv")
    ap.add_argument("--weights-json", type=Path, default=root / "tmp" / "agct_sasang_axis_weights_active_btrack_v1.json")
    ap.add_argument("--output-json", type=Path, default=root / "reports" / "agct_sasang_formula_contribution_report_v1_latest.json")
    ns = ap.parse_args()

    eval_script = root / "scripts" / "run_agct_biovalidity_clinical_proxy_eval_v1.py"
    proj_script = root / "scripts" / "run_agct_sasang_composition_projection_v1.py"
    full_w = json.loads(ns.weights_json.read_text(encoding="utf-8"))
    masks = _build_component_masks()

    # Isolate intermediates per invocation so parallel stress scans / chains cannot clobber paths.
    work = root / "tmp" / "agct_formula_contrib_v1" / f"run_{uuid.uuid4().hex[:16]}"
    work.mkdir(parents=True, exist_ok=True)

    def eval_with_weights(tag: str, cohort: Path, geno: Path, w: dict[str, dict[str, float]]) -> tuple[dict, dict]:
        w_path = work / f"{tag}_weights.json"
        o_path = work / f"{tag}_eval.json"
        p_path = work / f"{tag}_projection.json"
        w_path.write_text(json.dumps(w, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _run(
            [
                sys.executable,
                str(eval_script),
                "--cohort-csv",
                str(cohort),
                "--genotype-csv",
                str(geno),
                "--weights-json",
                str(w_path),
                "--output-json",
                str(o_path),
            ],
            root,
        )
        ev = _load_json_when_ready(o_path)
        _run(
            [
                sys.executable,
                str(proj_script),
                "--genotype-csv",
                str(geno),
                "--cohort-csv",
                str(cohort),
                "--axis-weights-json",
                str(w_path),
                "--output-json",
                str(p_path),
            ],
            root,
        )
        pv = _load_json_when_ready(p_path)
        return ev, pv

    segment_inputs = _build_segment_inputs(root, ns.cohort_csv, ns.genotype_csv, work)

    segment_reports: dict[str, dict[str, object]] = {}
    for seg_name, seg_meta in segment_inputs.items():
        cohort = Path(seg_meta["cohort_csv"])
        geno = Path(seg_meta["genotype_csv"])
        full_eval, full_proj = eval_with_weights(f"{seg_name}_full", cohort, geno, full_w)
        base = full_eval["summary"]
        base_corr = float(base["risk_corr_proxy"] or 0.0)
        base_acc = float(base["classification_accuracy"])
        base_axis_top = full_proj["summary"]["axis_top_counts"]
        base_axis_means = {a: full_proj["summary"]["axis_summary"][a]["mean_projection"] for a in AXES}
        base_risk_axis = {
            a: _safe_float((full_proj["risk_axis_correlations"].get(a, {}) or {}).get("pearson_corr_with_risk"))
            for a in AXES
        }

        rows = []
        for name, mask in masks.items():
            ablated_w = _remove_component(full_w, mask)
            ev, pv = eval_with_weights(f"{seg_name}_ablated_{name}", cohort, geno, ablated_w)
            s = ev["summary"]
            corr = float(s["risk_corr_proxy"] or 0.0)
            acc = float(s["classification_accuracy"])
            axis_top = pv["summary"]["axis_top_counts"]
            axis_means = {a: pv["summary"]["axis_summary"][a]["mean_projection"] for a in AXES}
            risk_axis = {
                a: _safe_float((pv["risk_axis_correlations"].get(a, {}) or {}).get("pearson_corr_with_risk"))
                for a in AXES
            }
            rows.append(
                {
                    "component": name,
                    "risk_corr_after_ablation": corr,
                    "delta_risk_corr_vs_full": corr - base_corr,
                    "accuracy_after_ablation": acc,
                    "delta_accuracy_vs_full": acc - base_acc,
                    "axis_top_count_l1_vs_full": _l1_dict(axis_top, base_axis_top),
                    "axis_mean_projection_l1_vs_full": _l1_dict(axis_means, base_axis_means),
                    "risk_axis_corr_l1_vs_full": _l1_dict(risk_axis, base_risk_axis),
                    "report": str((work / f"{seg_name}_ablated_{name}_eval.json").resolve()),
                    "projection_report": str((work / f"{seg_name}_ablated_{name}_projection.json").resolve()),
                }
            )

        mag_delta_corr = [abs(float(r["delta_risk_corr_vs_full"])) for r in rows]
        mag_delta_acc = [abs(float(r["delta_accuracy_vs_full"])) for r in rows]
        risk_l1 = [float(r["risk_axis_corr_l1_vs_full"]) for r in rows]
        axis_l1 = [float(r["axis_mean_projection_l1_vs_full"]) for r in rows]
        top_l1 = [float(r["axis_top_count_l1_vs_full"]) for r in rows]
        n_dc = _minmax_norm(mag_delta_corr)
        n_da = _minmax_norm(mag_delta_acc)
        n_rk = _minmax_norm(risk_l1)
        n_ax = _minmax_norm(axis_l1)
        n_tp = _minmax_norm(top_l1)
        for i, r in enumerate(rows):
            score = (
                0.25 * n_dc[i]
                + 0.15 * n_da[i]
                + 0.30 * n_rk[i]
                + 0.20 * n_ax[i]
                + 0.10 * n_tp[i]
            )
            r["contribution_score"] = score
        rows.sort(key=lambda x: float(x["contribution_score"]), reverse=True)
        for i, r in enumerate(rows, start=1):
            r["contribution_rank"] = i

        segment_reports[seg_name] = {
            "segment_meta": {k: v for k, v in seg_meta.items() if k not in ("cohort_csv", "genotype_csv")},
            "full_model": {
                "risk_corr_proxy": base_corr,
                "classification_accuracy": base_acc,
                "report": str((work / f"{seg_name}_full_eval.json").resolve()),
                "projection_report": str((work / f"{seg_name}_full_projection.json").resolve()),
            },
            "component_ablations": rows,
            "ranking_summary": [
                {
                    "component": r["component"],
                    "contribution_score": r["contribution_score"],
                    "contribution_rank": r["contribution_rank"],
                }
                for r in rows
            ],
            "interpretation": {
                "top_component_by_contribution_score": rows[0]["component"] if rows else None,
                "note": "Composite score combines performance deltas and axis-structure drifts after ablation (B-track heuristic).",
            },
        }

    full_report = segment_reports["full"]
    payload = {
        "schema": "agct_sasang_formula_contribution_report_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "governance": {
            "research_only": True,
            "non_gating": True,
            "human_review_required": True,
        },
        "inputs": {
            "cohort_csv": str(ns.cohort_csv.resolve()),
            "genotype_csv": str(ns.genotype_csv.resolve()),
            "weights_json": str(ns.weights_json.resolve()),
        },
        "full_model": full_report["full_model"],
        "component_ablations": full_report["component_ablations"],
        "ranking_summary": full_report["ranking_summary"],
        "interpretation": full_report["interpretation"],
        "segment_reports": segment_reports,
        "notes": [
            "Component-to-theory mapping is heuristic and B-track-only.",
            "stress_tail/recovery_stability segmentation uses risk-score quantile heuristics (q75 / q25..q75).",
            "Do not interpret as clinical/causal proof.",
        ],
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} full_corr={float(full_report['full_model']['risk_corr_proxy']):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
