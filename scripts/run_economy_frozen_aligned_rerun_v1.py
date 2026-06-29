#!/usr/bin/env python3
"""Re-run economy profile aligned to frozen active lexicon + bridge flags — fair Golden-40 diff."""

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

from scripts.build_master_codebook_golden40_lexicon_ab_v1 import (  # noqa: E402
    _load_signoff_relaxed,
    _metrics,
)
from scripts.compression_profile_v1 import profile_evaluate_report_kwargs  # noqa: E402
from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402
from scripts.run_ultra_compression_default import (  # noqa: E402
    BASELINE_V2,
    DECISION,
    INPUT_V2,
)
from scripts.ultra_compression_track_a_policy_floor_v1 import (  # noqa: E402
    apply_promoted_policy_floor_to_quality_gate,
)

EXP = ROOT / "experiments" / "compression_pipeline_grid_sweep_v1"
ACTIVE = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
DEFAULT_LEXICON_41708 = (
    ROOT / "reports" / "constitution" / "btrack_pilot" / "master_codebook_lexicon_v1_41708_rows_latest.json"
)
DEFAULT_OUT_REPORT = EXP / "runs" / "profile_economy_frozen_aligned.json"
DEFAULT_OUT_SUMMARY = EXP / "results" / "economy_frozen_aligned_rerun_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _per_case_delta(
    baseline_cases: list[dict[str, Any]], candidate_cases: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_b = {str(c.get("id")): c for c in baseline_cases if c.get("id")}
    by_c = {str(c.get("id")): c for c in candidate_cases if c.get("id")}
    out: list[dict[str, Any]] = []
    for cid in sorted(set(by_b) & set(by_c)):
        b, c = by_b[cid], by_c[cid]
        ds = float(c.get("token_saving_rate") or 0) - float(b.get("token_saving_rate") or 0)
        dj = float(c.get("reconstruction_fidelity_jaccard") or 0) - float(
            b.get("reconstruction_fidelity_jaccard") or 0
        )
        out.append(
            {
                "id": cid,
                "delta_saving": round(ds, 6),
                "delta_jaccard": round(dj, 6),
            }
        )
    return out


