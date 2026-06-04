#!/usr/bin/env python3
"""P0 Hangul cmp2_011–040: ACTIVE baseline vs [HYPO] harness / CJK bigrams — evidence only."""
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
from scripts.core.master_codebook_lexicon_v1_bridge import (  # noqa: E402
    lexicon_hits_for_text,
    resolve_latest_codebook_path,
)
from scripts.run_ultra_compression_default import INPUT_V2  # noqa: E402

ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
OUT = ROOT / "reports/lexicon_hangul_p0_before_after_v1_latest.json"
HANGUL_CASE_IDS = {f"cmp2_{i:03d}" for i in range(11, 41)}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hit_count(raw: str, cb: Path, *, harness: bool, cjk: bool) -> int:
    hits, _ = lexicon_hits_for_text(
        raw,
        cb,
        min_token_len=2,
        include_hangul_tokenizer_harness=harness,
        include_cjk_bigrams=cjk,
    )
    return len(hits)


def _subset_eval(
    src: dict[str, Any],
    cb: Path,
    *,
    harness: bool,
    cjk: bool,
    relaxed: tuple,
) -> dict[str, Any]:
    domain_relaxed, allow, exclude = relaxed
    sub = {"compression_cases": [c for c in (src.get("compression_cases") or []) if str(c.get("id")) in HANGUL_CASE_IDS]}
    report = _run_eval(
        sub,
        lexicon_path=cb,
        domain_relaxed=domain_relaxed,
        relaxed_case_allowlist=allow,
        relaxed_case_exclude=exclude,
        include_hangul_tokenizer_harness=harness,
    )
    if cjk:
        from scripts.core.multilens_bridge_policy_env import env_apply_gematria_4d_bridge_policy
        from scripts.report_multilens_performance_eval import evaluate_report
        from scripts.run_ultra_compression_default import BASELINE_V2, DECISION
        from scripts.ultra_compression_track_a_policy_floor_v1 import apply_promoted_policy_floor_to_quality_gate

        baseline_doc = json.loads(BASELINE_V2.read_text(encoding="utf-8"))
        decision_doc = json.loads(DECISION.read_text(encoding="utf-8"))
        selected = decision_doc.get("selected_candidate") or {}
        baseline_avg_jaccard = float(
            baseline_doc.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
        )
        threshold_pp = float(decision_doc.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))
        active_rc = json.loads(ACTIVE.read_text(encoding="utf-8")).get("run_config") or {}
        report = evaluate_report(
            sub,
            source_input=str(INPUT_V2.relative_to(ROOT)).replace("\\", "/"),
            mode=str(active_rc.get("mode", "experimental")),
            strategy=str(active_rc.get("strategy", "A")),
            intensity=str(active_rc.get("intensity", "extreme")),
            must_keep=set(active_rc.get("must_keep_terms") or []),
            jaccard_drop_threshold_pp=threshold_pp,
            baseline_avg_jaccard=baseline_avg_jaccard,
            general_max_saving_rate=float(active_rc.get("general_max_saving_rate", 0.35)),
            sensitive_max_saving_rate=float(active_rc.get("sensitive_max_saving_rate", 0.3)),
            hangul_max_saving_rate=float(active_rc.get("hangul_max_saving_rate", 0.6)),
            use_domain_router=bool(active_rc.get("use_domain_router", True)),
            use_master_codebook_lexicon_v1=True,
            master_codebook_lexicon_path=str(cb.resolve()),
            master_codebook_lexicon_include_cjk_bigrams=True,
            master_codebook_lexicon_include_hangul_tokenizer_harness=False,
            master_codebook_lexicon_exclude_function_words=bool(
                active_rc.get("master_codebook_lexicon_exclude_function_words", False)
            ),
            include_gematria_metadata=bool(active_rc.get("include_gematria_metadata", True)),
            include_gematria_4d_bridge=bool(active_rc.get("include_gematria_4d_bridge", True)),
            apply_gematria_4d_bridge_policy=bool(active_rc.get("apply_gematria_4d_bridge_policy", False)),
            domain_relaxed_max_saving_overrides=domain_relaxed or None,
            domain_relaxed_max_saving_case_allowlist=allow,
            domain_relaxed_max_saving_exclude_case_ids=exclude,
            include_cee_core=bool(active_rc.get("include_cee_core", True)),
        )
        apply_promoted_policy_floor_to_quality_gate(report)
    return report


