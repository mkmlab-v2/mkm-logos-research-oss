# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.9, K:0.5, M:0.3}
# Balance: 87
# Purpose: Train and evaluate a lightweight swap_typo reranker.
# Keywords: reranker, swap_typo, spike, evaluation
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
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
    _levenshtein,
    _noisify,
    _repair_tokens_with_vocab,
    _swap_distance_noisy_then_repaired,
)

ART = ROOT / "docs" / "final" / "artifacts"
DATASET_OUT = ART / "l1_swap_typo_reranker_v1_dataset_summary.json"
AB_OUT = ART / "l1_swap_typo_reranker_v1_ab_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_seeds(raw: str) -> list[int]:
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def _features_for_candidate(
    cand_tokens: list[str],
    noisy_tokens: list[str],
    repaired_ref: list[str],
    literal_channel: dict[int, str],
    observed_vec,
) -> dict[str, float]:
    lit = float(
        sum(1 for idx, tok in literal_channel.items() if idx >= len(cand_tokens) or cand_tokens[idx] != tok)
    )
    rep_edit = 0.0
    for i in range(max(len(cand_tokens), len(repaired_ref))):
        a = repaired_ref[i] if i < len(repaired_ref) else ""
        b = cand_tokens[i] if i < len(cand_tokens) else ""
        rep_edit += float(_levenshtein(a, b))
    max_swap = max(1.0, (len(cand_tokens) * (len(cand_tokens) - 1)) / 2.0)
    swap_dist = float(_swap_distance_noisy_then_repaired(noisy_tokens, repaired_ref, cand_tokens))
    cos_rep = float(_cos(_encode(repaired_ref), _encode(cand_tokens)))
    cos_obs = float(_cos(observed_vec, _encode(cand_tokens)))
    return {
        "literal_mismatch": lit,
        "norm_repaired_edit": rep_edit / max(1.0, float(len(cand_tokens))),
        "norm_swap_dist": swap_dist / max_swap,
        "cos_repaired": cos_rep,
        "cos_observed": cos_obs,
    }


def _sample_rows(
    seeds: list[int],
    samples: int,
    beam_size: int,
    noise_level: float,
    scoring_mode: str,
    forced_mode: str | None = "swap_typo",
) -> list[dict]:
    corpus = _build_corpus()
    pos_vocab = _build_position_vocab(corpus)
    rows: list[dict] = []
    for seed in seeds:
        rng = random.Random(seed)
        for _ in range(samples):
            src = corpus[rng.randrange(len(corpus))]
            src_tokens = src.split()
            literal_channel = _extract_literal_channel(src_tokens)
            noisy, _ = _noisify(src, rng, noise_level, forced_mode=forced_mode)
            noisy_tokens = noisy.split()
            observed = _encode(noisy_tokens)
            literal_corrupted = any(
                idx < len(noisy_tokens) and ("X" in noisy_tokens[idx] or noisy_tokens[idx] == "OOV_TOKEN")
                for idx in literal_channel.keys()
            )
            cands = _beam_candidates(
                noisy,
                corpus,
                beam_size,
                rng,
                scoring_mode=scoring_mode,
                literal_channel=literal_channel,
                enforce_literal_lock=not literal_corrupted,
            )
            repaired_ref = _repair_tokens_with_vocab(noisy_tokens, pos_vocab)
            for c in cands:
                ct = c.split()
                restored = _apply_literal_channel(ct, literal_channel)
                rows.append(
                    {
                        "seed": seed,
                        "source": src,
                        "noisy": noisy,
                        "candidate": c,
                        "is_exact": int(" ".join(restored) == src),
                        **_features_for_candidate(ct, noisy_tokens, repaired_ref, literal_channel, observed),
                    }
                )
    return rows


def _pick_with_weights(cands: list[dict], w: dict[str, float]) -> dict:
    best = None
    best_score = None
    for row in cands:
        score = (
            w["w_lit"] * row["literal_mismatch"]
            + w["w_edit"] * row["norm_repaired_edit"]
            + w["w_swap"] * row["norm_swap_dist"]
            - w["w_cos_rep"] * row["cos_repaired"]
            - w["w_cos_obs"] * row["cos_observed"]
        )
        if best_score is None or score < best_score:
            best_score = score
            best = row
    return best if best is not None else cands[0]


def _exact_rate_by_group(rows: list[dict], w: dict[str, float]) -> float:
    by_group: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        key = (r["source"], r["noisy"])
        by_group.setdefault(key, []).append(r)
    if not by_group:
        return 0.0
    hits = 0
    for grp in by_group.values():
        pick = _pick_with_weights(grp, w)
        hits += int(pick["is_exact"] == 1)
    return hits / len(by_group)