def _eval_economy_frozen_aligned(
    src: dict[str, Any],
    lexicon: Path,
    frozen_rc: dict[str, Any],
    domain_relaxed: dict[str, float],
    allow: frozenset[str] | None,
    exclude: frozenset[str] | None,
) -> dict[str, Any]:
    baseline_doc = _load(BASELINE_V2)
    decision_doc = _load(DECISION)
    baseline_avg_jaccard = float(
        baseline_doc.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    threshold_pp = float(decision_doc.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))
    kw = profile_evaluate_report_kwargs("economy")
    must_keep = set(frozen_rc.get("must_keep_terms") or ["사상의학", "체질", "sasang", "myeongni", "bible"])
    kw["include_gematria_metadata"] = bool(frozen_rc.get("include_gematria_metadata", True))
    kw["include_gematria_4d_bridge"] = bool(frozen_rc.get("include_gematria_4d_bridge", True))
    kw["include_cee_core"] = bool(frozen_rc.get("include_cee_core", True))
    kw["apply_gematria_4d_bridge_policy"] = bool(frozen_rc.get("apply_gematria_4d_bridge_policy", False))

    report = evaluate_report(
        src,
        source_input=_rel(INPUT_V2),
        mode="experimental",
        must_keep=must_keep,
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_avg_jaccard,
        master_codebook_lexicon_path=str(lexicon.resolve()),
        domain_relaxed_max_saving_overrides=domain_relaxed or None,
        domain_relaxed_max_saving_case_allowlist=allow,
        domain_relaxed_max_saving_exclude_case_ids=exclude,
        **kw,
    )
    apply_promoted_policy_floor_to_quality_gate(report)
    report.setdefault("run_config", {})
    report["run_config"]["frozen_aligned_rerun_v1"] = {
        "lexicon_basename": lexicon.name,
        "bridge_flags_matched_frozen_active": True,
        "must_keep_terms_source": "frozen_active_run_config",
    }
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Economy profile rerun aligned to frozen active (research_only).")
    ap.add_argument("--frozen", type=Path, default=ACTIVE)
    ap.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON_41708)
    ap.add_argument("--out-report", type=Path, default=DEFAULT_OUT_REPORT)
    ap.add_argument("--out-summary", type=Path, default=DEFAULT_OUT_SUMMARY)
    ap.add_argument("--mirror-pilot", action="store_true")
    args = ap.parse_args()

    for path in (args.frozen, args.lexicon, INPUT_V2):
        if not path.is_file():
            print(f"ABORT: missing {path}")
            return 2

    frozen_doc = _load(args.frozen)
    frozen_rc = frozen_doc.get("run_config") or {}
    frozen_metrics = _metrics(frozen_doc)
    frozen_cases = (frozen_doc.get("compression_metrics") or {}).get("cases") or []

    src = _load(INPUT_V2)
    relaxed, allow, exclude = _load_signoff_relaxed()
    report = _eval_economy_frozen_aligned(src, args.lexicon, frozen_rc, relaxed, allow, exclude)

    args.out_report.parent.mkdir(parents=True, exist_ok=True)
    args.out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cand_metrics = _metrics(report)
    cand_cases = (report.get("compression_metrics") or {}).get("cases") or []
    deltas = _per_case_delta(frozen_cases, cand_cases)
    changed = [d for d in deltas if abs(d["delta_saving"]) > 1e-9 or abs(d["delta_jaccard"]) > 1e-9]

    fs = float(frozen_metrics.get("global_token_saving_rate") or 0)
    cs = float(cand_metrics.get("global_token_saving_rate") or 0)
    fj = float(frozen_metrics.get("avg_reconstruction_fidelity_jaccard") or 0)
    cj = float(cand_metrics.get("avg_reconstruction_fidelity_jaccard") or 0)

    summary = {
        "schema": "economy_frozen_aligned_rerun_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "promote_active": False,
        "correlation_claim_allowed": False,
        "frozen_active_pointer": _rel(args.frozen),
        "aligned_report_pointer": _rel(args.out_report),
        "alignment": {
            "lexicon": _rel(args.lexicon),
            "bridge_flags_from_frozen_active": True,
            "economy_profile_caps": True,
            "policy_floor_applied": True,
        },
        "frozen_active_metrics": frozen_metrics,
        "aligned_economy_metrics": cand_metrics,
        "global_delta": {
            "delta_saving_pp": round((cs - fs) * 100.0, 4),
            "delta_jaccard_pp": round((cj - fj) * 100.0, 4),
        },
        "per_case": {
            "changed_case_count": len(changed),
            "unchanged_case_count": 40 - len(changed),
            "changed_case_ids": [d["id"] for d in changed],
            "deltas": deltas,
        },
        "verdict": {
            "collapsed_to_frozen": len(changed) == 0
            and abs(cs - fs) < 1e-9
            and abs(cj - fj) < 1e-9,
            "recommendation": (
                "Prior grid economy uplift was config-mismatch artifact; hold active."
                if len(changed) == 0 and abs(cs - fs) < 1e-6 and abs(cj - fj) < 1e-6
                else "Residual deltas remain after alignment — investigate policy_floor or caps."
            ),
        },
    }

    args.out_summary.parent.mkdir(parents=True, exist_ok=True)
    args.out_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_report}")
    print(f"WROTE: {args.out_summary}")
    print(f"changed_cases={len(changed)} delta_saving_pp={summary['global_delta']['delta_saving_pp']}")

    if args.mirror_pilot:
        pilot = ROOT / "reports" / "constitution" / "btrack_pilot" / "economy_frozen_aligned_rerun_v1_latest.json"
        pilot.write_text(args.out_summary.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"WROTE: {pilot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
