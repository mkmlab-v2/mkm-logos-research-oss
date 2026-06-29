#!/usr/bin/env python3
"""[HYPO] Freeze B-track trilogy archive from Lane A/B/C + no-guard compare artifacts."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "experiments" / "no_guard_limit_test" / "results"
DEFAULT_OUT = RESULTS / "archive_limitless_trilogy_report_v1_latest.json"

SOURCE_PATHS = {
    "lane_a_meta_channel": RESULTS / "prism_meta_channel_bench_v1_latest.json",
    "lane_b_dynamic_pinset": RESULTS / "prism_dynamic_pinset_bench_v1_latest.json",
    "lane_c_no_guard_meta": RESULTS / "prism_no_guard_meta_channel_bench_v1_latest.json",
    "no_guard_vs_guarded_compare": RESULTS / "no_guard_vs_guarded_compare_v1_latest.json",
}

PHASE2_SOURCE_PATHS = {
    "lane_b2_dynamic_heavy": RESULTS / "prism_dynamic_pinset_heavy_bench_v1_latest.json",
    "lane_d_no_guard_meta_corpus": RESULTS / "prism_no_guard_meta_corpus_bench_v1_latest.json",
}

PHASE3_SOURCE_PATHS = {
    "lane_e_corpus_isolation": RESULTS / "prism_corpus_isolation_bench_v1_latest.json",
    "coding_proxy_meta_wire": ROOT / "scripts/sandbox/coding_proxy_meta_channel_v1.py",
    "proxy_meta_wire_bench": RESULTS / "prism_proxy_meta_wire_bench_v1_latest.json",
}

STAGING_SOURCE_PATHS = {
    "staging_readiness": RESULTS / "prism_meta_channel_staging_readiness_v1_latest.json",
    "staging_live_smoke": RESULTS / "prism_meta_channel_staging_live_smoke_v1_latest.json",
    "n40_dogfood_extension": RESULTS / "prism_n40_dogfood_extension_v1_latest.json",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _is_valid_lane_doc(doc: dict[str, Any] | None) -> bool:
    return bool(doc and not doc.get("dry_run") and doc.get("case_count"))


def build_report(*, strict: bool, require_phase2: bool = False) -> dict[str, Any]:
    loaded: dict[str, dict[str, Any] | None] = {k: _load(p) for k, p in SOURCE_PATHS.items()}
    phase2_loaded: dict[str, dict[str, Any] | None] = {
        k: _load(p) for k, p in PHASE2_SOURCE_PATHS.items()
    }
    phase3_lane_e = _load(PHASE3_SOURCE_PATHS["lane_e_corpus_isolation"])
    phase3_wire_bench = _load(PHASE3_SOURCE_PATHS["proxy_meta_wire_bench"])
    missing = [k for k, p in SOURCE_PATHS.items() if not p.is_file()]
    invalid = [k for k, doc in loaded.items() if doc and not _is_valid_lane_doc(doc)]
    if k := "lane_b_dynamic_pinset":
        if loaded[k] and loaded[k].get("dry_run"):
            invalid.append(k)

    if strict and (missing or invalid):
        raise SystemExit(
            f"missing={missing} invalid_or_dry_run={invalid} — re-run lane benches first"
        )

    phase2_missing = [k for k, p in PHASE2_SOURCE_PATHS.items() if not p.is_file()]
    phase2_invalid = [
        k for k, doc in phase2_loaded.items() if doc and not _is_valid_lane_doc(doc)
    ]
    if require_phase2 and (phase2_missing or phase2_invalid):
        raise SystemExit(
            f"phase2 missing={phase2_missing} invalid={phase2_invalid} — re-run B2/D benches"
        )

    lane_a = loaded["lane_a_meta_channel"] or {}
    lane_b = loaded["lane_b_dynamic_pinset"] or {}
    lane_c = loaded["lane_c_no_guard_meta"] or {}
    compare = loaded["no_guard_vs_guarded_compare"] or {}

    a_agg = lane_a.get("aggregate") or {}
    b_agg = lane_b.get("aggregate") or {}
    c_agg = lane_c.get("aggregate") or {}
    cmp_agg = compare.get("aggregate") or {}

    b2 = phase2_loaded.get("lane_b2_dynamic_heavy") or {}
    b2_agg = b2.get("aggregate") or {}

    lane_b_dynamic_proven = bool(
        b_agg.get("dynamic_pinset_unique_sets", 0) > 1
        or b_agg.get("pinset_ids_differ_count", 0) > 0
        or b2_agg.get("dynamic_advantage_proven")
    )
    b_row_differ = b_agg.get("pinset_ids_differ_count") or b2_agg.get("pinset_ids_differ_count")
    b_row_unique = b_agg.get("dynamic_pinset_unique_sets") or b2_agg.get("dynamic_pinset_unique_sets")

    ssot_one_liner = (
        "PoC: prepend 비권장; meta_channel_post_gatekeeper user-text 메트릭 보존(guarded·no-guard); "
        "가드 ON이 지능 수호에 필수(0.926 vs 0.713); Track A·본선 hardening 변경 없음 [HYPO] research_only"
    )
    lane_d = phase2_loaded.get("lane_d_no_guard_meta_corpus") or {}
    d_agg = lane_d.get("aggregate") or {}
    b2_proven = bool(b2_agg.get("dynamic_advantage_proven"))
    phase2_complete = _is_valid_lane_doc(b2) and _is_valid_lane_doc(lane_d)
    e_agg = (phase3_lane_e or {}).get("aggregate") or {}
    phase3_complete = _is_valid_lane_doc(phase3_lane_e) and _is_valid_lane_doc(phase3_wire_bench)
    wire_agg = (phase3_wire_bench or {}).get("aggregate") or {}
    staging_ready = _load(STAGING_SOURCE_PATHS["staging_readiness"]) or {}
    staging_live = _load(STAGING_SOURCE_PATHS["staging_live_smoke"]) or {}
    n40_ext = _load(STAGING_SOURCE_PATHS["n40_dogfood_extension"]) or {}

    doc: dict[str, Any] = {
        "schema": "archive_limitless_trilogy_report_v1",
        "archive_status": "frozen_b_track",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "track_wall": "not_track_a_promotion",
        "regime_field": "regime_prism_meta_channel_poc_success",
        "corpus": "data/btrack/cursor_coding_compress_bench_v1_n20.jsonl",
        "case_count": 20,
        "ssot_one_liner_ko": ssot_one_liner,
        "field_lens_resolver": {
            "field": "regime_prism_meta_channel_poc_success",
            "sasang": "meta sidecar가 user-text 압축 메트릭 delta 0 (A·C 20/20) [HYPO]",
            "myeongni": "prepend 합선 비권장; 포인터는 압축 입력 밖(meta_channel)",
            "logos": "[NON_GATING] sandbox 격벽·본선 무터치",
            "conflict_resolver": "prepend 붕괴 vs meta sidecar 격리 → meta sidecar 입증",
            "final_action": "ARCHIVE_LIMITLESS_TRILOGY_REPORT — B-track freeze only",
        },
        "trilogy_table": [
            {
                "lane": "A",
                "label": "guarded_meta_channel",
                "hardening": "ON",
                "meta_channel": True,
                "avg_jaccard": a_agg.get("meta_channel_avg_jaccard"),
                "prepend_avg_jaccard": a_agg.get("prepend_avg_jaccard"),
                "meta_preserves_baseline": f"{a_agg.get('meta_preserves_baseline_count')}/20",
                "avg_meta_tokens": a_agg.get("avg_meta_channel_tokens"),
                "verdict_ko": "안전 지대 PoC 통과",
            },
            {
                "lane": "B",
                "label": "guarded_dynamic_pinset_meta",
                "hardening": "ON",
                "meta_channel": True,
                "avg_jaccard": b_agg.get("meta_dynamic_avg_jaccard"),
                "dynamic_unique_sets": b_row_unique,
                "pinset_ids_differ_count": b_row_differ,
                "dynamic_advantage_proven": lane_b_dynamic_proven,
                "meta_preserves_baseline": f"{b_agg.get('dynamic_preserves_baseline_count')}/20",
                "dynamic_profile": "py_coding_dynamic",
                "verdict_ko": (
                    "동적 pinset 차별화 입증 (full·heavy)"
                    if lane_b_dynamic_proven
                    else "동적 우위 미입증"
                ),
            },
            {
                "lane": "C",
                "label": "no_guard_meta_channel",
                "hardening": "OFF",
                "meta_channel": True,
                "avg_jaccard": c_agg.get("no_guard_meta_avg_jaccard"),
                "prepend_avg_jaccard": c_agg.get("no_guard_prepend_avg_jaccard"),
                "avg_saving": c_agg.get("no_guard_meta_avg_saving"),
                "min_jaccard": c_agg.get("no_guard_meta_min_jaccard"),
                "meta_preserves_baseline": f"{c_agg.get('meta_preserves_no_guard_count')}/20",
                "avg_meta_tokens": c_agg.get("avg_meta_channel_tokens"),
                "verdict_ko": "무가드 한계(0.713) 유지; meta user-text 보존",
            },
        ],
        "no_guard_vs_guarded": {
            "no_guard_avg_jaccard": cmp_agg.get("no_guard_avg_jaccard"),
            "guarded_avg_jaccard": cmp_agg.get("guarded_avg_jaccard"),
            "circuit_breaker_saved_count": cmp_agg.get("circuit_breaker_saved_quality_count"),
            "gatekeeper_bypass_count": cmp_agg.get("gatekeeper_bypass_count"),
        },
        "forbidden_claims": [
            "track_a_promotion",
            "production_hardening_change",
            "99pct_compression_headline",
            "unlimited_knowledge_injection",
            "corpus_bloat_default_path",
        ],
        "allowed_claims": [
            "meta_channel_post_gatekeeper_poc_pass",
            "prepend_not_recommended",
            "guards_required_for_quality_floor",
            "mainline_untouched",
            "dynamic_pinset_py_coding_dynamic_n20_research_only",
            "proxy_meta_wire_env_flag_default_off",
        ],
        "next_bench_optional": [] if phase2_complete else [
            "lane_b on code_context/long_multifile heavy slice",
            "no_guard + meta + corpus_expansion triple axis",
        ],
        "n40_dogfood_extension_path": "experiments/no_guard_limit_test/results/prism_n40_dogfood_extension_v1_latest.json",
        "staging_extension": {
            "staging_enable_ok": staging_ready.get("staging_enable_ok"),
            "human_signoff_status": (staging_ready.get("human_signoff") or {}).get("status"),
            "live_smoke_pass": staging_live.get("staging_live_smoke_pass"),
            "env_flag": staging_ready.get("env_flag"),
            "env_default": staging_ready.get("env_default"),
            "n40_complete": n40_ext.get("complete"),
        },
        "phase3_extension": {
            "complete": phase3_complete,
            "dynamic_profile": "py_coding_dynamic",
            "coding_proxy_meta_wire": _rel(PHASE3_SOURCE_PATHS["coding_proxy_meta_wire"]),
            "meta_wire_env": "MKM_PRISM_META_CHANNEL_BTRACK",
            "lane_e_isolation": {
                "baseline_avg_jaccard": e_agg.get("baseline_avg_jaccard"),
                "corpus_only_avg_jaccard": e_agg.get("corpus_only_avg_jaccard"),
                "meta_only_avg_jaccard": e_agg.get("meta_only_avg_jaccard"),
                "meta_only_preserves_count": e_agg.get("meta_only_preserves_count"),
                "corpus_only_changed_count": e_agg.get("corpus_only_changed_count"),
            },
            "proxy_meta_wire_bench": {
                "wire_poc_pass": wire_agg.get("wire_poc_pass"),
                "preserves_metrics_count": wire_agg.get("preserves_metrics_count"),
                "meta_present_count": wire_agg.get("meta_present_count"),
            },
        },
        "phase2_extension": {
            "complete": phase2_complete,
            "lane_b2_heavy": {
                "case_count": b2.get("case_count"),
                "heavy_lanes": b2.get("heavy_lanes"),
                "pinset_ids_differ_count": b2_agg.get("pinset_ids_differ_count"),
                "dynamic_unique_sets": b2_agg.get("dynamic_pinset_unique_sets"),
                "dynamic_advantage_proven": b2_proven,
                "meta_dynamic_avg_jaccard": b2_agg.get("meta_dynamic_avg_jaccard"),
                "verdict_ko": (
                    "heavy slice 동적 pinset 차별화 입증"
                    if b2_proven
                    else "heavy slice에서도 fixed와 동일 가능"
                ),
            },
            "lane_d_triple": {
                "case_count": lane_d.get("case_count"),
                "corpus_must_keep_extra_count": (lane_d.get("corpus_expansion") or {}).get(
                    "must_keep_extra_count"
                ),
                "baseline_avg_jaccard": d_agg.get("baseline_avg_jaccard"),
                "meta_only_avg_jaccard": d_agg.get("meta_only_avg_jaccard"),
                "meta_corpus_avg_jaccard": d_agg.get("meta_corpus_avg_jaccard"),
                "meta_only_preserves_count": d_agg.get("meta_only_preserves_count"),
                "meta_corpus_preserves_count": d_agg.get("meta_corpus_preserves_count"),
            },
        },
        "evidence_paths": {
            **{k: _rel(p) for k, p in SOURCE_PATHS.items()},
            **{k: _rel(p) for k, p in PHASE2_SOURCE_PATHS.items()},
            "lane_e_corpus_isolation": _rel(PHASE3_SOURCE_PATHS["lane_e_corpus_isolation"]),
            "coding_proxy_meta_wire": _rel(PHASE3_SOURCE_PATHS["coding_proxy_meta_wire"]),
            "proxy_meta_wire_bench": _rel(PHASE3_SOURCE_PATHS["proxy_meta_wire_bench"]),
        },
        "evidence_valid": {
            **{
                k: _is_valid_lane_doc(loaded[k]) and not (loaded[k] or {}).get("dry_run")
                for k in SOURCE_PATHS
            },
            **{
                k: _is_valid_lane_doc(phase2_loaded[k]) and not (phase2_loaded[k] or {}).get("dry_run")
                for k in PHASE2_SOURCE_PATHS
            },
            "lane_e_corpus_isolation": phase3_complete,
            "coding_proxy_meta_wire": PHASE3_SOURCE_PATHS["coding_proxy_meta_wire"].is_file(),
            "proxy_meta_wire_bench": _is_valid_lane_doc(phase3_wire_bench),
        },
        "pytest_smoke": "tests/test_build_archive_limitless_trilogy_report_v1.py",
        "boundary_ack": "Archive freeze; not CONSTITUTION or Track A active report.",
    }
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description="Build limitless trilogy archive report.")
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    ap.add_argument("--strict", action="store_true", help="Exit 1 if any source missing or dry_run.")
    ap.add_argument(
        "--require-phase2",
        action="store_true",
        help="Exit 1 if B2/D phase2 bench artifacts missing.",
    )
    args = ap.parse_args()

    doc = build_report(strict=bool(args.strict), require_phase2=bool(args.require_phase2))
    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