def _fit_weights(train_rows: list[dict]) -> dict[str, float]:
    grid = {
        "w_lit": [8.0, 10.0, 12.0],
        "w_edit": [1.5, 2.0, 2.5],
        "w_swap": [0.6, 0.9, 1.2],
        "w_cos_rep": [0.6, 0.9, 1.2],
        "w_cos_obs": [0.2, 0.4, 0.6],
    }
    keys = list(grid.keys())
    best_w = None
    best_score = None
    for vals in itertools.product(*(grid[k] for k in keys)):
        w = {k: float(v) for k, v in zip(keys, vals)}
        score = _exact_rate_by_group(train_rows, w)
        if best_score is None or score > best_score:
            best_score = score
            best_w = w
    return best_w if best_w is not None else {"w_lit": 10.0, "w_edit": 2.0, "w_swap": 1.0, "w_cos_rep": 1.0, "w_cos_obs": 0.4}


def _run_eval(
    seeds: list[int],
    samples: int,
    beam_size: int,
    noise_level: float,
    scoring_mode: str,
    weights: dict[str, float],
    mode: str | None,
) -> dict[str, float]:
    rows = _sample_rows(
        seeds=seeds,
        samples=samples,
        beam_size=beam_size,
        noise_level=noise_level,
        scoring_mode=scoring_mode,
        forced_mode=mode,
    )
    by_group: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        by_group.setdefault((r["source"], r["noisy"]), []).append(r)
    exact = 0
    recovery = 0
    for grp in by_group.values():
        pick = _pick_with_weights(grp, weights)
        src_tokens = pick["source"].split()
        cand_tokens = pick["candidate"].split()
        lit = _extract_literal_channel(src_tokens)
        restored_tokens = _apply_literal_channel(cand_tokens, lit)
        exact += int(" ".join(restored_tokens) == pick["source"])
        recovery += int(_cos(_encode(src_tokens), _encode(restored_tokens)) > 0.95)
    rate = (exact / len(by_group)) if by_group else 0.0
    rec_rate = (recovery / len(by_group)) if by_group else 0.0
    return {
        "sample_count": float(len(by_group)),
        "exact_restore_rate": float(rate),
        "recovery_rate": float(rec_rate),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train-seeds", type=str, default="701,809,907")
    ap.add_argument("--eval-seeds", type=str, default="1009,1103")
    ap.add_argument("--samples", type=int, default=180)
    ap.add_argument("--beam-size", type=int, default=8)
    ap.add_argument("--noise-level", type=float, default=0.1)
    ap.add_argument("--scoring-mode", choices=("legacy", "enhanced", "swap_v2"), default="enhanced")
    args = ap.parse_args()

    train_seeds = _parse_seeds(args.train_seeds)
    eval_seeds = _parse_seeds(args.eval_seeds)

    train_rows = _sample_rows(
        seeds=train_seeds,
        samples=args.samples,
        beam_size=args.beam_size,
        noise_level=args.noise_level,
        scoring_mode=args.scoring_mode,
        forced_mode="swap_typo",
    )
    weights = _fit_weights(train_rows)
    train_exact = _exact_rate_by_group(train_rows, weights)

    ds_doc = {
        "schema": "l1_swap_typo_reranker_v1_dataset_summary",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "inputs": {
            "train_seeds": train_seeds,
            "samples_per_seed": args.samples,
            "beam_size": args.beam_size,
            "noise_level": args.noise_level,
            "scoring_mode": args.scoring_mode,
        },
        "dataset_rows": len(train_rows),
        "group_count": len({(r["source"], r["noisy"]) for r in train_rows}),
        "fitted_weights": weights,
        "train_exact_restore_rate": train_exact,
    }
    DATASET_OUT.write_text(json.dumps(ds_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    mixed_eval = _run_eval(
        seeds=eval_seeds,
        samples=args.samples,
        beam_size=args.beam_size,
        noise_level=args.noise_level,
        scoring_mode=args.scoring_mode,
        weights=weights,
        mode=None,
    )
    swap_typo_eval = _run_eval(
        seeds=eval_seeds,
        samples=args.samples,
        beam_size=args.beam_size,
        noise_level=args.noise_level,
        scoring_mode=args.scoring_mode,
        weights=weights,
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
    ab_doc = {
        "schema": "l1_swap_typo_reranker_v1_ab",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "inputs": {
            "train_seeds": train_seeds,
            "eval_seeds": eval_seeds,
            "samples_per_seed": args.samples,
            "beam_size": args.beam_size,
            "noise_level": args.noise_level,
            "scoring_mode": args.scoring_mode,
        },
        "candidate": "swap_typo_reranker_v1_weighted_linear",
        "fitted_weights": weights,
        "results": {"mixed": mixed_eval, "swap_typo": swap_typo_eval},
        "baseline_reference": baseline,
        "delta_vs_baseline": delta,
        "gate": {"checks": checks, "all_ok": all(checks.values()), "decision": "GO_RERANKER_V1" if all(checks.values()) else "HOLD_V4"},
    }
    AB_OUT.write_text(json.dumps(ab_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "dataset_out": str(DATASET_OUT), "ab_out": str(AB_OUT), "gate": ab_doc["gate"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
