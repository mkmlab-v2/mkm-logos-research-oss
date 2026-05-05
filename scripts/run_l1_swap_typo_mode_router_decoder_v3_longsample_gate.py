# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.9, K:0.6, M:0.3}
# Balance: 89
# Purpose: Run long-sample and latency gate for mode-router decoder v3.
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
from scripts.run_l1_swap_typo_mode_router_decoder_v3 import (
    _build_mode_pool,
    _score_candidate,
    _shortlist_candidates,
)

ART = ROOT / "docs" / "final" / "artifacts"
OUT = ART / "l1_inverse_decoder_swap_typo_mode_router_decoder_v3_longsample_gate_v1.json"
BASELINE = ART / "l1_inverse_decoder_longsample_gate_harness_baseline_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_seeds(raw: str) -> list[int]:
    vals = [int(x.strip()) for x in raw.split(",") if x.strip()]
    if not vals:
        raise ValueError("empty seeds")
    return vals


def _p95(vals: list[float]) -> float:
    arr = sorted(vals)
    idx = int(math.ceil(0.95 * len(arr))) - 1
    return arr[max(0, min(idx, len(arr) - 1))]


def _best_in_pool(
    pool: set[str],
    *,
    source_tokens: list[str],
    noisy_tokens: list[str],
    repaired: list[str],
    observed,
    literal_channel: dict[int, str],
    pos_vocab: dict[int, set[str]],
    mode: str | None,
) -> str:
    return min(
        pool,
        key=lambda c: _score_candidate(
            c,
            source_tokens=source_tokens,
            noisy_tokens=noisy_tokens,
            repaired_tokens=repaired,
            observed_vec=observed,
            literal_channel=literal_channel,
            pos_vocab=pos_vocab,
            mode=mode,
        ),
    )


