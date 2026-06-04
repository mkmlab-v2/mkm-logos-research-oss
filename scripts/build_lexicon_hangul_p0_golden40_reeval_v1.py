#!/usr/bin/env python3
"""Golden-40 full reeval: ACTIVE flags vs [HYPO] harness / CJK / exclude_function_words."""
from __future__ import annotations

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
    _run_eval,
)
from scripts.core.master_codebook_lexicon_v1_bridge import resolve_latest_codebook_path
from scripts.core.multilens_bridge_policy_env import env_apply_gematria_4d_bridge_policy
from scripts.report_multilens_performance_eval import evaluate_report
from scripts.run_ultra_compression_default import BASELINE_V2, DECISION, INPUT_V2
from scripts.ultra_compression_track_a_policy_floor_v1 import apply_promoted_policy_floor_to_quality_gate

ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
OUT = ROOT / "reports/lexicon_hangul_p0_golden40_reeval_v1_latest.json"
HANGUL_IDS = {f"cmp2_{i:03d}" for i in range(11, 41)}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _delta_vs(active: dict[str, Any], cand: dict[str, Any]) -> dict[str, Any]:
    s0 = float(active.get("global_token_saving_rate") or 0)
    j0 = float(active.get("avg_reconstruction_fidelity_jaccard") or 0)
    s1 = float(cand.get("global_token_saving_rate") or 0)
    j1 = float(cand.get("avg_reconstruction_fidelity_jaccard") or 0)
    return {
        "delta_saving_pp": round((s1 - s0) * 100, 4),
        "delta_jaccard_pp": round((j1 - j0) * 100, 4),
        "beat_frozen_saving_and_jaccard": s1 >= s0 and j1 >= j0,
        "strict_beat_both_axes": s1 > s0 and j1 > j0,
    }


def _full_eval(
    src: dict[str, Any],
    cb: Path,
    relaxed: tuple,
    *,
    harness: bool = False,
    cjk: bool = False,
    exclude_function_words: bool = False,
) -> dict[str, Any]:
    domain_relaxed, allow, exclude = relaxed
    if cjk:
        active_doc = json.loads(ACTIVE.read_text(encoding="utf-8"))
        rc = active_doc.get("run_config") or {}
        baseline_doc = json.loads(BASELINE_V2.read_text(encoding="utf-8"))
        decision_doc = json.loads(DECISION.read_text(encoding="utf-8"))
        selected = decision_doc.get("selected_candidate") or {}
        baseline_j = float(
            baseline_doc.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
        )
        threshold_pp = float(decision_doc.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))
        report = evaluate_report(
            src,
            source_input=str(INPUT_V2.relative_to(ROOT)).replace("\\", "/"),
            mode=str(rc.get("mode", "experimental")),
            strategy=str(rc.get("strategy", "A")),
            intensity=str(rc.get("intensity", "extreme")),
            must_keep=set(rc.get("must_keep_terms") or []),
            jaccard_drop_threshold_pp=threshold_pp,
            baseline_avg_jaccard=baseline_j,
            general_max_saving_rate=float(rc.get("general_max_saving_rate", 0.35)),
            sensitive_max_saving_rate=float(rc.get("sensitive_max_saving_rate", 0.3)),
            hangul_max_saving_rate=float(rc.get("hangul_max_saving_rate", 0.6)),
            use_domain_router=bool(rc.get("use_domain_router", True)),
            use_master_codebook_lexicon_v1=True,
            master_codebook_lexicon_path=str(cb.resolve()),
            master_codebook_lexicon_include_cjk_bigrams=True,
            master_codebook_lexicon_include_hangul_tokenizer_harness=False,
            master_codebook_lexicon_exclude_function_words=exclude_function_words,
            include_gematria_metadata=bool(rc.get("include_gematria_metadata", True)),
            include_gematria_4d_bridge=bool(rc.get("include_gematria_4d_bridge", True)),
            apply_gematria_4d_bridge_policy=env_apply_gematria_4d_bridge_policy(),
            domain_relaxed_max_saving_overrides=domain_relaxed or None,
            domain_relaxed_max_saving_case_allowlist=allow,
            domain_relaxed_max_saving_exclude_case_ids=exclude,
            include_cee_core=bool(rc.get("include_cee_core", True)),
        )
        apply_promoted_policy_floor_to_quality_gate(report)
        return report
    return _run_eval(
        src,
        lexicon_path=cb,
        domain_relaxed=domain_relaxed,
        relaxed_case_allowlist=allow,
        relaxed_case_exclude=exclude,
        exclude_function_words=exclude_function_words,
        include_hangul_tokenizer_harness=harness,
    )


