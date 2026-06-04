#!/usr/bin/env python3
"""[HYPO] NG-40 cap sweep (41k OFF) — find saving/Jaccard tradeoff vs frozen ACTIVE."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_nextgen_latent_indexer_eval_ng40_v1 import (  # noqa: E402
    ACTIVE,
    INPUT_V2,
    _beat,
    _frozen_active,
    _utc,
    evaluate_ng40_lane,
)

SWEEP_OUT_OFF = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_cap_sweep_v1_latest.json"
)
BEST_OUT_OFF = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_best_v1_latest.json"
)
SWEEP_OUT_ON = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_41k_on_cap_sweep_v1_latest.json"
)
BEST_OUT_ON = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_41k_on_best_v1_latest.json"
)
SWEEP_OUT_ON_FINE = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_41k_on_offbest_fine_sweep_v1_latest.json"
)
BEST_OUT_ON_FINE = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_41k_on_offbest_best_v1_latest.json"
)
SWEEP_OUT_OFF_ULTRA = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_off_best_ultra_fine_sweep_v1_latest.json"
)

# Coarse grid around frozen ACTIVE caps (0.35 / 0.30 / 0.60) and prior loose defaults.
DEFAULT_GENERAL = (0.32, 0.34, 0.35, 0.36, 0.38, 0.40, 0.48, 0.52, 0.54)
DEFAULT_SENSITIVE = (0.28, 0.30, 0.32, 0.35, 0.42, 0.48, 0.50)
DEFAULT_HANGUL = (0.44, 0.48, 0.52, 0.56, 0.60, 0.64)


def _rank_key(row: dict[str, Any], *, primary: str = "jaccard") -> tuple:
    """Higher is better: beat first, then primary axis (saving or jaccard), then tie-break."""
    agg = row.get("aggregate") or {}
    beat = row.get("beat_check") or {}
    j = float(agg.get("avg_reconstruction_fidelity_jaccard") or 0)
    s = float(agg.get("global_token_saving_rate") or 0)
    b = 1 if beat.get("beat_frozen") else 0
    if primary == "saving":
        return (b, s, j)
    return (b, j, s)


def _preset_grids(preset: str) -> tuple[tuple[float, ...], ...]:
    if preset == "active_neighborhood":
        return (
            (0.32, 0.34, 0.35, 0.36, 0.38),
            (0.28, 0.30, 0.32, 0.35),
            (0.50, 0.55, 0.60, 0.65),
        )
    if preset == "fast":
        return (
            (0.35, 0.40, 0.50, 0.54),
            (0.30, 0.40, 0.50),
            (0.48, 0.60),
        )
    if preset == "on_beat_search":
        return (
            (0.28, 0.30, 0.32, 0.34, 0.35, 0.36, 0.38),
            (0.26, 0.28, 0.30, 0.32, 0.34),
            (0.50, 0.55, 0.58, 0.60, 0.65),
        )
    if preset == "on_off_best_neighborhood":
        return (
            (0.30, 0.31, 0.32, 0.33, 0.34),
            (0.26, 0.27, 0.28, 0.29, 0.30),
            (0.50, 0.52, 0.55, 0.58, 0.60),
        )
    if preset == "on_offbest_caps_pair":
        return ((0.32,), (0.28,), (0.55,))
    if preset == "off_best_ultra_fine":
        return (
            (0.31, 0.32, 0.33),
            (0.27, 0.28, 0.29),
            (0.53, 0.54, 0.55, 0.56),
        )
    return (DEFAULT_GENERAL, DEFAULT_SENSITIVE, DEFAULT_HANGUL)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench-input", type=Path, default=INPUT_V2)
    ap.add_argument("--out-json", type=Path, default=None)
    ap.add_argument("--best-out-json", type=Path, default=None)
    ap.add_argument(
        "--lexicon-on",
        action="store_true",
        help="41k ON + ACTIVE gematria/cee parity (Track A fair compare)",
    )
    ap.add_argument(
        "--preset",
        choices=(
            "full",
            "active_neighborhood",
            "fast",
            "on_beat_search",
            "on_off_best_neighborhood",
            "on_offbest_caps_pair",
            "off_best_ultra_fine",
        ),
        default=None,
    )
    ap.add_argument(
        "--write-best-report",
        action="store_true",
        default=True,
        help="Write full .report.json for best row (required for ACTIVE apply gate)",
    )
    ap.add_argument(
        "--also-match-active-presets",
        action="store_true",
        default=True,
        help="Always run ACTIVE-matched cap triplets (+ domain_relaxed variants)",
    )
    ap.add_argument("--max-rows", type=int, default=0, help="0 = no limit")
    args = ap.parse_args()

    lexicon_on = bool(args.lexicon_on)
    fine_offbest = args.preset == "on_off_best_neighborhood"
    ultra_offbest = args.preset == "off_best_ultra_fine"
    if args.out_json is None:
        if lexicon_on and fine_offbest:
            args.out_json = SWEEP_OUT_ON_FINE
        elif not lexicon_on and ultra_offbest:
            args.out_json = SWEEP_OUT_OFF_ULTRA
        else:
            args.out_json = SWEEP_OUT_ON if lexicon_on else SWEEP_OUT_OFF
    if args.best_out_json is None:
        if lexicon_on and fine_offbest:
            args.best_out_json = BEST_OUT_ON_FINE
        else:
            args.best_out_json = BEST_OUT_ON if lexicon_on else BEST_OUT_OFF
    rank_primary = "jaccard" if lexicon_on else "saving"
    if args.preset is None:
        args.preset = "on_beat_search" if lexicon_on else "active_neighborhood"

    if not args.bench_input.is_file():
        print(f"error: missing {args.bench_input}", file=sys.stderr)
        return 1

    doc = json.loads(args.bench_input.read_text(encoding="utf-8"))
    baseline_j = 0.0
    baseline_path = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
    if baseline_path.is_file():
        bdoc = json.loads(baseline_path.read_text(encoding="utf-8"))
        baseline_j = float(
            bdoc.get("compression_metrics", {}).get(
                "avg_reconstruction_fidelity_jaccard", 0.0
            )
        )

    frozen = _frozen_active()
    g_grid, s_grid, h_grid = _preset_grids(args.preset)

    combos: list[tuple[float, float, float, bool]] = [
        (g, s, h, False) for g, s, h in product(g_grid, s_grid, h_grid)
    ]
    if args.also_match_active_presets:
        if lexicon_on:
            extras = [
                (0.32, 0.28, 0.55, False),
                (0.32, 0.28, 0.55, True),
                (0.35, 0.30, 0.60, True),
                (0.34, 0.28, 0.58, True),
                (0.36, 0.30, 0.60, True),
            ]
        else:
            extras = [
                (0.35, 0.30, 0.60, False),
                (0.35, 0.30, 0.60, True),
                (0.54, 0.50, 0.48, False),
                (0.54, 0.50, 0.48, True),
            ]
        seen = {c[:3] for c in combos}
        for g, s, h, dr in extras:
            if (g, s, h) not in seen:
                combos.append((g, s, h, dr))
                seen.add((g, s, h))
            elif dr:
                combos.append((g, s, h, dr))

    # Dedupe full tuple including domain_relaxed
    uniq: list[tuple[float, float, float, bool]] = []
    seen_full: set[tuple[float, float, float, bool]] = set()
    for c in combos:
        if c not in seen_full:
            seen_full.add(c)
            uniq.append(c)
    combos = uniq
    if args.max_rows > 0:
        combos = combos[: args.max_rows]

    rows: list[dict[str, Any]] = []
    best_report: dict[str, Any] | None = None
    for g, s, h, domain_relaxed in combos:
        agg, report = evaluate_ng40_lane(
            doc,
            bench_input=args.bench_input,
            general_cap=g,
            sensitive_cap=s,
            hangul_cap=h,
            baseline_j=baseline_j,
            use_domain_relaxed=domain_relaxed,
            use_master_codebook_lexicon_v1=lexicon_on,
            active_track_parity=lexicon_on,
        )
        beat = _beat(agg, frozen)
        rows.append(
            {
                "caps": {
                    "general_max_saving_rate": g,
                    "sensitive_max_saving_rate": s,
                    "hangul_max_saving_rate": h,
                    "with_domain_relaxed": domain_relaxed,
                    "use_master_codebook_lexicon_v1": lexicon_on,
                    "active_track_parity": lexicon_on,
                },
                "aggregate": agg,
                "beat_check": beat,
            }
        )

    rows.sort(key=lambda r: _rank_key(r, primary=rank_primary), reverse=True)
    best = rows[0] if rows else None
    any_beat = any((r.get("beat_check") or {}).get("beat_frozen") for r in rows)

    sweep_doc = {
        "schema": "nextgen_latent_eval_ng40_cap_sweep_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "lexicon_on": lexicon_on,
        "preset": args.preset,
        "combo_count": len(rows),
        "any_beat_frozen": any_beat,
        "frozen_baseline_parallel": frozen,
        "rows": rows,
        "best": best,
        "guardrails": [
            "Sweep is B-track only; beat_frozen does not auto-write ACTIVE without gates",
            (
                "41k lexicon ON + ACTIVE parity rows — eligible for apply if beat + sign-off"
                if lexicon_on
                else "41k lexicon OFF — not eligible for ACTIVE apply script"
            ),
        ],
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(sweep_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if best:
        caps = best["caps"]
        g, s, h = (
            caps["general_max_saving_rate"],
            caps["sensitive_max_saving_rate"],
            caps["hangul_max_saving_rate"],
        )
        if args.write_best_report:
            _, best_report = evaluate_ng40_lane(
                doc,
                bench_input=args.bench_input,
                general_cap=float(g),
                sensitive_cap=float(s),
                hangul_cap=float(h),
                baseline_j=baseline_j,
                use_domain_relaxed=bool(caps.get("with_domain_relaxed")),
                use_master_codebook_lexicon_v1=lexicon_on,
                active_track_parity=lexicon_on,
            )
        arm_id = (
            "ng40_latent_eval_41k_on_best_v1"
            if lexicon_on
            else "ng40_latent_eval_best_v1"
        )
        best_eval = {
            "schema": "nextgen_latent_eval_ng40_v1",
            "generated_at_utc": _utc(),
            "research_only": True,
            "hypo_label": "[HYPO]",
            "track_a_active_write": False,
            "golden40_compatible": True,
            "lane": (
                "nextgen_latent_eval_with_41k_lexicon"
                if lexicon_on
                else "nextgen_latent_eval_no_41k_lexicon"
            ),
            "arm_id": arm_id,
            "source_sweep": str(
            args.out_json.resolve().relative_to(ROOT.resolve())
        ).replace("\\", "/"),
            "aggregate": best["aggregate"],
            "frozen_baseline_parallel": frozen,
            "beat_check": best["beat_check"],
            "run_config_summary": {
                "mode": "experimental",
                "use_master_codebook_lexicon_v1": lexicon_on,
                "active_track_parity": lexicon_on,
                **caps,
            },
            "guardrails": sweep_doc["guardrails"],
        }
        args.best_out_json.parent.mkdir(parents=True, exist_ok=True)
        args.best_out_json.write_text(
            json.dumps(best_eval, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if best_report is not None:
            report_path = args.best_out_json.with_suffix(".report.json")
            report_path.write_text(
                json.dumps(best_report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            try:
                rp = str(report_path.resolve().relative_to(ROOT.resolve())).replace(
                    "\\", "/"
                )
            except ValueError:
                rp = str(report_path).replace("\\", "/")
            best_eval["report_pointer"] = rp
            args.best_out_json.write_text(
                json.dumps(best_eval, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "best_out": str(args.best_out_json) if best else None,
                "combo_count": len(rows),
                "any_beat_frozen": any_beat,
                "best_caps": best["caps"] if best else None,
                "best_saving": (best or {}).get("aggregate", {}).get(
                    "global_token_saving_rate"
                ),
                "best_jaccard": (best or {}).get("aggregate", {}).get(
                    "avg_reconstruction_fidelity_jaccard"
                ),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
