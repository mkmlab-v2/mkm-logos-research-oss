#!/usr/bin/env python3
"""Golden 40 A/B: same Track A ultra-default eval, explicit 41658 vs archived 41775 lexicon.

Does not write MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json.
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

from scripts.compression_profile_v1 import PROFILE_BENCH_SSOT  # noqa: E402
from scripts.core.multilens_bridge_policy_env import env_apply_gematria_4d_bridge_policy  # noqa: E402
from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402
from scripts.run_ultra_compression_default import (  # noqa: E402
    BASELINE_V2,
    DECISION,
    INPUT_V2,
    PROMOTION_SIGNOFF,
)
from scripts.ultra_compression_track_a_policy_floor_v1 import (  # noqa: E402
    apply_promoted_policy_floor_to_quality_gate,
)

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_658 = PILOT / "master_codebook_lexicon_v1_41658_rows_latest.json"
DEFAULT_775_ARCHIVED = PILOT / "master_codebook_lexicon_v1_41775_rows_archived_20260523.json"
DEFAULT_OUT = PILOT / "master_codebook_golden40_lexicon_ab_v1.json"
ACTIVE = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_signoff_relaxed() -> tuple[dict[str, float], frozenset[str] | None, frozenset[str] | None]:
    domain_relaxed: dict[str, float] = {}
    relaxed_case_allowlist: frozenset[str] | None = None
    relaxed_case_exclude: frozenset[str] | None = None
    if not PROMOTION_SIGNOFF.is_file():
        return domain_relaxed, relaxed_case_allowlist, relaxed_case_exclude
    signoff_doc = json.loads(PROMOTION_SIGNOFF.read_text(encoding="utf-8"))
    signoff_cfg = signoff_doc.get("selected_run_config")
    if not isinstance(signoff_cfg, dict):
        return domain_relaxed, relaxed_case_allowlist, relaxed_case_exclude
    overrides = signoff_cfg.get("domain_relaxed_max_saving_overrides") or {}
    if isinstance(overrides, dict):
        domain_relaxed = {str(k): float(v) for k, v in overrides.items()}
    allow_list = signoff_cfg.get("domain_relaxed_max_saving_case_allowlist")
    if isinstance(allow_list, list) and allow_list:
        relaxed_case_allowlist = frozenset(str(x) for x in allow_list)
    exclude_list = signoff_cfg.get("domain_relaxed_max_saving_exclude_case_ids")
    if isinstance(exclude_list, list) and exclude_list:
        relaxed_case_exclude = frozenset(str(x) for x in exclude_list)
    return domain_relaxed, relaxed_case_allowlist, relaxed_case_exclude


def _metrics(report: dict[str, Any]) -> dict[str, Any]:
    m = report.get("compression_metrics") or {}
    return {
        "case_count": m.get("case_count"),
        "global_token_saving_rate": m.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": m.get("avg_reconstruction_fidelity_jaccard"),
        "sensitive_violation_count": m.get("sensitive_violation_count"),
    }


def _run_eval(
    src_doc: dict[str, Any],
    *,
    lexicon_path: Path,
    domain_relaxed: dict[str, float],
    relaxed_case_allowlist: frozenset[str] | None,
    relaxed_case_exclude: frozenset[str] | None,
) -> dict[str, Any]:
    baseline_doc = json.loads(BASELINE_V2.read_text(encoding="utf-8"))
    decision_doc = json.loads(DECISION.read_text(encoding="utf-8"))
    selected = decision_doc.get("selected_candidate") or {}
    strategy = str(selected.get("strategy", "B"))
    intensity = str(selected.get("intensity", "extreme"))
    general_max_saving_rate = selected.get("general_max_saving_rate")
    sensitive_max_saving_rate = selected.get("sensitive_max_saving_rate")
    hangul_max_saving_rate = selected.get("hangul_max_saving_rate")
    if general_max_saving_rate is not None:
        general_max_saving_rate = float(general_max_saving_rate)
    if sensitive_max_saving_rate is not None:
        sensitive_max_saving_rate = float(sensitive_max_saving_rate)
    if hangul_max_saving_rate is not None:
        hangul_max_saving_rate = float(hangul_max_saving_rate)
    baseline_avg_jaccard = float(
        baseline_doc.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    threshold_pp = float(decision_doc.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))
    apply_bridge_policy = env_apply_gematria_4d_bridge_policy()

    report = evaluate_report(
        src_doc,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=strategy,
        intensity=intensity,
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_avg_jaccard,
        general_max_saving_rate=general_max_saving_rate,
        sensitive_max_saving_rate=sensitive_max_saving_rate,
        hangul_max_saving_rate=hangul_max_saving_rate,
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        master_codebook_lexicon_path=str(lexicon_path.resolve()),
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        apply_gematria_4d_bridge_policy=apply_bridge_policy,
        domain_relaxed_max_saving_overrides=domain_relaxed or None,
        domain_relaxed_max_saving_case_allowlist=relaxed_case_allowlist,
        domain_relaxed_max_saving_exclude_case_ids=relaxed_case_exclude,
        include_cee_core=True,
    )
    apply_promoted_policy_floor_to_quality_gate(report)
    return report


def _per_case_deltas(
    cases_a: list[dict[str, Any]], cases_b: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_a = {str(c.get("id")): c for c in cases_a if c.get("id")}
    by_b = {str(c.get("id")): c for c in cases_b if c.get("id")}
    out: list[dict[str, Any]] = []
    for cid in sorted(set(by_a) & set(by_b)):
        a, b = by_a[cid], by_b[cid]
        ds = float(b.get("token_saving_rate") or 0) - float(a.get("token_saving_rate") or 0)
        dj = float(b.get("reconstruction_fidelity_jaccard") or 0) - float(
            a.get("reconstruction_fidelity_jaccard") or 0
        )
        if abs(ds) > 1e-9 or abs(dj) > 1e-9:
            out.append(
                {
                    "id": cid,
                    "delta_saving_41775_minus_41658": round(ds, 6),
                    "delta_jaccard_41775_minus_41658": round(dj, 6),
                }
            )
    out.sort(
        key=lambda r: abs(r["delta_jaccard_41775_minus_41658"]) + abs(r["delta_saving_41775_minus_41658"]),
        reverse=True,
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Golden 40 lexicon row-count A/B (41658 vs archived 41775)")
    ap.add_argument("--codebook-41658", type=Path, default=DEFAULT_658)
    ap.add_argument("--codebook-41775-archived", type=Path, default=DEFAULT_775_ARCHIVED)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    p658 = args.codebook_41658 if args.codebook_41658.is_absolute() else ROOT / args.codebook_41658
    p775 = (
        args.codebook_41775_archived
        if args.codebook_41775_archived.is_absolute()
        else ROOT / args.codebook_41775_archived
    )
    for p in (p658, p775):
        if not p.is_file():
            print(f"ERROR: missing {p}", file=sys.stderr)
            return 2

    src_doc = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    domain_relaxed, allowlist, exclude = _load_signoff_relaxed()

    r658 = _run_eval(
        src_doc,
        lexicon_path=p658,
        domain_relaxed=domain_relaxed,
        relaxed_case_allowlist=allowlist,
        relaxed_case_exclude=exclude,
    )
    r775 = _run_eval(
        src_doc,
        lexicon_path=p775,
        domain_relaxed=domain_relaxed,
        relaxed_case_allowlist=allowlist,
        relaxed_case_exclude=exclude,
    )

    m658 = _metrics(r658)
    m775 = _metrics(r775)
    ds = float(m775["global_token_saving_rate"] or 0) - float(m658["global_token_saving_rate"] or 0)
    dj = float(m775["avg_reconstruction_fidelity_jaccard"] or 0) - float(
        m658["avg_reconstruction_fidelity_jaccard"] or 0
    )

    frozen = PROFILE_BENCH_SSOT["economy"]
    frozen_saving = float(frozen["headline_global_token_saving_rate"])
    frozen_jaccard = float(frozen["headline_jaccard"])

    active_metrics: dict[str, Any] | None = None
    if ACTIVE.is_file():
        active_metrics = _metrics(json.loads(ACTIVE.read_text(encoding="utf-8")))

    cases_658 = (r658.get("compression_metrics") or {}).get("cases") or []
    cases_775 = (r775.get("compression_metrics") or {}).get("cases") or []
    case_deltas = _per_case_deltas(cases_658, cases_775)

    eps_saving = 1e-6
    eps_jaccard = 1e-6
    lexicon_ab_negligible = abs(ds) < eps_saving and abs(dj) < eps_jaccard

    if lexicon_ab_negligible:
        verdict = "117_row_lexicon_drift_does_not_move_golden40_aggregate"
    elif abs(float(m658["global_token_saving_rate"] or 0) - frozen_saving) > eps_saving or abs(
        float(m658["avg_reconstruction_fidelity_jaccard"] or 0) - frozen_jaccard
    ) > eps_jaccard:
        if abs(float(m775["global_token_saving_rate"] or 0) - frozen_saving) < eps_saving and abs(
            float(m775["avg_reconstruction_fidelity_jaccard"] or 0) - frozen_jaccard
        ) < eps_jaccard:
            verdict = "41658_path_moves_kpi_vs_frozen_41775_archived_matches_frozen_headline"
        else:
            verdict = "both_lexicons_differ_from_frozen_headline_recheck_nondeterminism_or_config"
    else:
        verdict = "41658_matches_frozen_41775_archived_differs"

    doc: dict[str, Any] = {
        "schema": "master_codebook_golden40_lexicon_ab_v1",
        "verified_at_utc": _utc(),
        "bench": "golden_40_full_v2_ultra_default_equivalent",
        "active_report_untouched": True,
        "lexicon_paths": {
            "rows_41658": str(p658.resolve()),
            "rows_41775_archived": str(p775.resolve()),
        },
        "frozen_headline_economy_ssot": {
            "global_token_saving_rate": frozen_saving,
            "avg_reconstruction_fidelity_jaccard": frozen_jaccard,
            "source": "scripts/compression_profile_v1.py PROFILE_BENCH_SSOT economy",
        },
        "active_report_on_disk_at_run": active_metrics,
        "metrics_41658_explicit_path": m658,
        "metrics_41775_archived_explicit_path": m775,
        "delta_41775_minus_41658": {
            "global_token_saving_rate": round(ds, 6),
            "avg_reconstruction_fidelity_jaccard": round(dj, 6),
        },
        "per_case_deltas_nonzero_count": len(case_deltas),
        "per_case_deltas_top10": case_deltas[:10],
        "verdict": verdict,
        "interpretation": {
            "net_atom_row_gap": 117,
            "greek_hebrew_parity": "see master_codebook_41775_vs_41658_atom_diff_v1.json",
            "fail_comp_004": "does_not_auto_rewrite_active_or_frozen_headline",
        },
    }

    out = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {out}")
    print(f"verdict={verdict}")
    print(f"41658 saving={m658['global_token_saving_rate']} jaccard={m658['avg_reconstruction_fidelity_jaccard']}")
    print(f"41775 saving={m775['global_token_saving_rate']} jaccard={m775['avg_reconstruction_fidelity_jaccard']}")
    print(f"delta_41775_minus_41658 saving={round(ds, 6)} jaccard={round(dj, 6)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
