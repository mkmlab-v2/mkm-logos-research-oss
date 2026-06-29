#!/usr/bin/env python3
"""B-track pilot: Golden-40 Hangul cases — default \\w+ lookup vs include_cjk_bigrams ([HYPO])."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.master_codebook_lexicon_v1_bridge import (  # noqa: E402
    lexicon_hits_for_text,
    resolve_latest_codebook_path,
)
from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402

INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
OUT = ROOT / "reports/lexicon_hangul_cjk_parallel_pilot_v1_latest.json"
HANGUL_CASE_PREFIX = "cmp2_0"  # cmp2_011+


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hangul_ratio(raw: str) -> float:
    import re

    h = re.compile(r"[\uac00-\ud7a3]")
    n = len(h.findall(raw))
    return n / max(len(raw), 1)


def _bench_subset_metrics(src: dict, case_ids: set[str], *, use_cjk: bool) -> dict:
    baseline = json.loads(BASELINE_V2.read_text(encoding="utf-8"))
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    selected = decision.get("selected_candidate") or {}
    baseline_j = float(
        baseline.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    threshold_pp = float(decision.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))
    subset_cases = [c for c in (src.get("compression_cases") or []) if str(c.get("id")) in case_ids]
    sub_doc = {"compression_cases": subset_cases, "fusion_answer_cases": []}
    report = evaluate_report(
        sub_doc,
        source_input=str(INPUT_V2.relative_to(ROOT)).replace("\\", "/"),
        mode="experimental",
        strategy=str(selected.get("strategy", "A")),
        intensity=str(selected.get("intensity", "extreme")),
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_j,
        general_max_saving_rate=float(selected.get("general_max_saving_rate", 0.35)),
        sensitive_max_saving_rate=float(selected.get("sensitive_max_saving_rate", 0.3)),
        hangul_max_saving_rate=float(selected.get("hangul_max_saving_rate", 0.6)),
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        master_codebook_lexicon_include_cjk_bigrams=use_cjk,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        apply_gematria_4d_bridge_policy=False,
        include_cee_core=True,
    )
    cm = report.get("compression_metrics") or {}
    return {
        "case_count": len(subset_cases),
        "global_token_saving_rate": cm.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
        "include_cjk_bigrams": use_cjk,
    }


def main() -> int:
    import re

    cb = resolve_latest_codebook_path()
    if cb is None:
        print("ABORT: lexicon missing")
        return 1

    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    cases = src.get("compression_cases") or []
    hangul_ids = {
        str(c.get("id"))
        for c in cases
        if _hangul_ratio(str(c.get("raw_text", ""))) >= 0.15
        or (str(c.get("id") or "") >= "cmp2_011")
    }

    per_case = []
    for c in cases:
        cid = str(c.get("id", ""))
        if cid not in hangul_ids:
            continue
        raw = str(c.get("raw_text", ""))
        d_hits, d_meta = lexicon_hits_for_text(raw, cb, include_cjk_bigrams=False)
        c_hits, c_meta = lexicon_hits_for_text(raw, cb, include_cjk_bigrams=True)
        per_case.append(
            {
                "id": cid,
                "hangul_char_ratio": round(_hangul_ratio(raw), 4),
                "default_hit_count": len(d_hits),
                "cjk_bigram_hit_count": len(c_hits),
                "delta_hits": len(c_hits) - len(d_hits),
                "new_hits_sample": sorted(c_hits - d_hits)[:12],
            }
        )

    metrics_default = _bench_subset_metrics(src, hangul_ids, use_cjk=False)
    metrics_cjk = _bench_subset_metrics(src, hangul_ids, use_cjk=True)

    doc = {
        "schema": "lexicon_hangul_cjk_parallel_pilot_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_active_write": False,
        "hypo_label": "[HYPO]",
        "lexicon_path": str(cb.relative_to(ROOT)).replace("\\", "/"),
        "hangul_case_count": len(per_case),
        "aggregate_hit_lift": {
            "total_default_hits": sum(r["default_hit_count"] for r in per_case),
            "total_cjk_bigram_hits": sum(r["cjk_bigram_hit_count"] for r in per_case),
            "cases_with_delta_gt_0": sum(1 for r in per_case if r["delta_hits"] > 0),
        },
        "per_case": per_case,
        "hangul_subset_compression_pilot": {
            "default_w_only": metrics_default,
            "with_cjk_bigrams_flag": metrics_cjk,
        },
        "verdict": {
            "promote_to_track_a": False,
            "recommendation": "Wire include_cjk_bigrams for Hangul bench slice only after human review",
        },
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "hangul_cases": len(per_case), "lift_cases": doc["aggregate_hit_lift"]["cases_with_delta_gt_0"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
