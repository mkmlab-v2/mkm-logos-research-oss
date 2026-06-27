#!/usr/bin/env python3
"""[HYPO] Next-Gen Golden-40 eval: experimental compress without 41k lexicon (B-track).

Uses evaluate_report with use_master_codebook_lexicon_v1=False — discrete 41k OFF.
"""
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

from scripts.report_multilens_performance_eval import evaluate_report

INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
DEFAULT_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_v1_latest.json"
)

_MUST_KEEP = frozenset({"사상의학", "체질", "sasang", "myeongri", "bible"})


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _metrics(cm: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_count": cm.get("case_count"),
        "global_token_saving_rate": cm.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
        "min_reconstruction_fidelity_jaccard": cm.get("min_reconstruction_fidelity_jaccard"),
        "sensitive_violation_count": cm.get("sensitive_violation_count"),
    }


def _frozen_active() -> dict[str, Any]:
    if not ACTIVE.is_file():
        return {"present": False}
    doc = json.loads(ACTIVE.read_text(encoding="utf-8"))
    return {"present": True, **_metrics(doc.get("compression_metrics") or {})}


LEXICON_DEFAULT = (
    ROOT
    / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41708_rows_latest.json"
)


def _active_lexicon_path() -> Path | None:
    if not ACTIVE.is_file():
        return LEXICON_DEFAULT if LEXICON_DEFAULT.is_file() else None
    rc = json.loads(ACTIVE.read_text(encoding="utf-8")).get("run_config") or {}
    raw = rc.get("master_codebook_lexicon_path")
    if not raw:
        return LEXICON_DEFAULT if LEXICON_DEFAULT.is_file() else None
    p = Path(str(raw))
    return p if p.is_file() else (LEXICON_DEFAULT if LEXICON_DEFAULT.is_file() else None)


