#!/usr/bin/env python3
"""[HYPO] Multi-corpus 41k/bridge/caps combo grid — find + validate best B-track profile.

Golden-40 (evaluate_report) + field JSONL corpora. Never writes Track A ACTIVE report.
Output: reports/compression_41k_best_combo_grid_v1_latest.json
"""

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

from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402

INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
DEFAULT_OUT = ROOT / "reports/compression_41k_best_combo_grid_v1_latest.json"
POLICY_FLOOR = 0.47
JACCARD_FLOOR_FIELD = 0.73

FIELD_CORPORA: list[dict[str, str]] = [
    {
        "corpus_id": "public_open_web_v1",
        "path": "data/compression/stateless_poc_prospect_public-open-web-v1_v1.jsonl",
    },
    {
        "corpus_id": "wtt_premium_cs_customer_v1",
        "path": "data/compression/stateless_poc_prospect_wtt-premium-cs-customer-v1_v1.jsonl",
    },
    {
        "corpus_id": "open_structured_long_v1",
        "path": "data/compression/stateless_poc_open_structured_long_v1.jsonl",
    },
]

FORBIDDEN_WRITE = frozenset({ACTIVE.resolve()})


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _active_run_config() -> dict[str, Any]:
    return dict(_load(ACTIVE).get("run_config") or {})


def _decision_common() -> dict[str, Any]:
    base = _load(BASELINE_V2)
    dec = _load(DECISION)
    sel = dec.get("selected_candidate") or {}
    baseline_j = float(base.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0))
    threshold_pp = float(dec.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))
    rc = _active_run_config()
    return {
        "mode": str(rc.get("mode") or "experimental"),
        "strategy": str(rc.get("strategy") or sel.get("strategy") or "A"),
        "intensity": str(rc.get("intensity") or sel.get("intensity") or "extreme"),
        "must_keep": set(rc.get("must_keep_terms") or ["사상의학", "체질", "sasang", "myeongri", "bible"]),
        "jaccard_drop_threshold_pp": threshold_pp,
        "baseline_avg_jaccard": baseline_j,
        "general_max_saving_rate": float(rc.get("general_max_saving_rate", sel.get("general_max_saving_rate", 0.35))),
        "sensitive_max_saving_rate": float(rc.get("sensitive_max_saving_rate", sel.get("sensitive_max_saving_rate", 0.3))),
        "hangul_max_saving_rate": float(rc.get("hangul_max_saving_rate", sel.get("hangul_max_saving_rate", 0.6))),
        "use_hangul_principle": bool(rc.get("use_hangul_principle", False)),
        "use_domain_router": bool(rc.get("use_domain_router", True)),
        "include_gematria_metadata": bool(rc.get("include_gematria_metadata", True)),
        "include_gematria_4d_bridge": bool(rc.get("include_gematria_4d_bridge", True)),
        "include_cee_core": bool(rc.get("include_cee_core", True)),
    }


def _combo_variants() -> list[dict[str, Any]]:
    rc = _active_run_config()
    base_lex = bool(rc.get("use_master_codebook_lexicon_v1", True))
    relaxed = dict(rc.get("domain_relaxed_max_saving_overrides") or {})
    allow = rc.get("domain_relaxed_max_saving_case_allowlist")
    allow_f = frozenset(allow) if allow else None

    def _v(combo_id: str, label: str, **kw: Any) -> dict[str, Any]:
        row = {
            "combo_id": combo_id,
            "label_ko": label,
            "use_master_codebook_lexicon_v1": base_lex,
            "apply_gematria_4d_bridge_policy": False,
            "bridge_policy_domain_allowlist": None,
            "domain_relaxed_max_saving_overrides": relaxed,
            "domain_relaxed_max_saving_case_allowlist": allow_f,
            "enable_candidate_pool_expansion": False,
            "enable_router_blend_candidate": False,
        }
        row.update(kw)
        return row

    return [
        _v("active_frozen_parity", "ACTIVE 동결 parity (41k ON, bridge OFF, ssot relaxed)"),
        _v("lexicon_off_same_caps", "41k OFF · 동일 caps/relaxed", use_master_codebook_lexicon_v1=False),
        _v(
            "lexicon_off_no_relaxed",
            "41k OFF · ssot relaxed 제거",
            use_master_codebook_lexicon_v1=False,
            domain_relaxed_max_saving_overrides={},
            domain_relaxed_max_saving_case_allowlist=None,
        ),
        _v("bridge_on_full", "41k ON · bridge policy ON (전 도메인)", apply_gematria_4d_bridge_policy=True),
        _v(
            "bridge_selective_ssot",
            "41k ON · bridge ON · ssot 도메인만",
            apply_gematria_4d_bridge_policy=True,
            bridge_policy_domain_allowlist=frozenset({"ssot"}),
        ),
        _v(
            "candidate_pool_on",
            "41k ON · candidate pool expansion",
            enable_candidate_pool_expansion=True,
        ),
        _v(
            "lexicon_off_candidate_pool",
            "41k OFF · candidate pool",
            use_master_codebook_lexicon_v1=False,
            enable_candidate_pool_expansion=True,
        ),
        _v(
            "router_blend_on",
            "41k ON · router blend candidate",
            enable_router_blend_candidate=True,
        ),
        _v(
            "caps_higher_saving",
            "41k ON · caps +5pp (general/sensitive/hangul)",
            general_max_saving_rate_override=0.40,
            sensitive_max_saving_rate_override=0.35,
            hangul_max_saving_rate_override=0.65,
        ),
        _v(
            "lexicon_on_no_relaxed",
            "41k ON · ssot relaxed 제거",
            domain_relaxed_max_saving_overrides={},
            domain_relaxed_max_saving_case_allowlist=None,
        ),
    ]


