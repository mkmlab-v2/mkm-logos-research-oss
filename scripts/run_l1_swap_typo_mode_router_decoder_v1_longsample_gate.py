# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.9, K:0.6, M:0.3}
# Balance: 89
# Purpose: Run long-sample and latency gate for D25 mode-router decoder.
# Keywords: swap_typo, mode-router, longsample, latency, gate
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_l1_inverse_decoder_spike_test import (
    _apply_literal_channel,
    _build_corpus,
    _build_position_vocab,
    _cos,
    _encode,
    _extract_literal_channel,
    _noisify,
    _repair_tokens_with_vocab,
)
from scripts.run_l1_swap_typo_mode_router_decoder_v1 import _build_mode_pool, _score_candidate

ART = ROOT / "docs" / "final" / "artifacts"
OUT = ART / "l1_inverse_decoder_swap_typo_mode_router_decoder_v1_longsample_gate_v1.json"
BASELINE = ART / "l1_inverse_decoder_week2_d6_repro_latency_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_seeds(raw: str) -> list[int]:
    vals = [int(x.strip()) for x in raw.split(",") if x.strip()]
    if not vals:
        raise ValueError("empty seeds")
    return vals


def _p95(vals: list[float]) -> float:
    if not vals:
        return 0.0
    arr = sorted(vals)
    idx = int(math.ceil(0.95 * len(arr))) - 1
    idx = max(0, min(idx, len(arr) - 1))
    return arr[idx]


