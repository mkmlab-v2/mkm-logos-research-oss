#!/usr/bin/env python3
"""[HYPO] NG-40 paired ablation: 41k OFF vs ON at matched caps (lexicon attribution)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_nextgen_latent_indexer_eval_ng40_v1 import (  # noqa: E402
    ACTIVE,
    INPUT_V2,
    _active_lexicon_path,
    _beat,
    _frozen_active,
    _utc,
    evaluate_ng40_lane,
)

BEST_CAPS_JSON = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_best_v1_latest.json"
)
OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_lexicon_ablation_v1_latest.json"
)

ACTIVE_CAPS = (0.35, 0.30, 0.60)


def _load_caps(path: Path) -> tuple[float, float, float, bool]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    rc = doc.get("run_config_summary") or {}
    return (
        float(rc.get("general_max_saving_rate", 0.32)),
        float(rc.get("sensitive_max_saving_rate", 0.28)),
        float(rc.get("hangul_max_saving_rate", 0.55)),
        bool(rc.get("with_domain_relaxed", False)),
    )


def _run_arm(
    doc: dict[str, Any],
    *,
    bench_input: Path,
    arm_id: str,
    label: str,
    g: float,
    s: float,
    h: float,
    lexicon_on: bool,
    domain_relaxed: bool,
    active_parity: bool,
    baseline_j: float,
) -> dict[str, Any]:
    agg, _report = evaluate_ng40_lane(
        doc,
        bench_input=bench_input,
        general_cap=g,
        sensitive_cap=s,
        hangul_cap=h,
        baseline_j=baseline_j,
        use_domain_relaxed=domain_relaxed,
        use_master_codebook_lexicon_v1=lexicon_on,
        active_track_parity=active_parity,
    )
    frozen = _frozen_active()
    beat = _beat(agg, frozen)
    return {
        "arm_id": arm_id,
        "label": label,
        "caps": {
            "general_max_saving_rate": g,
            "sensitive_max_saving_rate": s,
            "hangul_max_saving_rate": h,
            "with_domain_relaxed": domain_relaxed,
        },
        "use_master_codebook_lexicon_v1": lexicon_on,
        "active_track_parity": active_parity,
        "aggregate": agg,
        "beat_check": beat,
    }


def _delta_pp(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return round((float(a) - float(b)) * 100, 2)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench-input", type=Path, default=INPUT_V2)
    ap.add_argument("--best-caps-json", type=Path, default=BEST_CAPS_JSON)
    ap.add_argument("--out-json", type=Path, default=OUT)
    ap.add_argument(
        "--quick",
        action="store_true",
        help="Only best_caps OFF/ON pair (skip ACTIVE cap arms)",
    )
    args = ap.parse_args()

    if not args.bench_input.is_file():
        print(f"error: missing {args.bench_input}", file=sys.stderr)
        return 1
    if not _active_lexicon_path():
        print("error: 41k lexicon path missing", file=sys.stderr)
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

    if args.best_caps_json.is_file():
        bg, bs, bh, bdr = _load_caps(args.best_caps_json)
    else:
        bg, bs, bh, bdr = (0.32, 0.28, 0.55, False)

    ag, as_, ah = ACTIVE_CAPS
    arms = [
        _run_arm(
            doc,
            bench_input=args.bench_input,
            arm_id="off_at_best_caps",
            label="41k OFF · sweep best caps",
            g=bg,
            s=bs,
            h=bh,
            lexicon_on=False,
            domain_relaxed=bdr,
            active_parity=False,
            baseline_j=baseline_j,
        ),
        _run_arm(
            doc,
            bench_input=args.bench_input,
            arm_id="on_at_best_caps_parity",
            label="41k ON · same caps · ACTIVE gematria/cee parity",
            g=bg,
            s=bs,
            h=bh,
            lexicon_on=True,
            domain_relaxed=bdr,
            active_parity=True,
            baseline_j=baseline_j,
        ),
    ]
    if not args.quick:
        arms.extend(
            [
                _run_arm(
                    doc,
                    bench_input=args.bench_input,
                    arm_id="on_at_active_caps_parity",
                    label="41k ON · ACTIVE caps · domain_relaxed",
                    g=ag,
                    s=as_,
                    h=ah,
                    lexicon_on=True,
                    domain_relaxed=True,
                    active_parity=True,
                    baseline_j=baseline_j,
                ),
                _run_arm(
                    doc,
                    bench_input=args.bench_input,
                    arm_id="off_at_active_caps",
                    label="41k OFF · ACTIVE caps · domain_relaxed",
                    g=ag,
                    s=as_,
                    h=ah,
                    lexicon_on=False,
                    domain_relaxed=True,
                    active_parity=False,
                    baseline_j=baseline_j,
                ),
            ]
        )

    off_best = arms[0]["aggregate"]
    on_best = arms[1]["aggregate"]
    frozen = _frozen_active()
    frozen_cm = {}
    if ACTIVE.is_file():
        frozen_cm = json.loads(ACTIVE.read_text(encoding="utf-8")).get(
            "compression_metrics"
        ) or {}

    attribution = {
        "lexicon_on_minus_off_at_best_caps": {
            "delta_saving_pp": _delta_pp(
                on_best.get("global_token_saving_rate"),
                off_best.get("global_token_saving_rate"),
            ),
            "delta_jaccard_pp": _delta_pp(
                on_best.get("avg_reconstruction_fidelity_jaccard"),
                off_best.get("avg_reconstruction_fidelity_jaccard"),
            ),
        },
        "off_at_best_beats_frozen": arms[0]["beat_check"].get("beat_frozen"),
        "on_at_best_beats_frozen": arms[1]["beat_check"].get("beat_frozen"),
        "frozen_active_headline": {
            "global_token_saving_rate": frozen.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": frozen.get(
                "avg_reconstruction_fidelity_jaccard"
            ),
        },
        "interpretation_ko": (
            "beat_frozen at best caps without 41k implies cap tuning dominates at this grid; "
            "compare lexicon_on_minus_off to see discrete lookup contribution at matched caps."
        ),
    }

    out = {
        "schema": "nextgen_latent_eval_ng40_lexicon_ablation_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "lexicon_path": str(_active_lexicon_path()).replace("\\", "/"),
        "best_caps_source": (
            str(args.best_caps_json.relative_to(ROOT)).replace("\\", "/")
            if args.best_caps_json.is_file()
            else None
        ),
        "arms": arms,
        "attribution": attribution,
        "guardrails": [
            "Ablation does not auto-write ACTIVE; 41k ON arm may approach frozen SSOT",
            "Neural latent E2E not claimed; evaluate_report experimental path only",
        ],
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "off_best": {
                    "saving": off_best.get("global_token_saving_rate"),
                    "jaccard": off_best.get("avg_reconstruction_fidelity_jaccard"),
                    "beat_frozen": arms[0]["beat_check"].get("beat_frozen"),
                },
                "on_best": {
                    "saving": on_best.get("global_token_saving_rate"),
                    "jaccard": on_best.get("avg_reconstruction_fidelity_jaccard"),
                    "beat_frozen": arms[1]["beat_check"].get("beat_frozen"),
                },
                "lexicon_delta_pp": attribution["lexicon_on_minus_off_at_best_caps"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