def _hangul_case_deltas(base_cases: list, alt_cases: list) -> list[dict[str, Any]]:
    by_b = {str(c.get("id")): c for c in base_cases if c.get("id")}
    by_a = {str(c.get("id")): c for c in alt_cases if c.get("id")}
    rows = []
    for cid in sorted(HANGUL_IDS):
        if cid not in by_b or cid not in by_a:
            continue
        b, a = by_b[cid], by_a[cid]
        ds = float(a.get("token_saving_rate") or 0) - float(b.get("token_saving_rate") or 0)
        dj = float(a.get("reconstruction_fidelity_jaccard") or 0) - float(
            b.get("reconstruction_fidelity_jaccard") or 0
        )
        rows.append(
            {
                "id": cid,
                "delta_saving": round(ds, 6),
                "delta_jaccard": round(dj, 6),
                "changed": abs(ds) > 1e-9 or abs(dj) > 1e-9,
            }
        )
    return rows


def main() -> int:
    if not INPUT_V2.is_file() or not ACTIVE.is_file():
        print("ABORT: missing INPUT_V2 or ACTIVE")
        return 1
    cb = resolve_latest_codebook_path()
    if cb is None:
        print("ABORT: lexicon missing")
        return 1

    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    active_doc = json.loads(ACTIVE.read_text(encoding="utf-8"))
    frozen = _metrics(active_doc)
    relaxed = _load_signoff_relaxed()

    arms = {
        "active_baseline": {"harness": False, "cjk": False, "exclude_function_words": False},
        "hypo_hangul_harness_v1": {"harness": True, "cjk": False, "exclude_function_words": False},
        "hypo_cjk_bigrams": {"harness": False, "cjk": True, "exclude_function_words": False},
        "hypo_exclude_function_words_p1": {
            "harness": False,
            "cjk": False,
            "exclude_function_words": True,
        },
    }

    results: dict[str, Any] = {}
    reports: dict[str, dict] = {}
    for arm_id, flags in arms.items():
        rep = _full_eval(src, cb, relaxed, **flags)
        reports[arm_id] = rep
        m = _metrics(rep)
        m.update(flags)
        m["vs_active_frozen"] = _delta_vs(frozen, m)
        if arm_id != "active_baseline":
            base_cases = (reports["active_baseline"].get("compression_metrics") or {}).get("cases") or []
            alt_cases = (rep.get("compression_metrics") or {}).get("cases") or []
            m["hangul_cmp2_011_040_case_deltas"] = _hangul_case_deltas(base_cases, alt_cases)
            m["hangul_cases_with_metric_change"] = sum(
                1 for r in m["hangul_cmp2_011_040_case_deltas"] if r["changed"]
            )
        results[arm_id] = m

    doc = {
        "schema": "lexicon_hangul_p0_golden40_reeval_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "would_change_active": False,
        "lexicon_path": str(cb.relative_to(ROOT)).replace("\\", "/"),
        "active_frozen_metrics": frozen,
        "active_frozen_pointer": str(ACTIVE.relative_to(ROOT)).replace("\\", "/"),
        "arms": results,
        "verdict": {
            "harness_moves_golden40_aggregate": results["hypo_hangul_harness_v1"]["vs_active_frozen"][
                "strict_beat_both_axes"
            ]
            or (
                results["hypo_hangul_harness_v1"]["vs_active_frozen"]["delta_saving_pp"] != 0
                or results["hypo_hangul_harness_v1"]["vs_active_frozen"]["delta_jaccard_pp"] != 0
            ),
            "harness_moves_hangul_case_metrics": results["hypo_hangul_harness_v1"]["hangul_cases_with_metric_change"]
            > 0,
            "cjk_moves_golden40_aggregate": (
                results["hypo_cjk_bigrams"]["vs_active_frozen"]["delta_saving_pp"] != 0
                or results["hypo_cjk_bigrams"]["vs_active_frozen"]["delta_jaccard_pp"] != 0
            ),
            "function_word_exclude_moves_aggregate": (
                results["hypo_exclude_function_words_p1"]["vs_active_frozen"]["delta_saving_pp"] != 0
                or results["hypo_exclude_function_words_p1"]["vs_active_frozen"]["delta_jaccard_pp"] != 0
            ),
            "recommendation": (
                "Harness improves lookup but Golden-40 KPI unchanged — wire must_keep→saving path or ko ingest before ACTIVE talk."
                if results["hypo_hangul_harness_v1"]["hangul_cases_with_metric_change"] == 0
                and results["hypo_hangul_harness_v1"]["vs_active_frozen"]["delta_saving_pp"] == 0
                else "Re-run promotion gate with human sign-off if aggregate beat holds."
            ),
        },
        "pointers": {
            "p0_before_after": "reports/lexicon_hangul_p0_before_after_v1_latest.json",
            "overlay_pilot": "reports/lexicon_hangul_overlay_pilot_v1_latest.json",
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "would_change_active": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