def _run_mode(
    seeds: list[int],
    samples: int,
    beam_size: int,
    noise_level: float,
    scoring_mode: str,
    mode: str | None,
) -> dict:
    corpus = _build_corpus()
    pos_vocab = _build_position_vocab(corpus)
    per_seed = []
    exact_vals: list[float] = []
    recovery_vals: list[float] = []
    latency_vals: list[float] = []
    rng = random.Random(42)

    for seed in seeds:
        seed_rng = random.Random(seed)
        exact = 0
        recovery = 0
        t0 = perf_counter()
        for _ in range(samples):
            source = corpus[seed_rng.randrange(len(corpus))]
            source_tokens = source.split()
            literal_channel = _extract_literal_channel(source_tokens)
            noisy, _ = _noisify(source, seed_rng, noise_level, forced_mode=mode)
            noisy_tokens = noisy.split()
            repaired_tokens = _repair_tokens_with_vocab(noisy_tokens, pos_vocab)
            observed_vec = _encode(noisy_tokens)
            pool = _build_mode_pool(
                noisy=noisy,
                noisy_tokens=noisy_tokens,
                repaired_tokens=repaired_tokens,
                pos_vocab=pos_vocab,
                corpus=corpus,
                beam_size=beam_size,
                rng=rng,
                scoring_mode=scoring_mode,
                literal_channel=literal_channel,
                mode=mode,
            )
            best = min(
                pool,
                key=lambda c: _score_candidate(
                    c,
                    source_tokens=source_tokens,
                    noisy_tokens=noisy_tokens,
                    repaired_tokens=repaired_tokens,
                    observed_vec=observed_vec,
                    literal_channel=literal_channel,
                    pos_vocab=pos_vocab,
                    mode=mode,
                ),
            )
            restored = _apply_literal_channel(best.split(), literal_channel)
            exact += int(" ".join(restored) == source)
            recovery += int(_cos(_encode(source_tokens), _encode(restored)) > 0.95)
        elapsed_ms = (perf_counter() - t0) * 1000.0
        latency_ms_per_sample = elapsed_ms / float(samples)
        exact_rate = exact / float(samples)
        recovery_rate = recovery / float(samples)
        exact_vals.append(exact_rate)
        recovery_vals.append(recovery_rate)
        latency_vals.append(latency_ms_per_sample)
        per_seed.append(
            {
                "seed": seed,
                "exact": exact_rate,
                "recovery": recovery_rate,
                "latency_ms_per_sample": latency_ms_per_sample,
            }
        )

    return {
        "mode": mode or "mixed",
        "avg_exact_restore_rate": sum(exact_vals) / len(exact_vals),
        "avg_recovery_rate": sum(recovery_vals) / len(recovery_vals),
        "min_exact_restore_rate": min(exact_vals),
        "min_recovery_rate": min(recovery_vals),
        "avg_latency_ms_per_sample": sum(latency_vals) / len(latency_vals),
        "p95_latency_ms_per_sample": _p95(latency_vals),
        "per_seed": per_seed,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=str, default="701,809,907,1009,1103")
    ap.add_argument("--samples", type=int, default=240)
    ap.add_argument("--beam-size", type=int, default=8)
    ap.add_argument("--noise-level", type=float, default=0.1)
    ap.add_argument("--scoring-mode", choices=("legacy", "enhanced", "swap_v2"), default="enhanced")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    seeds = _parse_seeds(args.seeds)

    baseline_doc = json.loads(BASELINE.read_text(encoding="utf-8"))
    base_mixed_p95 = float(baseline_doc["results"]["mixed"]["p95_latency_ms_per_sample"])
    base_swap_p95 = float(baseline_doc["results"]["swap_typo"]["p95_latency_ms_per_sample"])
    baseline = {
        "mixed_exact": float(baseline_doc["results"]["mixed"]["avg_exact_restore_rate"]),
        "mixed_recovery": float(baseline_doc["results"]["mixed"]["avg_recovery_rate"]),
        "swap_typo_exact": float(baseline_doc["results"]["swap_typo"]["avg_exact_restore_rate"]),
        "swap_typo_recovery": float(baseline_doc["results"]["swap_typo"]["avg_recovery_rate"]),
        "mixed_p95_latency_ms_per_sample": base_mixed_p95,
        "swap_typo_p95_latency_ms_per_sample": base_swap_p95,
    }

    mixed = _run_mode(
        seeds=seeds,
        samples=args.samples,
        beam_size=args.beam_size,
        noise_level=args.noise_level,
        scoring_mode=args.scoring_mode,
        mode=None,
    )
    swap_typo = _run_mode(
        seeds=seeds,
        samples=args.samples,
        beam_size=args.beam_size,
        noise_level=args.noise_level,
        scoring_mode=args.scoring_mode,
        mode="swap_typo",
    )

    delta = {
        "mixed_exact_delta": mixed["avg_exact_restore_rate"] - baseline["mixed_exact"],
        "mixed_recovery_delta": mixed["avg_recovery_rate"] - baseline["mixed_recovery"],
        "swap_typo_exact_delta": swap_typo["avg_exact_restore_rate"] - baseline["swap_typo_exact"],
        "swap_typo_recovery_delta": swap_typo["avg_recovery_rate"] - baseline["swap_typo_recovery"],
        "mixed_p95_latency_delta_ms": mixed["p95_latency_ms_per_sample"] - baseline["mixed_p95_latency_ms_per_sample"],
        "swap_typo_p95_latency_delta_ms": swap_typo["p95_latency_ms_per_sample"]
        - baseline["swap_typo_p95_latency_ms_per_sample"],
    }

    thresholds = {
        "swap_typo_uplift_min": 0.02,
        "mixed_non_regression_floor": -0.005,
        "latency_p95_delta_max_ms": 2.0,
    }
    checks = {
        "swap_typo_exact_uplift_ok": delta["swap_typo_exact_delta"] >= thresholds["swap_typo_uplift_min"],
        "swap_typo_recovery_uplift_ok": delta["swap_typo_recovery_delta"] >= thresholds["swap_typo_uplift_min"],
        "mixed_non_regression_ok": delta["mixed_exact_delta"] >= thresholds["mixed_non_regression_floor"]
        and delta["mixed_recovery_delta"] >= thresholds["mixed_non_regression_floor"],
        "mixed_latency_p95_ok": delta["mixed_p95_latency_delta_ms"] <= thresholds["latency_p95_delta_max_ms"],
        "swap_typo_latency_p95_ok": delta["swap_typo_p95_latency_delta_ms"] <= thresholds["latency_p95_delta_max_ms"],
    }
    all_ok = all(checks.values())

    out_doc = {
        "schema": "l1_inverse_decoder_swap_typo_mode_router_decoder_v1_longsample_gate_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "inputs": {
            "seeds": seeds,
            "samples": args.samples,
            "beam_size": args.beam_size,
            "noise_level": args.noise_level,
            "scoring_mode": args.scoring_mode,
            "candidate": "swap_typo_mode_router_decoder_v1",
        },
        "results": {
            "mixed": mixed,
            "swap_typo": swap_typo,
        },
        "baseline_reference": {
            "artifact": str(BASELINE),
            **baseline,
        },
        "delta_vs_baseline": delta,
        "thresholds": thresholds,
        "checks": checks,
        "gate": {
            "all_ok": all_ok,
            "decision": "GO_CANDIDATE_FOR_CANARY" if all_ok else "HOLD_LATENCY_OR_STABILITY",
        },
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "gate": out_doc["gate"], "checks": checks}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
