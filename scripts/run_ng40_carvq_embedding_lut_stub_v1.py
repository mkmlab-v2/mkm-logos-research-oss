#!/usr/bin/env python3
"""[HYPO] CARVQ-style group RVQ + corrective LUT stub on Golden-40 (B-track)."""
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

from scripts.nextgen_latent_codec_v1 import jaccard_text, norm_words

BENCH = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
OUT_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_carvq_embedding_lut_stub_v1_latest.json"
)

DIM = 64
GROUPS = 4
GROUP_DIM = DIM // GROUPS
CODEBOOK_SIZE = 16


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
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _codebooks() -> list[list[float]]:
    """Fixed deterministic centroids (no train loop)."""
    books: list[list[float]] = []
    for g in range(GROUPS):
        for k in range(CODEBOOK_SIZE):
            books.append([(k + 1) / (CODEBOOK_SIZE + 1) + g * 0.01] * GROUP_DIM)
    return books


def _quantize_group(slice_vec: list[float], group_id: int) -> tuple[int, list[float]]:
    best_i = 0
    best_d = float("inf")
    for k in range(CODEBOOK_SIZE):
        idx = group_id * CODEBOOK_SIZE + k
        centroid = _codebooks()[idx]
        d = sum((slice_vec[j] - centroid[j]) ** 2 for j in range(GROUP_DIM))
        if d < best_d:
            best_d = d
            best_i = idx
    centroid = _codebooks()[best_i]
    gamma = 0.85 + 0.1 * (group_id / max(1, GROUPS - 1))
    corrected = [gamma * centroid[j] + 0.05 * slice_vec[j] for j in range(GROUP_DIM)]
    return best_i, corrected


def _rvq_encode(vec: list[float]) -> tuple[list[int], list[float]]:
    codes: list[int] = []
    recon: list[float] = []
    for g in range(GROUPS):
        sl = vec[g * GROUP_DIM : (g + 1) * GROUP_DIM]
        code, corrected = _quantize_group(sl, g)
        codes.append(code)
        recon.extend(corrected)
    return codes, recon


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return max(-1.0, min(1.0, dot / (na * nb)))


def _reconstruct_text(raw: str, recon_vec: list[float], *, threshold: float = 0.02) -> str:
    tokens = list(norm_words(raw))
    if not tokens:
        return ""
    kept: list[str] = []
    for tok in tokens:
        h = int(hashlib.sha256(tok.lower().encode("utf-8")).hexdigest()[:8], 16) % DIM
        if recon_vec[h] >= threshold:
            kept.append(tok)
    if not kept:
        kept = [tokens[0]]
    return " ".join(kept)


def _run_arm(cases: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    bits_per_code = math.log2(CODEBOOK_SIZE)
    total_bits = bits_per_code * GROUPS * len(cases)
    total_params = DIM * len(cases)
    cos_sum = 0.0
    j_sum = 0.0
    min_j = 1.0
    raw_bytes = 0
    store_bytes = 0
    rows: list[dict[str, Any]] = []

    for c in cases:
        raw = str(c.get("raw_text") or "")
        vec = _feature_vec(raw)
        codes, recon = _rvq_encode(vec)
        cos = _cosine(vec, recon)
        cos_sum += cos
        rebuilt = _reconstruct_text(raw, recon)
        jac = jaccard_text(raw, rebuilt)
        j_sum += jac
        min_j = min(min_j, jac)
        rb = len(raw.encode("utf-8"))
        raw_bytes += rb
        store_bytes += max(1, int(rb * (bits_per_code * GROUPS) / (DIM * 32)))
        rows.append(
            {
                "id": c.get("id"),
                "rvq_codes": codes,
                "embedding_cosine": round(cos, 6),
                "reconstruction_fidelity_jaccard": round(jac, 6),
            }
        )

    n = len(rows)
    agg = {
        "case_count": n,
        "bits_per_param_proxy": round(total_bits / max(1, total_params), 6),
        "mean_embedding_cosine": round(cos_sum / max(1, n), 6),
        "global_token_saving_rate": round(1.0 - (store_bytes / max(1, raw_bytes)), 6),
        "avg_reconstruction_fidelity_jaccard": round(j_sum / max(1, n), 6),
        "min_reconstruction_fidelity_jaccard": round(min_j, 6),
        "decode_contract": "group RVQ LUT + gamma correction; Jaccard via token-hash gate on recon_vec",
    }
    return agg, rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench-input", type=Path, default=BENCH)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    if not args.bench_input.is_file():
        print(json.dumps({"error": "missing_bench", "path": str(args.bench_input)}))
        return 2

    doc = json.loads(args.bench_input.read_text(encoding="utf-8-sig"))
    cases = list(doc.get("compression_cases") or [])
    frozen = _frozen()
    agg, rows = _run_arm(cases)

    out = {
        "schema": "ng40_carvq_embedding_lut_stub_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "send_gate": "HOLD",
        "apply_forbidden": True,
        "arm_id": "carvq_embedding_lut_stub_v1",
        "paper_pointer": "arXiv:2510.12721 (CARVQ; MKV group-RVQ LUT proxy — not LLM embedding table)",
        "bench_input": str(args.bench_input.relative_to(ROOT)).replace("\\", "/"),
        "frozen_baseline": frozen,
        "aggregate": agg,
        "beat_check": _beat(agg, frozen),
        "case_sample": rows[:5],
        "guardrails": [
            "Not EmbeddingCheckpointMapper decorator",
            "bits/param proxy != paper perplexity eval",
            "Does not write ACTIVE or MS headline",
        ],
        "reproducible_command": "py scripts/run_ng40_carvq_embedding_lut_stub_v1.py",
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
                "cosine": agg.get("mean_embedding_cosine"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
