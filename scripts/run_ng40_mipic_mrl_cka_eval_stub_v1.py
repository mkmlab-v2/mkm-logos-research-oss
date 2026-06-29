#!/usr/bin/env python3
"""[HYPO] MIPIC-style MRL truncation + linear CKA proxy on Golden-40 (B-track stub)."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.nextgen_latent_codec_v1 import jaccard_text, latent_salience_reconstruct

BENCH = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
OUT_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_mipic_mrl_cka_eval_stub_v1_latest.json"
)

DIM = 64
MRL_LEVELS = (8, 16, 32, 48, 64)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _frozen() -> dict[str, Any]:
    if not ACTIVE.is_file():
        return {"present": False}
    cm = json.loads(ACTIVE.read_text(encoding="utf-8")).get("compression_metrics") or {}
    return {
        "present": True,
        "global_token_saving_rate": cm.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
    }


def _beat(cand: dict, fr: dict) -> dict[str, Any]:
    if not fr.get("present"):
        return {"beat_frozen": False, "reason": "missing_frozen"}
    s_c, j_c = cand.get("global_token_saving_rate"), cand.get("avg_reconstruction_fidelity_jaccard")
    s_f, j_f = fr.get("global_token_saving_rate"), fr.get("avg_reconstruction_fidelity_jaccard")
    if None in (s_c, j_c, s_f, j_f):
        return {"beat_frozen": False, "reason": "incomplete_metrics"}
    beat = float(s_c) >= float(s_f) and float(j_c) >= float(j_f)
    return {
        "beat_frozen": beat,
        "delta_saving_pp": round((float(s_c) - float(s_f)) * 100, 2),
        "delta_jaccard_pp": round((float(j_c) - float(j_f)) * 100, 2),
        "reason": "both_saving_and_jaccard_gte_frozen" if beat else "not_both_axes",
    }


def _feature_vec(text: str, dim: int = DIM) -> list[float]:
    vec = [0.0] * dim
    low = text.lower()
    for i in range(max(0, len(low) - 2)):
        gram = low[i : i + 3]
        h = int(hashlib.sha256(gram.encode("utf-8")).hexdigest()[:8], 16) % dim
        vec[h] += 1.0
    if not any(vec):
        vec[0] = 1.0
    return vec


def _truncate(vec: list[float], k: int) -> list[float]:
    k = max(1, min(len(vec), k))
    return vec[:k] + [0.0] * (len(vec) - k)


def _center(mat: list[list[float]]) -> list[list[float]]:
    if not mat:
        return []
    n = len(mat)
    d = len(mat[0])
    means = [sum(row[j] for row in mat) / n for j in range(d)]
    return [[row[j] - means[j] for j in range(d)] for row in mat]


def _frobenius(a: list[list[float]]) -> float:
    return math.sqrt(sum(v * v for row in a for v in row))


def _matmul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    n, m, p = len(a), len(a[0]), len(b[0])
    out = [[0.0] * p for _ in range(n)]
    for i in range(n):
        for k in range(m):
            aik = a[i][k]
            if aik == 0.0:
                continue
            for j in range(p):
                out[i][j] += aik * b[k][j]
    return out


def _transpose(a: list[list[float]]) -> list[list[float]]:
    if not a:
        return []
    return [list(col) for col in zip(*a)]


def _linear_cka(x: list[list[float]], y: list[list[float]]) -> float:
    if not x or not y or len(x) != len(y):
        return 0.0
    xc, yc = _center(x), _center(y)
    xtx = _matmul(_transpose(xc), xc)
    yty = _matmul(_transpose(yc), yc)
    ytx = _matmul(_transpose(yc), xc)
    num = _frobenius(ytx) ** 2
    den = _frobenius(xtx) * _frobenius(yty)
    if den <= 1e-12:
        return 0.0
    return max(0.0, min(1.0, num / den))


def _run_arm(cases: list[dict[str, Any]], *, min_cka: float = 0.85) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    full_rows = [_feature_vec(str(c.get("raw_text") or "")) for c in cases]
    level_rows: list[dict[str, Any]] = []
    best_level = MRL_LEVELS[-1]
    best_cka = 0.0

    for k in MRL_LEVELS:
        trunc_rows = [_truncate(v, k) for v in full_rows]
        cka = _linear_cka(full_rows, trunc_rows)
        level_rows.append(
            {
                "mrl_dims": k,
                "dim_saving_rate": round(1.0 - (k / DIM), 6),
                "mean_linear_cka": round(cka, 6),
            }
        )
        if cka >= min_cka and k < best_level:
            best_level = k
            best_cka = cka
        elif cka > best_cka and best_cka < min_cka:
            best_level = k
            best_cka = cka

    keep_ratio = max(0.05, best_level / DIM)
    case_rows: list[dict[str, Any]] = []
    j_sum = 0.0
    min_j = 1.0
    raw_bytes = 0
    store_bytes = 0
    for c in cases:
        raw = str(c.get("raw_text") or "")
        recon, _ = latent_salience_reconstruct(raw, keep_ratio)
        jac = jaccard_text(raw, recon)
        j_sum += jac
        min_j = min(min_j, jac)
        rb = len(raw.encode("utf-8"))
        raw_bytes += rb
        store_bytes += max(1, int(rb * keep_ratio))
        case_rows.append(
            {
                "id": c.get("id"),
                "mrl_dims": best_level,
                "keep_ratio": round(keep_ratio, 6),
                "reconstruction_fidelity_jaccard": round(jac, 6),
            }
        )

    n = len(case_rows)
    agg = {
        "case_count": n,
        "mrl_dims_selected": best_level,
        "mean_linear_cka_at_selected": round(best_cka, 6),
        "global_token_saving_rate": round(1.0 - (store_bytes / max(1, raw_bytes)), 6),
        "avg_reconstruction_fidelity_jaccard": round(j_sum / max(1, n), 6),
        "min_reconstruction_fidelity_jaccard": round(min_j, 6),
        "decode_contract": "latent_salience_reconstruct at MRL-selected keep_ratio; CKA is hashed-trigram proxy",
    }
    return agg, case_rows, level_rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench-input", type=Path, default=BENCH)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--min-cka", type=float, default=0.85)
    args = ap.parse_args()
    if not args.bench_input.is_file():
        print(json.dumps({"error": "missing_bench", "path": str(args.bench_input)}))
        return 2

    doc = json.loads(args.bench_input.read_text(encoding="utf-8-sig"))
    cases = list(doc.get("compression_cases") or [])
    frozen = _frozen()
    agg, case_rows, sweep = _run_arm(cases, min_cka=args.min_cka)
    case_sample = case_rows[:5]

    out = {
        "schema": "ng40_mipic_mrl_cka_eval_stub_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "send_gate": "HOLD",
        "apply_forbidden": True,
        "arm_id": "mipic_mrl_cka_eval_stub_v1",
        "paper_pointer": "arXiv:2604.24374 (MIPIC; MKM hashed-trigram CKA proxy only — not BGE STS/NLI)",
        "bench_input": str(args.bench_input.relative_to(ROOT)).replace("\\", "/"),
        "frozen_baseline": frozen,
        "aggregate": agg,
        "mrl_level_sweep": sweep,
        "beat_check": _beat(agg, frozen),
        "case_sample": case_sample,
        "guardrails": [
            "Not MIPIC_SIA_Alignment_Block or ng40_eval_v2",
            "CKA proxy != paper STS/NLI reproduction",
            "Does not write ACTIVE or MS headline",
        ],
        "reproducible_command": "py scripts/run_ng40_mipic_mrl_cka_eval_stub_v1.py",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "beat_frozen": out["beat_check"].get("beat_frozen"),
                "saving": agg.get("global_token_saving_rate"),
                "jaccard": agg.get("avg_reconstruction_fidelity_jaccard"),
                "cka": agg.get("mean_linear_cka_at_selected"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
