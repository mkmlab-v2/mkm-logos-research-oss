# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.9, K:0.6, M:0.3}
# Balance: 88
# Purpose: Evaluate order-focused lane decoder for order_only_mismatch bucket.
# Keywords: swap_typo, order-lane, candidate-generation, ab-test
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_l1_inverse_decoder_spike_test import (
    _apply_literal_channel,
    _beam_candidates,
    _build_corpus,
    _build_position_vocab,
    _cos,
    _encode,
    _extract_literal_channel,
    _generate_adjacent_transposition_candidates,
    _levenshtein,
    _noisify,
    _repair_tokens_with_vocab,
    _swap_distance_noisy_then_repaired,
)

ART = ROOT / "docs" / "final" / "artifacts"
PREREG_OUT = ART / "l1_inverse_decoder_swap_typo_order_lane_decoder_v1_preregister.json"
AB_OUT = ART / "l1_inverse_decoder_swap_typo_order_lane_decoder_v1_ab_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_seeds(raw: str) -> list[int]:
    vals = [int(x.strip()) for x in raw.split(",") if x.strip()]
    if not vals:
        raise ValueError("empty seed list")
    return vals


def _lane_pool(
    noisy: str,
    repaired_tokens: list[str],
    corpus: list[str],
    beam_size: int,
    rng: random.Random,
    scoring_mode: str,
    literal_channel: dict[int, str],
    mode: str | None,
) -> set[str]:
    baseline = _beam_candidates(
        noisy,
        corpus,
        beam_size,
        rng,
        scoring_mode=scoring_mode,
        literal_channel=literal_channel,
        enforce_literal_lock=False,
    )
    # D24: aggressively widen order lane only; target order_only_mismatch bucket.
    order_lane = _generate_adjacent_transposition_candidates(
        repaired_tokens,
        max_steps=5 if mode == "swap_typo" else 3,
    )
    return set(baseline) | order_lane


def _score_candidate(
    candidate: str,
    source_tokens: list[str],
    noisy_tokens: list[str],
    repaired_tokens: list[str],
    observed_vec,
    literal_channel: dict[int, str],
    mode: str | None,
) -> float:
    cand_tokens = candidate.split()
    restored = _apply_literal_channel(cand_tokens, literal_channel)
    lit_mismatch = float(
        sum(1 for idx, tok in literal_channel.items() if idx >= len(restored) or restored[idx] != tok)
    )
    swap_dist = float(_swap_distance_noisy_then_repaired(noisy_tokens, repaired_tokens, restored))
    edit_sum = 0.0
    for i in range(max(len(restored), len(repaired_tokens))):
        a = repaired_tokens[i] if i < len(repaired_tokens) else ""
        b = restored[i] if i < len(restored) else ""
        edit_sum += float(_levenshtein(a, b))
    cos_obs = float(_cos(observed_vec, _encode(restored)))
    cos_src = float(_cos(_encode(source_tokens), _encode(restored)))

    if mode == "swap_typo":
        # Order bucket first: penalize swap distance heavily.
        return (14.0 * lit_mismatch) + (1.8 * swap_dist) + (1.2 * edit_sum) - (1.2 * cos_obs) - (0.8 * cos_src)
    return (12.0 * lit_mismatch) + (1.0 * swap_dist) + (1.5 * edit_sum) - (1.2 * cos_obs) - (0.6 * cos_src)


