"""Shared ACTIVE-aligned evaluate_report kwargs for Hangul curated benches."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.report_multilens_performance_eval import evaluate_report
from scripts.ultra_compression_track_a_policy_floor_v1 import apply_promoted_policy_floor_to_quality_gate

ROOT = Path(__file__).resolve().parents[2]
INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"

MEDICAL_KO_CASE_IDS = frozenset(f"cmp2_{i:03d}" for i in range(11, 41))


def active_run_config() -> dict[str, Any]:
    if not ACTIVE.is_file():
        return {}
    frozen = json.loads(ACTIVE.read_text(encoding="utf-8"))
    cfg = frozen.get("run_config")
    return cfg if isinstance(cfg, dict) else {}


def evaluate_with_active_profile(
    src_doc: dict[str, Any],
    *,
    lexicon_path: Path,
) -> dict[str, Any]:
    rcfg = active_run_config()
    baseline_doc = json.loads(BASELINE_V2.read_text(encoding="utf-8"))
    decision_doc = json.loads(DECISION.read_text(encoding="utf-8"))
    baseline_avg_jaccard = float(
        baseline_doc.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    threshold_pp = float(decision_doc.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))

    general_max = rcfg.get("general_max_saving_rate")
    sensitive_max = rcfg.get("sensitive_max_saving_rate")
    hangul_max = rcfg.get("hangul_max_saving_rate")
    overrides = rcfg.get("domain_relaxed_max_saving_overrides") or {}
    domain_relaxed = (
        {str(k): float(v) for k, v in overrides.items()} if isinstance(overrides, dict) else {}
    )
    allow_list = rcfg.get("domain_relaxed_max_saving_case_allowlist")
    relaxed_allow = (
        frozenset(str(x) for x in allow_list) if isinstance(allow_list, list) and allow_list else None
    )
    exclude_list = rcfg.get("domain_relaxed_max_saving_exclude_case_ids")
    relaxed_exclude = (
        frozenset(str(x) for x in exclude_list) if isinstance(exclude_list, list) and exclude_list else None
    )

    report = evaluate_report(
        src_doc,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode=str(rcfg.get("mode", "experimental")),
        strategy=str(rcfg.get("strategy", "A")),
        intensity=str(rcfg.get("intensity", "extreme")),
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_avg_jaccard,
        general_max_saving_rate=float(general_max) if general_max is not None else None,
        sensitive_max_saving_rate=float(sensitive_max) if sensitive_max is not None else None,
        hangul_max_saving_rate=float(hangul_max) if hangul_max is not None else None,
        use_domain_router=bool(rcfg.get("use_domain_router", True)),
        use_master_codebook_lexicon_v1=True,
        master_codebook_lexicon_path=str(lexicon_path.resolve()),
        include_gematria_metadata=bool(rcfg.get("include_gematria_metadata", True)),
        include_gematria_4d_bridge=bool(rcfg.get("include_gematria_4d_bridge", True)),
        apply_gematria_4d_bridge_policy=bool(rcfg.get("apply_gematria_4d_bridge_policy", False)),
        domain_relaxed_max_saving_overrides=domain_relaxed or None,
        domain_relaxed_max_saving_case_allowlist=relaxed_allow,
        domain_relaxed_max_saving_exclude_case_ids=relaxed_exclude,
        include_cee_core=bool(rcfg.get("include_cee_core", True)),
    )
    apply_promoted_policy_floor_to_quality_gate(report)
    return report


def subset_metrics(cases: list[dict[str, Any]], id_set: frozenset[str]) -> dict[str, Any]:
    rows = [c for c in cases if str(c.get("id", "")) in id_set]
    if not rows:
        return {"case_count": 0}
    n = len(rows)
    sav = sum(float(r.get("token_saving_rate") or 0.0) for r in rows) / n
    jac = sum(float(r.get("reconstruction_fidelity_jaccard") or 0.0) for r in rows) / n
    hits = 0
    for r in rows:
        route = r.get("route") or {}
        meta = route.get("master_codebook_lexicon_v1") or {}
        if int(meta.get("hit_count") or 0) > 0:
            hits += 1
    return {
        "case_count": n,
        "avg_token_saving_rate": sav,
        "avg_reconstruction_fidelity_jaccard": jac,
        "cases_with_lexicon_hit_gt_0": hits,
    }