def _per_case_rows(src: dict[str, Any], cb: Path, relaxed: tuple) -> dict[str, dict[str, Any]]:
    domain_relaxed, allow, exclude = relaxed
    modes = {
        "active_baseline": (False, False),
        "hypo_hangul_harness_v1": (True, False),
        "hypo_cjk_bigrams": (False, True),
    }
    reports: dict[str, dict[str, Any]] = {}
    for name, (harness, cjk) in modes.items():
        reports[name] = _subset_eval(src, cb, harness=harness, cjk=cjk, relaxed=relaxed)

    by_id: dict[str, dict[str, Any]] = {}
    for c in src.get("compression_cases") or []:
        cid = str(c.get("id", ""))
        if cid not in HANGUL_CASE_IDS:
            continue
        raw = str(c.get("raw_text", ""))
        row: dict[str, Any] = {"id": cid, "modes": {}}
        for name, (harness, cjk) in modes.items():
            rep = reports[name]
            case_m = next((x for x in (rep.get("compression_metrics") or {}).get("cases") or [] if str(x.get("id")) == cid), {})
            row["modes"][name] = {
                "lexicon_hit_count": _hit_count(raw, cb, harness=harness, cjk=cjk),
                "token_saving_rate": case_m.get("token_saving_rate"),
                "reconstruction_fidelity_jaccard": case_m.get("reconstruction_fidelity_jaccard"),
            }
        base = row["modes"]["active_baseline"]
        for alt in ("hypo_hangul_harness_v1", "hypo_cjk_bigrams"):
            m = row["modes"][alt]
            m["delta_vs_active_baseline"] = {
                "lexicon_hit_count": (m.get("lexicon_hit_count") or 0) - (base.get("lexicon_hit_count") or 0),
                "token_saving_rate": None
                if m.get("token_saving_rate") is None or base.get("token_saving_rate") is None
                else round(float(m["token_saving_rate"]) - float(base["token_saving_rate"]), 6),
                "reconstruction_fidelity_jaccard": None
                if m.get("reconstruction_fidelity_jaccard") is None or base.get("reconstruction_fidelity_jaccard") is None
                else round(float(m["reconstruction_fidelity_jaccard"]) - float(base["reconstruction_fidelity_jaccard"]), 6),
            }
        by_id[cid] = row
    return by_id


def main() -> int:
    if not INPUT_V2.is_file() or not ACTIVE.is_file():
        print("ABORT: missing INPUT_V2 or ACTIVE report")
        return 1
    cb = resolve_latest_codebook_path()
    if cb is None:
        print("ABORT: lexicon missing")
        return 1

    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    active_doc = json.loads(ACTIVE.read_text(encoding="utf-8"))
    active_cm = active_doc.get("compression_metrics") or {}
    active_rc = active_doc.get("run_config") or {}
    relaxed = _load_signoff_relaxed()

    aggregate: dict[str, Any] = {}
    for name, harness, cjk in (
        ("active_baseline", False, False),
        ("hypo_hangul_harness_v1", True, False),
        ("hypo_cjk_bigrams", False, True),
    ):
        rep = _subset_eval(src, cb, harness=harness, cjk=cjk, relaxed=relaxed)
        aggregate[name] = {
            **_metrics(rep),
            "include_hangul_tokenizer_harness": harness,
            "include_cjk_bigrams": cjk,
        }

    per_case = list(_per_case_rows(src, cb, relaxed).values())
    per_case.sort(key=lambda r: str(r["id"]))

    base_hits = sum(r["modes"]["active_baseline"]["lexicon_hit_count"] for r in per_case)
    harness_hits = sum(r["modes"]["hypo_hangul_harness_v1"]["lexicon_hit_count"] for r in per_case)
    cjk_hits = sum(r["modes"]["hypo_cjk_bigrams"]["lexicon_hit_count"] for r in per_case)

    doc = {
        "schema": "lexicon_hangul_p0_before_after_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "would_change_active": False,
        "case_ids": sorted(HANGUL_CASE_IDS),
        "lexicon_path": str(cb.relative_to(ROOT)).replace("\\", "/"),
        "active_frozen_pointer": str(ACTIVE.relative_to(ROOT)).replace("\\", "/"),
        "active_frozen_metrics_full_golden40": {
            "global_token_saving_rate": active_cm.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": active_cm.get("avg_reconstruction_fidelity_jaccard"),
        },
        "active_run_config_echo": {
            "include_hangul_tokenizer_harness": active_rc.get("master_codebook_lexicon_include_hangul_tokenizer_harness"),
            "include_cjk_bigrams": active_rc.get("master_codebook_lexicon_include_cjk_bigrams"),
            "apply_gematria_4d_bridge_policy": active_rc.get("apply_gematria_4d_bridge_policy"),
        },
        "subset_aggregate_cmp2_011_040": aggregate,
        "subset_delta_vs_active_baseline": {
            "hypo_hangul_harness_v1": {
                "global_token_saving_rate": round(
                    float(aggregate["hypo_hangul_harness_v1"]["global_token_saving_rate"] or 0)
                    - float(aggregate["active_baseline"]["global_token_saving_rate"] or 0),
                    6,
                ),
                "avg_reconstruction_fidelity_jaccard": round(
                    float(aggregate["hypo_hangul_harness_v1"]["avg_reconstruction_fidelity_jaccard"] or 0)
                    - float(aggregate["active_baseline"]["avg_reconstruction_fidelity_jaccard"] or 0),
                    6,
                ),
                "total_lexicon_hits": harness_hits - base_hits,
            },
            "hypo_cjk_bigrams": {
                "global_token_saving_rate": round(
                    float(aggregate["hypo_cjk_bigrams"]["global_token_saving_rate"] or 0)
                    - float(aggregate["active_baseline"]["global_token_saving_rate"] or 0),
                    6,
                ),
                "avg_reconstruction_fidelity_jaccard": round(
                    float(aggregate["hypo_cjk_bigrams"]["avg_reconstruction_fidelity_jaccard"] or 0)
                    - float(aggregate["active_baseline"]["avg_reconstruction_fidelity_jaccard"] or 0),
                    6,
                ),
                "total_lexicon_hits": cjk_hits - base_hits,
            },
        },
        "per_case": per_case,
        "operator_lines": [
            "[HYPO] research_only · would_change_active=false",
            (
                f"subset_cases={len(per_case)} baseline_hits={base_hits} "
                f"harness_hits={harness_hits} cjk_hits={cjk_hits}"
            ),
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "would_change_active": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
