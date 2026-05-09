#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gen_seq(rng: random.Random, n: int, mode: str) -> str:
    # mode controls composition bias for sensitivity testing.
    if mode == "yang_bias":
        weights = [0.38, 0.12, 0.34, 0.16]  # A,C,G,T
    elif mode == "yin_bias":
        weights = [0.16, 0.34, 0.14, 0.36]
    elif mode == "heat_bias":
        weights = [0.20, 0.16, 0.20, 0.44]
    elif mode == "cold_bias":
        weights = [0.44, 0.20, 0.20, 0.16]
    else:
        weights = [0.25, 0.25, 0.25, 0.25]
    bases = ("A", "C", "G", "T")
    return "".join(rng.choices(bases, weights=weights, k=n))


def _count_motif(seq: str, motif: str) -> int:
    if not motif:
        return 0
    m = len(motif)
    return sum(1 for i in range(0, len(seq) - m + 1) if seq[i : i + m] == motif)


def _evaluate(seq: str) -> dict:
    n = len(seq) or 1
    c = {b: seq.count(b) for b in ("A", "C", "G", "T")}
    r = {b: c[b] / n for b in c}

    yang = r["A"] + r["G"]
    yin = r["C"] + r["T"]
    heat = r["T"] + 0.5 * r["G"]
    cold = r["A"] + 0.5 * r["C"]

    motif_ag = _count_motif(seq, "AGAG")
    motif_ct = _count_motif(seq, "CTCT")
    motif_fire = _count_motif(seq, "TTG")
    motif_water = _count_motif(seq, "AAC")

    # heuristic axis scores (B-track symbolic)
    ty = yang + 0.15 * motif_ag / max(1, n / 4)
    sy = heat + 0.20 * motif_fire / max(1, n / 3)
    te = yin + 0.15 * motif_ct / max(1, n / 4)
    se = cold + 0.20 * motif_water / max(1, n / 3)

    raw = {"TY": ty, "SY": sy, "TE": te, "SE": se}
    s = sum(raw.values()) or 1.0
    proj = {k: v / s for k, v in raw.items()}
    top = sorted(proj.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    return {
        "counts": c,
        "ratios": r,
        "yinyang": {"yang": yang, "yin": yin},
        "thermo": {"heat": heat, "cold": cold},
        "motifs": {"AGAG": motif_ag, "CTCT": motif_ct, "TTG": motif_fire, "AAC": motif_water},
        "axis_projection": proj,
        "top_axis": top,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Synthetic AGCT motif/yinyang/sasang integrity test.")
    ap.add_argument("--n-samples", type=int, default=1000)
    ap.add_argument("--seq-len", type=int, default=120)
    ap.add_argument("--seed", type=int, default=20260505)
    ap.add_argument(
        "--output-json",
        type=Path,
        default=Path("reports/agct_motif_yinyang_sasang_synthetic_integrity_v1_latest.json"),
    )
    ns = ap.parse_args()

    rng = random.Random(ns.seed)
    modes = ("balanced", "yang_bias", "yin_bias", "heat_bias", "cold_bias")

    rows: list[dict] = []
    failures = 0
    for i in range(ns.n_samples):
        mode = modes[i % len(modes)]
        seq = _gen_seq(rng, ns.seq_len, mode)
        out = _evaluate(seq)

        # integrity checks: conservation + bounded outputs
        ratio_sum = sum(out["ratios"].values())
        proj_sum = sum(out["axis_projection"].values())
        ok = abs(ratio_sum - 1.0) < 1e-9 and abs(proj_sum - 1.0) < 1e-9 and out["top_axis"] in {"TY", "SY", "TE", "SE"}
        if not ok:
            failures += 1
        rows.append({"mode": mode, **out, "integrity_ok": ok})

    # sensitivity summary by mode
    by_mode: dict[str, dict] = {}
    for m in modes:
        subset = [r for r in rows if r["mode"] == m]
        n = len(subset) or 1
        top_counts = {"TY": 0, "SY": 0, "TE": 0, "SE": 0}
        yang_vals, yin_vals = [], []
        for r in subset:
            top_counts[r["top_axis"]] += 1
            yang_vals.append(r["yinyang"]["yang"])
            yin_vals.append(r["yinyang"]["yin"])
        by_mode[m] = {
            "n": len(subset),
            "top_axis_counts": top_counts,
            "mean_yang": sum(yang_vals) / n,
            "mean_yin": sum(yin_vals) / n,
        }

    payload = {
        "schema": "agct_motif_yinyang_sasang_synthetic_integrity_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "governance": {"research_only": True, "non_gating": True, "human_review_required": True},
        "inputs": {"n_samples": ns.n_samples, "seq_len": ns.seq_len, "seed": ns.seed},
        "summary": {
            "integrity_failures": failures,
            "integrity_pass": failures == 0,
            "modes": by_mode,
        },
        "preview": rows[:20],
        "notes": [
            "Synthetic integrity test validates rule consistency and sensitivity only.",
            "Not biological or clinical proof.",
        ],
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} integrity_failures={failures}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
