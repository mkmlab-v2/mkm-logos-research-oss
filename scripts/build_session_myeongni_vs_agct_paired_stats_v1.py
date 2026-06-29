#!/usr/bin/env python3
"""Paired significance for AGCT vs session hybrid KOSPI (252d), B-track [HYPO].

McNemar on discordant days + bootstrap CI for hit-rate delta. Not Track A / live promotion.
"""
from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from math import comb
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/session_myeongni_vs_agct_paired_stats_v1_latest.json"
ARTIFACT_OUT = ROOT / "docs/final/artifacts/session_myeongni_vs_agct_paired_stats_v1_latest.json"

AGCT_SCORE = ROOT / "reports/btrack_prophecy_score_agct_market_psych_252d.json"
HYB_SCORE = ROOT / "reports/btrack_prophecy_score_hybrid_session_kospi_252d_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _paired_rows() -> tuple[list[bool], list[bool], dict[str, Any]]:
    if not AGCT_SCORE.is_file() or not HYB_SCORE.is_file():
        raise SystemExit(f"missing score JSON: agct={AGCT_SCORE.is_file()} hybrid={HYB_SCORE.is_file()}")

    def _map(path: Path) -> dict[str, bool]:
        sc = json.loads(path.read_text(encoding="utf-8"))
        return {
            str(r.get("eval_date")): str(r.get("predicted_direction") or "")
            == str(r.get("actual_direction") or "")
            for r in sc.get("rows") or []
            if r.get("instrument") == "kospi"
        }

    agct = _map(AGCT_SCORE)
    hyb = _map(HYB_SCORE)
    keys = sorted(set(agct) & set(hyb))
    if not keys:
        raise SystemExit("no overlapping KOSPI eval_date keys")
    a_hits = [agct[k] for k in keys]
    h_hits = [hyb[k] for k in keys]
    n = len(keys)
    agct_only = hybrid_only = both_ok = 0
    for ah, hh in zip(a_hits, h_hits):
        if ah and hh:
            both_ok += 1
        elif ah and not hh:
            agct_only += 1
        elif hh and not ah:
            hybrid_only += 1
    summary = {
        "n_paired_days": n,
        "agct_hit_rate": round(sum(a_hits) / n, 6),
        "hybrid_kospi_leg_hit_rate": round(sum(h_hits) / n, 6),
        "delta_pp_agct_minus_hybrid": round((sum(a_hits) - sum(h_hits)) / n * 100, 2),
        "days_agct_only_correct": agct_only,
        "days_hybrid_only_correct": hybrid_only,
        "days_both_correct": both_ok,
        "days_both_wrong": n - agct_only - hybrid_only - both_ok,
        "note_ko": "동일 eval_date·KOSPI만. BTC bear leg 제외.",
    }
    return a_hits, h_hits, summary


def _binom_cdf(k: int, n: int, p: float = 0.5) -> float:
    return sum(comb(n, i) * (p**i) * ((1 - p) ** (n - i)) for i in range(0, k + 1))


def _mcnemar_exact(b: int, c: int) -> dict[str, Any]:
    """b=AGCT correct & hybrid wrong; c=hybrid correct & AGCT wrong."""
    n_disc = b + c
    if n_disc == 0:
        return {
            "discordant_agct_only": b,
            "discordant_hybrid_only": c,
            "p_value_two_sided": None,
            "method": "none",
            "significant_alpha_0_05": False,
        }
    # two-sided exact binomial on discordant count
    p_lower = _binom_cdf(min(b, c), n_disc, 0.5)
    p_upper = 1.0 - _binom_cdf(max(b, c) - 1, n_disc, 0.5)
    p_two = min(1.0, 2.0 * min(p_lower, p_upper))
    method = "exact_binomial"
    try:
        from scipy.stats import binomtest

        res = binomtest(b, n=n_disc, p=0.5, alternative="two-sided")
        p_two = float(res.pvalue)
        method = "scipy_binomtest"
    except ImportError:
        pass
    return {
        "discordant_agct_only": b,
        "discordant_hybrid_only": c,
        "n_discordant": n_disc,
        "p_value_two_sided": round(p_two, 6),
        "method": method,
        "significant_alpha_0_05": p_two < 0.05,
        "note_ko": "McNemar: discordant-day binomial; 방향 일치 가정 아님.",
    }