def evaluate_ng40_lane(
    doc: dict[str, Any],
    *,
    bench_input: Path,
    strategy: str = "A",
    intensity: str = "extreme",
    general_cap: float = 0.54,
    sensitive_cap: float = 0.5,
    hangul_cap: float = 0.48,
    baseline_j: float = 0.0,
    use_domain_relaxed: bool = False,
    use_master_codebook_lexicon_v1: bool = False,
    active_track_parity: bool = False,
    master_codebook_lexicon_path: Path | None = None,
    archetype_prior_must_keep: set[str] | frozenset[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run one NG-40 bench eval. Returns (aggregate_metrics, full_report)."""
    domain_relaxed: dict[str, float] | None = None
    relaxed_allow: frozenset[str] | None = None
    if use_domain_relaxed:
        domain_relaxed = {"ssot": 0.45}
        relaxed_allow = frozenset(
            {"cmp2_002", "cmp2_004", "cmp2_005", "cmp2_006", "cmp2_009"}
        )
    lex_path = master_codebook_lexicon_path
    if use_master_codebook_lexicon_v1 and lex_path is None:
        lex_path = _active_lexicon_path()
    gem_meta = include_gematria = include_cee = False
    if active_track_parity and use_master_codebook_lexicon_v1:
        gem_meta = include_gematria = include_cee = True
    must_keep = set(_MUST_KEEP)
    if archetype_prior_must_keep:
        must_keep.update(archetype_prior_must_keep)
    report = evaluate_report(
        doc,
        source_input=str(bench_input.relative_to(ROOT)).replace("\\", "/"),
        mode="experimental",
        strategy=strategy,
        intensity=intensity,
        must_keep=must_keep,
        jaccard_drop_threshold_pp=2.0,
        baseline_avg_jaccard=baseline_j,
        general_max_saving_rate=general_cap,
        sensitive_max_saving_rate=sensitive_cap,
        hangul_max_saving_rate=hangul_cap,
        use_domain_router=True,
        use_master_codebook_lexicon_v1=use_master_codebook_lexicon_v1,
        master_codebook_lexicon_path=lex_path,
        include_gematria_metadata=gem_meta,
        include_gematria_4d_bridge=include_gematria,
        include_cee_core=include_cee,
        apply_gematria_4d_bridge_policy=False,
        domain_relaxed_max_saving_overrides=domain_relaxed,
        domain_relaxed_max_saving_case_allowlist=relaxed_allow,
    )
    return _metrics(report.get("compression_metrics") or {}), report


def _beat(candidate: dict[str, Any], frozen: dict[str, Any]) -> dict[str, Any]:
    if not frozen.get("present"):
        return {"beat_frozen": False, "reason": "missing_frozen"}
    s_c = candidate.get("global_token_saving_rate")
    j_c = candidate.get("avg_reconstruction_fidelity_jaccard")
    s_f = frozen.get("global_token_saving_rate")
    j_f = frozen.get("avg_reconstruction_fidelity_jaccard")
    if None in (s_c, j_c, s_f, j_f):
        return {"beat_frozen": False, "reason": "incomplete_metrics"}
    beat = float(s_c) >= float(s_f) and float(j_c) >= float(j_f)
    return {
        "beat_frozen": beat,
        "delta_saving_pp": round((float(s_c) - float(s_f)) * 100, 2),
        "delta_jaccard_pp": round((float(j_c) - float(j_f)) * 100, 2),
        "reason": "both_saving_and_jaccard_gte_frozen" if beat else "not_both_axes",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench-input", type=Path, default=INPUT_V2)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strategy", default="A")
    ap.add_argument("--intensity", default="extreme")
    ap.add_argument("--general-cap", type=float, default=0.54)
    ap.add_argument("--sensitive-cap", type=float, default=0.5)
    ap.add_argument("--hangul-cap", type=float, default=0.48)
    ap.add_argument(
        "--match-active-caps",
        action="store_true",
        help="Use frozen ACTIVE cap profile (0.35/0.30/0.60)",
    )
    ap.add_argument(
        "--with-domain-relaxed",
        action="store_true",
        help="Apply ACTIVE ssot domain_relaxed_max_saving allowlist",
    )
    ap.add_argument(
        "--with-41k-lexicon",
        action="store_true",
        help="Enable master_codebook_lexicon_v1 (ACTIVE path)",
    )
    ap.add_argument(
        "--active-track-parity",
        action="store_true",
        help="With 41k: match ACTIVE gematria/cee flags (bridge policy still OFF)",
    )
    args = ap.parse_args()

    if not args.bench_input.is_file():
        print(f"error: missing {args.bench_input}", file=sys.stderr)
        return 1

    doc = json.loads(args.bench_input.read_text(encoding="utf-8"))
    baseline_j = 0.0
    if BASELINE_V2.is_file():
        bdoc = json.loads(BASELINE_V2.read_text(encoding="utf-8"))
        baseline_j = float(
            bdoc.get("compression_metrics", {}).get(
                "avg_reconstruction_fidelity_jaccard", 0.0
            )
        )

    if args.match_active_caps:
        args.general_cap = 0.35
        args.sensitive_cap = 0.30
        args.hangul_cap = 0.60

    agg, report = evaluate_ng40_lane(
        doc,
        bench_input=args.bench_input,
        strategy=args.strategy,
        intensity=args.intensity,
        general_cap=args.general_cap,
        sensitive_cap=args.sensitive_cap,
        hangul_cap=args.hangul_cap,
        baseline_j=baseline_j,
        use_domain_relaxed=args.with_domain_relaxed,
        use_master_codebook_lexicon_v1=args.with_41k_lexicon,
        active_track_parity=args.active_track_parity,
    )
    frozen = _frozen_active()
    out = {
        "schema": "nextgen_latent_eval_ng40_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "golden40_compatible": True,
        "lane": (
            "nextgen_latent_eval_with_41k_lexicon"
            if args.with_41k_lexicon
            else "nextgen_latent_eval_no_41k_lexicon"
        ),
        "aggregate": agg,
        "frozen_baseline_parallel": frozen,
        "beat_check": _beat(agg, frozen),
        "run_config_summary": {
            "mode": "experimental",
            "use_master_codebook_lexicon_v1": args.with_41k_lexicon,
            "active_track_parity": args.active_track_parity,
            "apply_gematria_4d_bridge_policy": False,
            "strategy": args.strategy,
            "intensity": args.intensity,
            "general_max_saving_rate": args.general_cap,
            "sensitive_max_saving_rate": args.sensitive_cap,
            "hangul_max_saving_rate": args.hangul_cap,
            "match_active_caps": args.match_active_caps,
            "with_domain_relaxed": args.with_domain_relaxed,
        },
        "report_pointer": None,
        "guardrails": [
            "Not Track A active until apply_btrack_nextgen_promotion_to_active_v1.py",
            "FAIL-COMP-004: repair-only uplift cannot auto-merge MS/live",
        ],
    }
    report_path = args.out_json.parent / f"{args.out_json.stem}.report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    try:
        rp = str(report_path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        rp = str(report_path).replace("\\", "/")
    out["report_pointer"] = rp

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "beat_frozen": out["beat_check"]["beat_frozen"],
                "saving": agg.get("global_token_saving_rate"),
                "jaccard": agg.get("avg_reconstruction_fidelity_jaccard"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