def _eval_mode(
    seeds: list[int],
    samples: int,
    beam_size: int,
    noise_level: float,
    scoring_mode: str,
    mode: str | None,
) -> dict[str, float]:
    corpus = _build_corpus()
    pos_vocab = _build_position_vocab(corpus)
    exact = 0
    recovery = 0
    n = 0
    lane_size_total = 0
    rng = random.Random(42)

    for seed in seeds:
        per_seed_rng = random.Random(seed)
        for _ in range(samples):
            source = corpus[per_seed_rng.randrange(len(corpus))]
            source_tokens = source.split()
            literal_channel = _extract_literal_channel(source_tokens)
            noisy, _ = _noisify(source, per_seed_rng, noise_level, forced_mode=mode)
            noisy_tokens = noisy.split()
            repaired_tokens = _repair_tokens_with_vocab(noisy_tokens, pos_vocab)
            observed_vec = _encode(noisy_tokens)
            lane_pool = _lane_pool(
                noisy=noisy,
                repaired_tokens=repaired_tokens,
                corpus=corpus,
                beam_size=beam_size,
                rng=rng,
                scoring_mode=scoring_mode,
                literal_channel=literal_channel,
                mode=mode,
            )
            lane_size_total += len(lane_pool)
            best = min(
                lane_pool,
                key=lambda c: _score_candidate(
                    c,
                    source_tokens=source_tokens,
                    noisy_tokens=noisy_tokens,
                    repaired_tokens=repaired_tokens,
                    observed_vec=observed_vec,
                    literal_channel=literal_channel,
                    mode=mode,
                ),
            )
            best_restored = _apply_literal_channel(best.split(), literal_channel)
            n += 1
            exact += int(" ".join(best_restored) == source)
            recovery += int(_cos(_encode(source_tokens), _encode(best_restored)) > 0.95)

    denom = max(1, n)
    return {
        "sample_count": float(n),
        "avg_lane_pool_size": float(lane_size_total) / float(denom),
        "exact_restore_rate": float(exact) / float(denom),
        "recovery_rate": float(recovery) / float(denom),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train-seeds", type=str, default="701,809")
    ap.add_argument("--eval-seeds", type=str, default="1009,1103")
    ap.add_argument("--samples", type=int, default=120)
    ap.add_argument("--beam-size", type=int, default=8)
    ap.add_argument("--noise-level", type=float, default=0.1)
    ap.add_argument("--scoring-mode", choices=("legacy", "enhanced", "swap_v2"), default="enhanced")
    args = ap.parse_args()

    train_seeds = _parse_seeds(args.train_seeds)
    eval_seeds = _parse_seeds(args.eval_seeds)

    prereg = {
        "schema": "l1_inverse_decoder_swap_typo_order_lane_decoder_v1_preregister",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "hypothesis": "Order-focused lane expansion can reduce order_only_mismatch in swap_typo mode without mixed regression.",
        "candidate": "swap_typo_order_lane_decoder_v1",
        "target_failure_bucket": "order_only_mismatch",
        "is_structural_new_path": True,
        "isolation": "order-lane candidate generation/scoring isolated from production v4 path",
        "inputs": {
            "train_seeds": train_seeds,
            "eval_seeds": eval_seeds,
            "samples_per_seed": args.samples,
            "beam_size": args.beam_size,
            "noise_level": args.noise_level,
            "scoring_mode": args.scoring_mode,
        },
        "gate": {
            "swap_typo_uplift_min": 0.02,
            "mixed_non_regression_floor": -0.005,
            "go_rule": "swap_typo exact/recovery each >= +0.02 and mixed exact/recovery each >= -0.005",
        },
    }
    PREREG_OUT.write_text(json.dumps(prereg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    mixed_eval = _eval_mode(
        seeds=eval_seeds,
        samples=args.samples,
        beam_size=args.beam_size,
        noise_level=args.noise_level,
        scoring_mode=args.scoring_mode,
        mode=None,
    )
    swap_typo_eval = _eval_mode(
        seeds=eval_seeds,
        samples=args.samples,
        beam_size=args.beam_size,
        noise_level=args.noise_level,
        scoring_mode=args.scoring_mode,
        mode="swap_typo",
    )

    baseline = {
        "mixed_exact": 0.6216666666666667,
        "mixed_recovery": 0.6391666666666667,
        "swap_typo_exact": 0.25083333333333335,
        "swap_typo_recovery": 0.2816666666666667,
    }
    delta = {
        "mixed_exact_delta": mixed_eval["exact_restore_rate"] - baseline["mixed_exact"],
        "mixed_recovery_delta": mixed_eval["recovery_rate"] - baseline["mixed_recovery"],
        "swap_typo_exact_delta": swap_typo_eval["exact_restore_rate"] - baseline["swap_typo_exact"],
        "swap_typo_recovery_delta": swap_typo_eval["recovery_rate"] - baseline["swap_typo_recovery"],
    }
    checks = {
        "swap_typo_exact_uplift_ok": delta["swap_typo_exact_delta"] >= 0.02,
        "swap_typo_recovery_uplift_ok": delta["swap_typo_recovery_delta"] >= 0.02,
        "mixed_non_regression_ok": delta["mixed_exact_delta"] >= -0.005 and delta["mixed_recovery_delta"] >= -0.005,
    }
    all_ok = all(checks.values())

    out_doc = {
        "schema": "l1_inverse_decoder_swap_typo_order_lane_decoder_v1_ab",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "candidate": "swap_typo_order_lane_decoder_v1",
        "results": {
            "mixed": mixed_eval,
            "swap_typo": swap_typo_eval,
        },
        "baseline_reference": baseline,
        "delta_vs_baseline": delta,
        "gate": {
            "checks": checks,
            "all_ok": all_ok,
            "decision": "GO_ORDER_LANE_DECODER_V1" if all_ok else "HOLD_V4",
        },
        "artifacts": {
            "preregister": str(PREREG_OUT),
        },
    }
    AB_OUT.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "preregister_out": str(PREREG_OUT),
                "ab_out": str(AB_OUT),
                "gate": out_doc["gate"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