def _eval_doc(doc: dict[str, Any], variant: dict[str, Any], *, source_label: str) -> dict[str, Any]:
    common = _decision_common()
    for key in (
        "general_max_saving_rate",
        "sensitive_max_saving_rate",
        "hangul_max_saving_rate",
    ):
        ov = variant.get(f"{key}_override")
        if ov is not None:
            common[key] = float(ov)

    rep = evaluate_report(
        doc,
        source_input=source_label,
        use_master_codebook_lexicon_v1=bool(variant.get("use_master_codebook_lexicon_v1", True)),
        apply_gematria_4d_bridge_policy=bool(variant.get("apply_gematria_4d_bridge_policy", False)),
        bridge_policy_domain_allowlist=variant.get("bridge_policy_domain_allowlist"),
        domain_relaxed_max_saving_overrides=variant.get("domain_relaxed_max_saving_overrides"),
        domain_relaxed_max_saving_case_allowlist=variant.get("domain_relaxed_max_saving_case_allowlist"),
        domain_relaxed_max_saving_exclude_case_ids=variant.get("domain_relaxed_max_saving_exclude_case_ids"),
        enable_candidate_pool_expansion=bool(variant.get("enable_candidate_pool_expansion", False)),
        enable_router_blend_candidate=bool(variant.get("enable_router_blend_candidate", False)),
        **common,
    )
    cm = rep.get("compression_metrics") or {}
    cases = cm.get("cases") or []
    pass_j = sum(
        1
        for c in cases
        if float(c.get("reconstruction_fidelity_jaccard") or 0) >= JACCARD_FLOOR_FIELD
    )
    return {
        "global_token_saving_rate": float(cm.get("global_token_saving_rate") or 0),
        "avg_reconstruction_fidelity_jaccard": float(cm.get("avg_reconstruction_fidelity_jaccard") or 0),
        "min_reconstruction_fidelity_jaccard": float(cm.get("min_reconstruction_fidelity_jaccard") or 0),
        "avg_sensitive_integrity": float(cm.get("avg_sensitive_integrity") or 0),
        "case_count": len(cases),
        "cases_pass_jaccard_floor": pass_j,
        "case_pass_rate": round(pass_j / len(cases), 4) if cases else 0.0,
        "ultra_saving_policy_ok": float(cm.get("global_token_saving_rate") or 0) >= POLICY_FLOOR,
    }


def _jsonl_to_eval_doc(path: Path, max_rows: int) -> dict[str, Any]:
    cases: list[dict[str, str]] = []
    if not path.is_file():
        return {"compression_cases": cases}
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines()):
        if not line.strip() or len(cases) >= max_rows:
            break
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        text = None
        for key in ("text", "raw_text", "content", "body"):
            v = obj.get(key)
            if isinstance(v, str) and v.strip():
                text = v
                break
        if not text:
            continue
        cases.append({"id": str(obj.get("id") or f"row_{i}"), "raw_text": text})
    return {"compression_cases": cases}


