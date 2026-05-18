#!/usr/bin/env python3
"""B-track: health/hangul domain-relax signoff *candidate* pack (does not replace Track A active)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_health_domain_signoff_candidate_latest.json"
SWEEP = ROOT / "docs/final/artifacts/compression_low_saving_local_cap_sweep_v1_latest.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
CASE_ID = "cmp2_011"
PROPOSED_VARIANT = "health_hangul_relaxed_cap_0.50"
POLICY_FLOOR = 0.47


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _case_row_from_report(report: dict[str, Any], case_id: str) -> dict[str, Any] | None:
    for c in (report.get("compression_metrics") or {}).get("cases") or []:
        if isinstance(c, dict) and str(c.get("id")) == case_id:
            return {
                "token_saving_rate": c.get("token_saving_rate"),
                "jaccard": c.get("reconstruction_fidelity_jaccard"),
                "domain": (c.get("route") or {}).get("domain"),
                "shard_id": (c.get("route") or {}).get("shard_id"),
                "lexicon_hit_count": ((c.get("route") or {}).get("master_codebook_lexicon_v1") or {}).get(
                    "hit_count"
                ),
            }
    return None


def _single_case_evaluate(raw_text: str, *, routing_profile: str) -> dict[str, Any]:
    from scripts.compression_v2_routing_profile_v1 import routing_profile_kwargs
    from scripts.compression_token_api_stub import _baseline_avg_jaccard, _decision_selected_profile
    from scripts.report_multilens_performance_eval import evaluate_report

    selected = _decision_selected_profile()
    route_kw = routing_profile_kwargs(routing_profile)  # type: ignore[arg-type]
    eval_extra = {
        k: v
        for k, v in route_kw.items()
        if k
        not in (
            "routing_profile",
            "promotion_signoff_path",
            "sweep_pointer",
            "note",
            "hypothesis_tier",
            "research_only",
            "routing_profile_degraded",
        )
    }
    doc = {
        "compression_cases": [
            {
                "id": CASE_ID,
                "raw_text": raw_text,
                "compressed_text": "",
                "reconstructed_text": "",
            }
        ],
        "fusion_answer_cases": [],
    }
    rep = evaluate_report(
        doc,
        source_input=f"single_case:{CASE_ID}",
        mode="experimental",
        strategy=str(selected.get("strategy", "A")),
        intensity=str(selected.get("intensity", "extreme")),
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=1.5,
        baseline_avg_jaccard=_baseline_avg_jaccard(),
        general_max_saving_rate=float(selected["general_max_saving_rate"])
        if selected.get("general_max_saving_rate") is not None
        else None,
        sensitive_max_saving_rate=float(selected["sensitive_max_saving_rate"])
        if selected.get("sensitive_max_saving_rate") is not None
        else None,
        hangul_max_saving_rate=float(selected["hangul_max_saving_rate"])
        if selected.get("hangul_max_saving_rate") is not None
        else None,
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        include_cee_core=True,
        apply_gematria_4d_bridge_policy=False,
        **eval_extra,
    )
    cases = (rep.get("compression_metrics") or {}).get("cases") or []
    first = cases[0] if cases else {}
    return {
        "token_saving_rate": first.get("token_saving_rate"),
        "jaccard": first.get("reconstruction_fidelity_jaccard"),
        "global_token_saving_rate": (rep.get("compression_metrics") or {}).get("global_token_saving_rate"),
    }


def build() -> dict[str, Any]:
    sweep = _load(SWEEP)
    variant = None
    for row in sweep.get("all_variants") or []:
        if isinstance(row, dict) and row.get("id") == PROPOSED_VARIANT:
            variant = row
            break
    active = _load(ACTIVE) if ACTIVE.is_file() else {}
    active_global = float((active.get("compression_metrics") or {}).get("global_token_saving_rate") or 0)
    cmp2_active = _case_row_from_report(active, CASE_ID)

    raw = ""
    for case in _load(INPUT_V2).get("compression_cases") or []:
        if isinstance(case, dict) and str(case.get("id")) == CASE_ID:
            raw = str(case.get("raw_text") or "")
            break

    b_track_single = _single_case_evaluate(raw, routing_profile="b_track_domain_relax")
    default_single = _single_case_evaluate(raw, routing_profile="default")

    bench_promotion_eligible = False
    if variant:
        bench_promotion_eligible = bool(variant.get("ultra_saving_policy_ok"))

    return {
        "schema": "mkm_inter_agent_health_domain_signoff_candidate_v1",
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "hypothesis_tier": "B",
        "track_wall": "b_track_research_only",
        "rq": "RQ-016-A-plan",
        "does_not_replace_track_a_active": True,
        "current_track_a_signoff": "multilens_ultra_compression_track_a_promotion_signoff_v1_latest.json (ssot top5 only)",
        "proposed_variant_id": PROPOSED_VARIANT,
        "proposed_run_config": (variant or {}).get("knobs"),
        "sweep_evidence": {
            "path": SWEEP.relative_to(ROOT).as_posix(),
            "global_token_saving_rate": variant.get("global_token_saving_rate") if variant else None,
            "ultra_saving_policy_ok": variant.get("ultra_saving_policy_ok") if variant else None,
            "avg_jaccard": variant.get("avg_reconstruction_fidelity_jaccard") if variant else None,
            "policy_floor": POLICY_FLOOR,
        },
        "cmp2_011_focus": {
            "active_report_row": cmp2_active,
            "v2_api_default": default_single,
            "v2_api_b_track_domain_relax": b_track_single,
            "savings_delta_b_track_minus_default": (
                round(
                    float(b_track_single.get("token_saving_rate") or 0)
                    - float(default_single.get("token_saving_rate") or 0),
                    6,
                )
                if b_track_single.get("token_saving_rate") is not None
                else None
            ),
        },
        "bench_promotion_eligible_without_human": bench_promotion_eligible,
        "human_review_required": True,
        "recommended_action": (
            "Human gate: do not merge into Track A active without commander sign-off. "
            "health_hangul_relaxed_cap_0.50 misses 0.47 floor on full 40-case sweep; "
            "use for inter-agent B-track routing_profile=b_track_domain_relax only until re-sweep passes."
        ),
        "public_copy_ko": (
            "건강·한글 도메인 완화 캡은 연구 후보이며, 현재 동결 Track A 벤치(약 47.5%)를 대체하지 않습니다."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.out_json),
                "bench_promotion_eligible": doc.get("bench_promotion_eligible_without_human"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