def _bootstrap_delta_pp(
    a_hits: list[bool],
    h_hits: list[bool],
    *,
    n_boot: int,
    seed: int,
) -> dict[str, Any]:
    n = len(a_hits)
    rng = random.Random(seed)
    deltas: list[float] = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        ah = sum(a_hits[i] for i in idx) / n
        hh = sum(h_hits[i] for i in idx) / n
        deltas.append((ah - hh) * 100.0)
    deltas.sort()
    lo = deltas[int(0.025 * n_boot)]
    hi = deltas[int(0.975 * n_boot)]
    point = (sum(a_hits) - sum(h_hits)) / n * 100.0
    prob_agct_better = sum(1 for d in deltas if d > 0) / n_boot
    return {
        "n_bootstrap": n_boot,
        "seed": seed,
        "delta_pp_point": round(point, 2),
        "ci_95_low_pp": round(lo, 2),
        "ci_95_high_pp": round(hi, 2),
        "prob_agct_better": round(prob_agct_better, 4),
        "ci_excludes_zero": lo > 0 or hi < 0,
    }


def build(*, n_boot: int, seed: int) -> dict[str, Any]:
    a_hits, h_hits, paired = _paired_rows()
    mcn = _mcnemar_exact(
        paired["days_agct_only_correct"],
        paired["days_hybrid_only_correct"],
    )
    boot = _bootstrap_delta_pp(a_hits, h_hits, n_boot=n_boot, seed=seed)
    sig = mcn.get("significant_alpha_0_05") is True
    ci_pos = boot["ci_95_low_pp"] > 0
    if sig and ci_pos:
        verdict = (
            f"252d KOSPI 페어드 n={paired['n_paired_days']}: AGCT +{paired['delta_pp_agct_minus_hybrid']}pp "
            f"(McNemar p={mcn.get('p_value_two_sided')}, bootstrap 95% CI "
            f"[{boot['ci_95_low_pp']}, {boot['ci_95_high_pp']}]pp). research_only·승격 없음."
        )
    elif ci_pos:
        verdict = (
            f"252d KOSPI: AGCT +{paired['delta_pp_agct_minus_hybrid']}pp; bootstrap CI 양수 "
            f"but McNemar p={mcn.get('p_value_two_sided')} (α=0.05 {'미달' if not sig else '통과'}). "
            "research_only."
        )
    else:
        verdict = (
            f"252d KOSPI: delta +{paired['delta_pp_agct_minus_hybrid']}pp; "
            "bootstrap CI가 0을 포함할 수 있음. research_only."
        )
    return {
        "schema": "session_myeongni_vs_agct_paired_stats_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "not_promoted_track_a": True,
        "inputs": {
            "agct_score_json": str(AGCT_SCORE.relative_to(ROOT)).replace("\\", "/"),
            "hybrid_score_json": str(HYB_SCORE.relative_to(ROOT)).replace("\\", "/"),
        },
        "paired_kospi_252d": paired,
        "mcnemar": mcn,
        "bootstrap_delta_hit_rate_pp": boot,
        "verdict_ko": verdict,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-bootstrap", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--also-artifact", action="store_true")
    args = ap.parse_args()
    doc = build(n_boot=args.n_bootstrap, seed=args.seed)
    DEFAULT_OUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(DEFAULT_OUT)
    if args.also_artifact:
        ARTIFACT_OUT.parent.mkdir(parents=True, exist_ok=True)
        ARTIFACT_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(ARTIFACT_OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