def _composite_score(golden: dict[str, Any], field: list[dict[str, Any]]) -> float:
    g_floor = 1.0 if golden.get("ultra_saving_policy_ok") else 0.0
    g_j = float(golden.get("avg_reconstruction_fidelity_jaccard") or 0)
    field_rates = [float(f.get("case_pass_rate") or 0) for f in field if f.get("case_count")]
    field_saving = [
        float(f.get("global_token_saving_rate") or 0) for f in field if f.get("case_count")
    ]
    field_j = [
        float(f.get("avg_reconstruction_fidelity_jaccard") or 0) for f in field if f.get("case_count")
    ]
    mean_pass = sum(field_rates) / len(field_rates) if field_rates else 0.0
    mean_save = sum(field_saving) / len(field_saving) if field_saving else 0.0
    mean_j = sum(field_j) / len(field_j) if field_j else 0.0
    return round(
        0.20 * g_floor
        + 0.15 * min(g_j, 1.0)
        + 0.40 * mean_pass
        + 0.15 * min(mean_save / 0.35, 1.0)
        + 0.10 * min(mean_j, 1.0),
        6,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-field-rows", type=int, default=30)
    ap.add_argument("--top-k-validate", type=int, default=5)
    args = ap.parse_args()
    if args.output.resolve() in FORBIDDEN_WRITE:
        print("Refusing to overwrite Track A ACTIVE report path.", file=sys.stderr)
        return 2

    golden_src = _load(INPUT_V2)
    active_cm = _load(ACTIVE).get("compression_metrics") or {}
    variants = _combo_variants()

    golden_rows: list[dict[str, Any]] = []
    for v in variants:
        combo_id = str(v["combo_id"])
        try:
            metrics = _eval_doc(golden_src, v, source_label=str(INPUT_V2.relative_to(ROOT)))
        except Exception as exc:  # noqa: BLE001
            golden_rows.append({"combo_id": combo_id, "error": str(exc)})
            continue
        golden_rows.append(
            {
                "combo_id": combo_id,
                "label_ko": v.get("label_ko"),
                "config": {
                    k: (
                        sorted(list(v[k]))
                        if isinstance(v.get(k), frozenset)
                        else v.get(k)
                    )
                    for k in v
                    if k not in {"combo_id", "label_ko"}
                    and not str(k).endswith("_override")
                },
                "golden40": metrics,
            }
        )

    golden_rows.sort(
        key=lambda r: _composite_score(r.get("golden40") or {}, []),
        reverse=True,
    )
    top_ids = [r["combo_id"] for r in golden_rows[: max(1, args.top_k_validate)] if "golden40" in r]
    variant_by_id = {str(v["combo_id"]): v for v in variants}

    field_docs: dict[str, dict[str, Any]] = {}
    for spec in FIELD_CORPORA:
        p = ROOT / spec["path"]
        field_docs[spec["corpus_id"]] = _jsonl_to_eval_doc(p, args.max_field_rows)

    validated: list[dict[str, Any]] = []
    for combo_id in top_ids:
        v = variant_by_id[combo_id]
        field_metrics: list[dict[str, Any]] = []
        for spec in FIELD_CORPORA:
            cid = spec["corpus_id"]
            doc = field_docs[cid]
            n = len(doc.get("compression_cases") or [])
            if n == 0:
                field_metrics.append({"corpus_id": cid, "case_count": 0, "skipped": True})
                continue
            try:
                m = _eval_doc(doc, v, source_label=spec["path"])
            except Exception as exc:  # noqa: BLE001
                field_metrics.append({"corpus_id": cid, "error": str(exc)})
                continue
            field_metrics.append({"corpus_id": cid, **m})
        golden = next(r["golden40"] for r in golden_rows if r.get("combo_id") == combo_id)
        validated.append(
            {
                "combo_id": combo_id,
                "label_ko": v.get("label_ko"),
                "composite_score": _composite_score(golden, field_metrics),
                "golden40": golden,
                "field_corpora": field_metrics,
            }
        )

    validated.sort(key=lambda r: float(r.get("composite_score") or 0), reverse=True)
    best = validated[0] if validated else None
    frozen = {
        "global_token_saving_rate": active_cm.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": active_cm.get("avg_reconstruction_fidelity_jaccard"),
    }

    report: dict[str, Any] = {
        "schema": "compression_41k_best_combo_grid_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_active_untouched": True,
        "policy_floor": POLICY_FLOOR,
        "field_jaccard_floor": JACCARD_FLOOR_FIELD,
        "scoring_note": "Composite weights field pass rate 40% > golden floor 20% — anti Golden-40-only overfit.",
        "frozen_active_baseline": frozen,
        "combo_count": len(variants),
        "golden40_ranking": golden_rows,
        "validated_top_k": validated,
        "best_combo": best,
        "verdict_ko": None,
        "reproduce": f"py scripts/run_compression_41k_best_combo_grid_v1.py --output {args.output.relative_to(ROOT)}",
    }

    if best:
        bg = best.get("golden40") or {}
        delta_save = float(bg.get("global_token_saving_rate") or 0) - float(
            frozen.get("global_token_saving_rate") or 0
        )
        delta_j = float(bg.get("avg_reconstruction_fidelity_jaccard") or 0) - float(
            frozen.get("avg_reconstruction_fidelity_jaccard") or 0
        )
        report["verdict_ko"] = (
            f"best={best.get('combo_id')} composite={best.get('composite_score')} "
            f"golden saving={bg.get('global_token_saving_rate')} j={bg.get('avg_reconstruction_fidelity_jaccard')} "
            f"vs ACTIVE Δsave={delta_save:+.4f} Δj={delta_j:+.4f}; "
            "research_only — does not auto-promote ACTIVE."
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    if report.get("verdict_ko"):
        print(report["verdict_ko"])
    return 0 if best else 1


if __name__ == "__main__":
    raise SystemExit(main())