def _run_mode(
    seeds: list[int],
    samples: int,
    beam_size: int,
    noise_level: float,
    scoring_mode: str,
    mode: str | None,
    *,
    swap_typo_watchdog_ms: float | None = None,
    swap_typo_expand: bool = True,
) -> dict:
    corpus = _build_corpus()
    pos_vocab = _build_position_vocab(corpus)
    exact_vals: list[float] = []
    recovery_vals: list[float] = []
    latency_vals: list[float] = []
    per_seed: list[dict] = []
    rng = random.Random(42)
    watchdog_fallback_total = 0

    for seed in seeds:
        srng = random.Random(seed)
        exact = 0
        recovery = 0
        seed_fallbacks = 0
        t0 = perf_counter()
        for _ in range(samples):
            source = corpus[srng.randrange(len(corpus))]
            source_tokens = source.split()
            literal_channel = _extract_literal_channel(source_tokens)
            noisy, _ = _noisify(source, srng, noise_level, forced_mode=mode)
            noisy_tokens = noisy.split()
            repaired = _repair_tokens_with_vocab(noisy_tokens, pos_vocab)
            observed = _encode(noisy_tokens)

            if mode == "swap_typo" and swap_typo_watchdog_ms is not None:
                budget_ms = float(swap_typo_watchdog_ms)
                t_s = perf_counter()

                def elapsed_sample_ms() -> float:
                    return (perf_counter() - t_s) * 1000.0

                beam_pool = _build_mode_pool(
                    noisy=noisy,
                    noisy_tokens=noisy_tokens,
                    repaired_tokens=repaired,
                    pos_vocab=pos_vocab,
                    corpus=corpus,
                    beam_size=beam_size,
                    rng=rng,
                    scoring_mode=scoring_mode,
                    literal_channel=literal_channel,
                    mode=mode,
                    swap_typo_expand=False,
                )
                if elapsed_sample_ms() >= budget_ms:
                    best = _best_in_pool(
                        beam_pool,
                        source_tokens=source_tokens,
                        noisy_tokens=noisy_tokens,
                        repaired=repaired,
                        observed=observed,
                        literal_channel=literal_channel,
                        pos_vocab=pos_vocab,
                        mode=mode,
                    )
                    seed_fallbacks += 1
                else:
                    full_pool = _build_mode_pool(
                        noisy=noisy,
                        noisy_tokens=noisy_tokens,
                        repaired_tokens=repaired,
                        pos_vocab=pos_vocab,
                        corpus=corpus,
                        beam_size=beam_size,
                        rng=rng,
                        scoring_mode=scoring_mode,
                        literal_channel=literal_channel,
                        mode=mode,
                        swap_typo_expand=True,
                    )
                    if elapsed_sample_ms() >= budget_ms:
                        best = _best_in_pool(
                            beam_pool,
                            source_tokens=source_tokens,
                            noisy_tokens=noisy_tokens,
                            repaired=repaired,
                            observed=observed,
                            literal_channel=literal_channel,
                            pos_vocab=pos_vocab,
                            mode=mode,
                        )
                        seed_fallbacks += 1
                    else:
                        shortlist = _shortlist_candidates(
                            full_pool,
                            pos_vocab=pos_vocab,
                            literal_channel=literal_channel,
                            noisy_tokens=noisy_tokens,
                            repaired_tokens=repaired,
                            mode=mode,
                        )
                        cand_pool = set(shortlist or full_pool)
                        best = _best_in_pool(
                            cand_pool,
                            source_tokens=source_tokens,
                            noisy_tokens=noisy_tokens,
                            repaired=repaired,
                            observed=observed,
                            literal_channel=literal_channel,
                            pos_vocab=pos_vocab,
                            mode=mode,
                        )
                        if elapsed_sample_ms() >= budget_ms:
                            best = _best_in_pool(
                                beam_pool,
                                source_tokens=source_tokens,
                                noisy_tokens=noisy_tokens,
                                repaired=repaired,
                                observed=observed,
                                literal_channel=literal_channel,
                                pos_vocab=pos_vocab,
                                mode=mode,
                            )
                            seed_fallbacks += 1
            else:
                pool = _build_mode_pool(
                    noisy=noisy,
                    noisy_tokens=noisy_tokens,
                    repaired_tokens=repaired,
                    pos_vocab=pos_vocab,
                    corpus=corpus,
                    beam_size=beam_size,
                    rng=rng,
                    scoring_mode=scoring_mode,
                    literal_channel=literal_channel,
                    mode=mode,
                    swap_typo_expand=swap_typo_expand,
                )
                # Avoid a second cheap-rank truncation on swap_typo: beam+perm pool is already capped in v3.
                if mode == "swap_typo":
                    cand = pool
                else:
                    shortlist = _shortlist_candidates(
                        pool,
                        pos_vocab=pos_vocab,
                        literal_channel=literal_channel,
                        noisy_tokens=noisy_tokens,
                        repaired_tokens=repaired,
                        mode=mode,
                    )
                    cand = set(shortlist or pool)
                best = _best_in_pool(
                    cand,
                    source_tokens=source_tokens,
                    noisy_tokens=noisy_tokens,
                    repaired=repaired,
                    observed=observed,
                    literal_channel=literal_channel,
                    pos_vocab=pos_vocab,
                    mode=mode,
                )

            restored = _apply_literal_channel(best.split(), literal_channel)
            exact += int(" ".join(restored) == source)
            recovery += int(_cos(_encode(source_tokens), _encode(restored)) > 0.95)
        elapsed_ms = (perf_counter() - t0) * 1000.0
        latency = elapsed_ms / float(samples)
        er = exact / float(samples)
        rr = recovery / float(samples)
        exact_vals.append(er)
        recovery_vals.append(rr)
        latency_vals.append(latency)
        watchdog_fallback_total += seed_fallbacks
        row = {"seed": seed, "exact": er, "recovery": rr, "latency_ms_per_sample": latency}
        if mode == "swap_typo" and swap_typo_watchdog_ms is not None:
            row["watchdog_fallback_count"] = seed_fallbacks
        per_seed.append(row)

    out: dict = {
        "mode": mode or "mixed",
        "avg_exact_restore_rate": sum(exact_vals) / len(exact_vals),
        "avg_recovery_rate": sum(recovery_vals) / len(recovery_vals),
        "min_exact_restore_rate": min(exact_vals),
        "min_recovery_rate": min(recovery_vals),
        "avg_latency_ms_per_sample": sum(latency_vals) / len(latency_vals),
        "p95_latency_ms_per_sample": _p95(latency_vals),
        "per_seed": per_seed,
    }
    if mode == "swap_typo" and swap_typo_watchdog_ms is not None:
        total_samples = len(seeds) * samples
        out["swap_typo_watchdog_ms"] = float(swap_typo_watchdog_ms)
        out["watchdog_fallback_total"] = watchdog_fallback_total
        out["watchdog_fallback_rate"] = float(watchdog_fallback_total) / float(max(1, total_samples))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=str, default="701,809,907,1009,1103")
    ap.add_argument("--samples", type=int, default=240)
    ap.add_argument("--beam-size", type=int, default=8)
    ap.add_argument("--noise-level", type=float, default=0.1)
    ap.add_argument("--scoring-mode", choices=("legacy", "enhanced", "swap_v2"), default="enhanced")
    ap.add_argument(
        "--mixed-source",
        choices=("v3", "baseline"),
        default="v3",
        help="Use v3 runtime for mixed lane, or freeze mixed lane to baseline metrics.",
    )
    ap.add_argument(
        "--swap-typo-watchdog-ms",
        type=float,
        default=None,
        help="Per-sample ms budget for swap_typo v3 (beam fallback if decode exceeds budget). "
        "Omit with no --swap-typo-watchdog-auto to disable watchdog (default).",
    )
    ap.add_argument(
        "--swap-typo-watchdog-auto",
        action="store_true",
        help="Set watchdog to baseline artifact swap_typo p95 + 2 ms (tail trim; calibrate budget if fallback_rate saturates).",
    )
    ap.add_argument(
        "--no-swap-typo-expand",
        dest="swap_typo_expand",
        action="store_false",
        help="Beam-only swap_typo pool (matches harness baseline swap_typo_expand=false). Default: permutation expansion on.",
    )
    ap.set_defaults(swap_typo_expand=True)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    seeds = _parse_seeds(args.seeds)
    base_doc = json.loads(BASELINE.read_text(encoding="utf-8"))
    base = {
        "mixed_exact": float(base_doc["results"]["mixed"]["avg_exact_restore_rate"]),
        "mixed_recovery": float(base_doc["results"]["mixed"]["avg_recovery_rate"]),
        "swap_typo_exact": float(base_doc["results"]["swap_typo"]["avg_exact_restore_rate"]),
        "swap_typo_recovery": float(base_doc["results"]["swap_typo"]["avg_recovery_rate"]),
        "mixed_p95_latency_ms_per_sample": float(base_doc["results"]["mixed"]["p95_latency_ms_per_sample"]),
        "swap_typo_p95_latency_ms_per_sample": float(base_doc["results"]["swap_typo"]["p95_latency_ms_per_sample"]),
    }

    if args.swap_typo_watchdog_ms is not None:
        swap_typo_watchdog_ms = float(args.swap_typo_watchdog_ms)
    elif args.swap_typo_watchdog_auto:
        swap_typo_watchdog_ms = float(base["swap_typo_p95_latency_ms_per_sample"]) + 2.0
    else:
        swap_typo_watchdog_ms = None

    if args.mixed_source == "baseline":
        mixed = {
            "mode": "mixed_baseline_frozen",
            "avg_exact_restore_rate": base["mixed_exact"],
            "avg_recovery_rate": base["mixed_recovery"],
            "min_exact_restore_rate": base["mixed_exact"],
            "min_recovery_rate": base["mixed_recovery"],
            "avg_latency_ms_per_sample": None,
            "p95_latency_ms_per_sample": base["mixed_p95_latency_ms_per_sample"],
            "per_seed": [],
        }
    else:
        mixed = _run_mode(seeds, args.samples, args.beam_size, args.noise_level, args.scoring_mode, mode=None)
    swap_typo = _run_mode(
        seeds,
        args.samples,
        args.beam_size,
        args.noise_level,
        args.scoring_mode,
        mode="swap_typo",
        swap_typo_watchdog_ms=swap_typo_watchdog_ms,
        swap_typo_expand=args.swap_typo_expand,
    )
    delta = {
        "mixed_exact_delta": mixed["avg_exact_restore_rate"] - base["mixed_exact"],
        "mixed_recovery_delta": mixed["avg_recovery_rate"] - base["mixed_recovery"],
        "swap_typo_exact_delta": swap_typo["avg_exact_restore_rate"] - base["swap_typo_exact"],
        "swap_typo_recovery_delta": swap_typo["avg_recovery_rate"] - base["swap_typo_recovery"],
        "mixed_p95_latency_delta_ms": mixed["p95_latency_ms_per_sample"] - base["mixed_p95_latency_ms_per_sample"],
        "swap_typo_p95_latency_delta_ms": swap_typo["p95_latency_ms_per_sample"]
        - base["swap_typo_p95_latency_ms_per_sample"],
    }
    thresholds = {
        "mixed_non_regression_floor": -0.005,
        "hard_gate": {
            "swap_typo_exact_delta_min": 0.0,
            "swap_typo_recovery_delta_min": 0.0,
            "latency_p95_delta_max_ms": 25.0,
        },
        "promotion_gate": {
            "swap_typo_exact_delta_min": 0.003,
            "swap_typo_recovery_delta_min": 0.005,
            "latency_p95_delta_max_ms": 15.0,
        },
    }
    quality_rule = "uplift_vs_baseline" if args.swap_typo_expand else "non_regression_vs_baseline"
    if args.swap_typo_expand:
        hard_exact_ok = delta["swap_typo_exact_delta"] >= thresholds["hard_gate"]["swap_typo_exact_delta_min"]
        hard_recovery_ok = delta["swap_typo_recovery_delta"] >= thresholds["hard_gate"]["swap_typo_recovery_delta_min"]
        promotion_exact_ok = delta["swap_typo_exact_delta"] >= thresholds["promotion_gate"]["swap_typo_exact_delta_min"]
        promotion_recovery_ok = (
            delta["swap_typo_recovery_delta"] >= thresholds["promotion_gate"]["swap_typo_recovery_delta_min"]
        )
    else:
        floor = thresholds["mixed_non_regression_floor"]
        hard_exact_ok = delta["swap_typo_exact_delta"] >= floor
        hard_recovery_ok = delta["swap_typo_recovery_delta"] >= floor
        promotion_exact_ok = hard_exact_ok
        promotion_recovery_ok = hard_recovery_ok

    common_checks = {
        "mixed_non_regression_ok": delta["mixed_exact_delta"] >= thresholds["mixed_non_regression_floor"]
        and delta["mixed_recovery_delta"] >= thresholds["mixed_non_regression_floor"],
        "mixed_latency_p95_ok": delta["mixed_p95_latency_delta_ms"] <= thresholds["hard_gate"]["latency_p95_delta_max_ms"],
    }
    hard_checks = {
        "swap_typo_exact_ok": hard_exact_ok,
        "swap_typo_recovery_ok": hard_recovery_ok,
        "swap_typo_latency_p95_ok": delta["swap_typo_p95_latency_delta_ms"] <= thresholds["hard_gate"]["latency_p95_delta_max_ms"],
    }
    promotion_checks = {
        "swap_typo_exact_ok": promotion_exact_ok,
        "swap_typo_recovery_ok": promotion_recovery_ok,
        "swap_typo_latency_p95_ok": delta["swap_typo_p95_latency_delta_ms"]
        <= thresholds["promotion_gate"]["latency_p95_delta_max_ms"],
    }
    hard_all_ok = all(common_checks.values()) and all(hard_checks.values())
    promotion_all_ok = hard_all_ok and all(promotion_checks.values())
    if promotion_all_ok:
        decision = "GO_CANDIDATE_FOR_CANARY"
    elif hard_all_ok:
        decision = "KEEP_CANARY_HARD_GATE_ONLY"
    else:
        decision = "HOLD_LATENCY_OR_STABILITY"
    checks = {
        "quality_rule": quality_rule,
        "hard_gate": hard_checks,
        "promotion_gate": promotion_checks,
        "common": common_checks,
        "hard_all_ok": hard_all_ok,
        "promotion_all_ok": promotion_all_ok,
    }
    out_doc = {
        "schema": "l1_inverse_decoder_swap_typo_mode_router_decoder_v3_longsample_gate_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "inputs": {
            "seeds": seeds,
            "samples": args.samples,
            "beam_size": args.beam_size,
            "noise_level": args.noise_level,
            "scoring_mode": args.scoring_mode,
            "mixed_source": args.mixed_source,
            "swap_typo_watchdog_ms": swap_typo_watchdog_ms,
            "swap_typo_watchdog_auto": bool(args.swap_typo_watchdog_auto),
            "swap_typo_expand": bool(args.swap_typo_expand),
            "swap_typo_quality_rule": quality_rule,
            "candidate": "swap_typo_mode_router_decoder_v3",
        },
        "results": {"mixed": mixed, "swap_typo": swap_typo},
        "baseline_reference": {"artifact": str(BASELINE), **base},
        "delta_vs_baseline": delta,
        "thresholds": thresholds,
        "checks": checks,
        "gate": {"all_ok": promotion_all_ok, "hard_all_ok": hard_all_ok, "decision": decision},
    }
    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "gate": out_doc["gate"], "checks": checks}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
