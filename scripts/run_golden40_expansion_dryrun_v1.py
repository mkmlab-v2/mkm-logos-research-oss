#!/usr/bin/env python3
"""Golden 40 expansion dry-run: scale case count, eval Track A-equivalent stack, never write ACTIVE.

B-track / internal lab only. Does not modify MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json
or MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json. Headline KPI promotion defaults to HOLD (FAIL-COMP-004).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
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

REGISTRY = ROOT / "docs/final/artifacts/universal_compression_bench_matrix_registry_v1.json"
HOMOGENEOUS_MANIFEST = ROOT / "docs/final/artifacts/golden_40_homogeneous_expansion_manifest_v1.json"
IEOMA_SASANG_LANE = ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_sasang_v1.json"
LOGOS_VERSE_LANE = ROOT / "docs/final/artifacts/golden_40_logos_verse_compression_lane_v1.json"
EN_OPS_LANE = ROOT / "docs/final/artifacts/golden_40_en_ops_compression_lane_v1.json"
DEFAULT_LEXICON = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json"
DEFAULT_OUT = ROOT / "reports/golden_40_expansion_dryrun_v1_latest.json"
POOL_MODES = (
    "mixed_matrix",
    "homogeneous_sasang_ko",
    "homogeneous_logos_verse",
    "homogeneous_full",
    "homogeneous_en_ops",
    "golden_core_only",
)
HEADLINE_POLICY = ROOT / "reports/compression_track_a_headline_policy_v1_latest.json"
FORBIDDEN_WRITES = (
    ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
    ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _attach_hypo_sidecar(out_doc: dict[str, Any], field: str, path: Path | None) -> None:
    if not path:
        return
    sidecar = path if path.is_absolute() else ROOT / path
    if sidecar.is_file():
        try:
            rel = str(sidecar.relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            rel = str(sidecar.resolve())
        out_doc[field] = {
            "path": rel,
            "snapshot": _load_json(sidecar),
            "note": "Metadata only — evaluate_report KPI unchanged",
        }
    else:
        out_doc[field] = {"path": str(sidecar), "missing": True}


def _load_cases(path: Path, *, lane_id: str, domain_tag: str) -> list[dict[str, Any]]:
    doc = _load_json(path)
    cases = doc.get("compression_cases") or []
    out: list[dict[str, Any]] = []
    for row in cases:
        if not isinstance(row, dict):
            continue
        cid = str(row.get("id") or "").strip()
        if not cid:
            continue
        item = dict(row)
        item["id"] = f"{lane_id}__{cid}"
        item["domain_tag"] = domain_tag
        item["lane_id"] = lane_id
        item["expansion_source"] = str(path.relative_to(ROOT)).replace("\\", "/")
        item["research_only"] = True
        out.append(item)
    return out


def _golden_cases() -> list[dict[str, Any]]:
    doc = _load_json(INPUT_V2)
    out: list[dict[str, Any]] = []
    for row in doc.get("compression_cases") or []:
        if not isinstance(row, dict):
            continue
        cid = str(row.get("id") or "").strip()
        if not cid:
            continue
        item = dict(row)
        item["domain_tag"] = "golden_full_v2_40"
        item["lane_id"] = "golden_full_v2_40"
        item["expansion_source"] = "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
        item["research_only"] = False
        out.append(item)
    return out


def _expansion_pool(registry: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (included_lanes, skipped_lanes) metadata."""
    lanes_meta: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    pool: list[dict[str, Any]] = []
    for lane in sorted(registry.get("lanes") or [], key=lambda x: int(x.get("priority") or 0)):
        if not lane.get("enabled"):
            continue
        lane_id = str(lane.get("lane_id") or "")
        if lane.get("eval_contract"):
            skipped.append(
                {
                    "lane_id": lane_id,
                    "reason": "eval_contract_not_ultra_default",
                    "eval_contract": lane.get("eval_contract"),
                }
            )
            continue
        rel = str(lane.get("input_path") or "")
        path = ROOT / rel
        if not path.is_file():
            skipped.append({"lane_id": lane_id, "reason": "input_missing", "input_path": rel})
            continue
        batch = _load_cases(path, lane_id=lane_id, domain_tag=str(lane.get("domain_tag") or lane_id))
        pool.extend(batch)
        lanes_meta.append({"lane_id": lane_id, "cases": len(batch), "input_path": rel})
    pool.sort(key=lambda r: str(r.get("id") or ""))
    return pool, {"included": lanes_meta, "skipped": skipped}


def _load_lane_file(
    path: Path,
    *,
    lane_id: str,
    domain_tag: str,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    if not path.is_file():
        return [], {"lane_id": lane_id, "reason": "input_missing", "input_path": str(path.relative_to(ROOT)).replace("\\", "/")}
    batch = _load_cases(path, lane_id=lane_id, domain_tag=domain_tag)
    batch.sort(key=lambda r: str(r.get("id") or ""))
    return batch, {
        "lane_id": lane_id,
        "cases": len(batch),
        "input_path": str(path.relative_to(ROOT)).replace("\\", "/"),
    }


def _homogeneous_sasang_pool() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    batch, meta = _load_lane_file(IEOMA_SASANG_LANE, lane_id="ijeoma_sasang_v1", domain_tag="ijeoma_sasang")
    included = [meta] if meta and meta.get("cases") else []
    skipped = [meta] if meta and meta.get("reason") else []
    return batch, {
        "included": included,
        "skipped": skipped,
        "homogeneous_note": "KO sasang — Golden cmp2_011–040 proxy band",
    }


def _homogeneous_logos_verse_pool(
    *,
    logos_lane: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    batch, meta = _load_lane_file(
        logos_lane or LOGOS_VERSE_LANE,
        lane_id="golden_logos_verse_v1",
        domain_tag="logos_verse_ancient",
    )
    included = [meta] if meta and meta.get("cases") else []
    skipped = [meta] if meta and meta.get("reason") else []
    return batch, {
        "included": included,
        "skipped": skipped,
        "homogeneous_note": "Ancient verse previews (BHS/SBLGNT) — stride sample from verse_decoded_v2.jsonl",
    }


def _homogeneous_en_ops_pool(
    *,
    en_ops_lane: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    batch, meta = _load_lane_file(
        en_ops_lane or EN_OPS_LANE,
        lane_id="golden_en_ops_v1",
        domain_tag="golden_en_ops_proxy",
    )
    included = [meta] if meta and meta.get("cases") else []
    skipped = [meta] if meta and meta.get("reason") else []
    return batch, {
        "included": included,
        "skipped": skipped,
        "homogeneous_note": "EN ops/governance MD — cmp2_001–010 proxy band only",
    }


def _interleave_lane_batches(*batches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Round-robin across lanes so N>40 blends domains (avoid id-sort filling one lane first)."""
    pool: list[dict[str, Any]] = []
    seen: set[str] = set()
    max_len = max((len(b) for b in batches), default=0)
    for i in range(max_len):
        for batch in batches:
            if i >= len(batch):
                continue
            row = batch[i]
            rid = str(row.get("id") or "")
            if not rid or rid in seen:
                continue
            pool.append(row)
            seen.add(rid)
    return pool


def _homogeneous_full_pool(
    *,
    logos_lane: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sasang, sasang_meta = _homogeneous_sasang_pool()
    logos, logos_meta = _homogeneous_logos_verse_pool(logos_lane=logos_lane)
    pool = _interleave_lane_batches(sasang, logos)
    return pool, {
        "included": [m for m in (sasang_meta.get("included") or []) + (logos_meta.get("included") or []) if m],
        "skipped": (sasang_meta.get("skipped") or []) + (logos_meta.get("skipped") or []),
        "homogeneous_note": "Round-robin ijeoma_sasang + logos_verse — no finance/enterprise mixed matrix",
    }


def _resolve_expansion_pool(
    pool_mode: str,
    registry: dict[str, Any],
    *,
    logos_lane: Path | None = None,
    en_ops_lane: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if pool_mode == "mixed_matrix":
        return _expansion_pool(registry)
    if pool_mode == "homogeneous_sasang_ko":
        return _homogeneous_sasang_pool()
    if pool_mode == "homogeneous_logos_verse":
        return _homogeneous_logos_verse_pool(logos_lane=logos_lane)
    if pool_mode == "homogeneous_full":
        return _homogeneous_full_pool(logos_lane=logos_lane)
    if pool_mode == "homogeneous_en_ops":
        return _homogeneous_en_ops_pool(en_ops_lane=en_ops_lane)
    if pool_mode == "golden_core_only":
        return [], {"included": [], "skipped": [], "note": "golden_core_only — no lane expansion"}
    raise ValueError(f"unknown pool_mode: {pool_mode}")


def _merge_for_target(golden: list[dict[str, Any]], pool: list[dict[str, Any]], target: int) -> list[dict[str, Any]]:
    if target <= len(golden):
        return golden[:target]
    seen = {str(c["id"]) for c in golden}
    merged = list(golden)
    for row in pool:
        rid = str(row.get("id") or "")
        if not rid or rid in seen:
            continue
        merged.append(row)
        seen.add(rid)
        if len(merged) >= target:
            break
    return merged


def _percentile(sorted_vals: list[float], pct: float) -> float | None:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def _frozen_headline_targets() -> tuple[dict[str, Any], dict[str, Any]]:
    """MS/CENTRAL promoted headline (FAIL-COMP-004) vs disk remeasure pointer."""
    ms_frozen: dict[str, Any] = {
        "global_token_saving_rate": float(PROFILE_BENCH_SSOT["economy"]["headline_global_token_saving_rate"]),
        "avg_reconstruction_fidelity_jaccard": float(PROFILE_BENCH_SSOT["economy"]["headline_jaccard"]),
        "source": "scripts/compression_profile_v1.py PROFILE_BENCH_SSOT economy (disk at run)",
    }
    if HEADLINE_POLICY.is_file():
        hp = _load_json(HEADLINE_POLICY)
        prior = hp.get("frozen_headline_prior")
        if isinstance(prior, dict):
            ms_frozen = {
                "global_token_saving_rate": float(prior.get("global_token_saving_rate") or ms_frozen["global_token_saving_rate"]),
                "avg_reconstruction_fidelity_jaccard": float(
                    prior.get("avg_reconstruction_fidelity_jaccard") or ms_frozen["avg_reconstruction_fidelity_jaccard"]
                ),
                "global_token_saving_rate_pct": prior.get("global_token_saving_rate_pct"),
                "source": "reports/compression_track_a_headline_policy_v1_latest.json frozen_headline_prior",
            }
    disk_remeasure = {
        "global_token_saving_rate": float(PROFILE_BENCH_SSOT["economy"]["headline_global_token_saving_rate"]),
        "avg_reconstruction_fidelity_jaccard": float(PROFILE_BENCH_SSOT["economy"]["headline_jaccard"]),
        "source": "PROFILE_BENCH_SSOT economy (41658 ultra-default disk; not MS paste headline)",
    }
    return ms_frozen, disk_remeasure


def _golden_id_set() -> frozenset[str]:
    return frozenset(str(c.get("id") or "") for c in _golden_cases() if c.get("id"))


def _golden_core_metrics(cases: list[dict[str, Any]]) -> dict[str, Any] | None:
    golden_ids = _golden_id_set()
    rows = [c for c in cases if str(c.get("id") or "") in golden_ids]
    if not rows:
        return None
    saving = [float(c.get("token_saving_rate") or 0.0) for c in rows]
    jaccard = [float(c.get("reconstruction_fidelity_jaccard") or 0.0) for c in rows]
    return {
        "case_count": len(rows),
        "global_token_saving_rate": round(mean(saving), 6),
        "avg_reconstruction_fidelity_jaccard": round(mean(jaccard), 6),
    }


def _distribution(cases: list[dict[str, Any]]) -> dict[str, Any]:
    saving = sorted(float(c.get("token_saving_rate") or 0.0) for c in cases)
    jaccard = sorted(float(c.get("reconstruction_fidelity_jaccard") or 0.0) for c in cases)
    if not saving:
        return {"case_count": 0}
    return {
        "case_count": len(cases),
        "token_saving_rate": {
            "mean": round(mean(saving), 6),
            "min": round(saving[0], 6),
            "p5": round(_percentile(saving, 5) or saving[0], 6),
            "p50": round(_percentile(saving, 50) or saving[0], 6),
            "max": round(saving[-1], 6),
        },
        "reconstruction_fidelity_jaccard": {
            "mean": round(mean(jaccard), 6),
            "min": round(jaccard[0], 6),
            "p5": round(_percentile(jaccard, 5) or jaccard[0], 6),
            "p50": round(_percentile(jaccard, 50) or jaccard[0], 6),
            "max": round(jaccard[-1], 6),
        },
    }


def _load_signoff_relaxed() -> tuple[dict[str, float], frozenset[str] | None, frozenset[str] | None]:
    domain_relaxed: dict[str, float] = {}
    relaxed_case_allowlist: frozenset[str] | None = None
    relaxed_case_exclude: frozenset[str] | None = None
    if not PROMOTION_SIGNOFF.is_file():
        return domain_relaxed, relaxed_case_allowlist, relaxed_case_exclude
    signoff_doc = _load_json(PROMOTION_SIGNOFF)
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


def _run_eval(
    cases: list[dict[str, Any]],
    *,
    lexicon_path: Path,
    domain_relaxed: dict[str, float],
    relaxed_case_allowlist: frozenset[str] | None,
    relaxed_case_exclude: frozenset[str] | None,
    cap_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    baseline_doc = _load_json(BASELINE_V2)
    decision_doc = _load_json(DECISION)
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
    eval_relaxed = domain_relaxed
    eval_allowlist = relaxed_case_allowlist
    eval_exclude = relaxed_case_exclude
    if cap_overrides:
        if cap_overrides.get("general_max_saving_rate") is not None:
            general_max_saving_rate = float(cap_overrides["general_max_saving_rate"])
        if cap_overrides.get("sensitive_max_saving_rate") is not None:
            sensitive_max_saving_rate = float(cap_overrides["sensitive_max_saving_rate"])
        if cap_overrides.get("hangul_max_saving_rate") is not None:
            hangul_max_saving_rate = float(cap_overrides["hangul_max_saving_rate"])
        if "domain_relaxed_max_saving_overrides" in cap_overrides:
            eval_relaxed = dict(cap_overrides.get("domain_relaxed_max_saving_overrides") or {})
        if "domain_relaxed_max_saving_case_allowlist" in cap_overrides:
            eval_allowlist = cap_overrides.get("domain_relaxed_max_saving_case_allowlist")
        if "domain_relaxed_max_saving_exclude_case_ids" in cap_overrides:
            eval_exclude = cap_overrides.get("domain_relaxed_max_saving_exclude_case_ids")
    baseline_avg_jaccard = float(
        baseline_doc.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    threshold_pp = float(decision_doc.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))
    apply_bridge_policy = env_apply_gematria_4d_bridge_policy()

    src_doc = {
        "schema": "golden_40_expansion_dryrun_input_v1",
        "description": "Ephemeral eval input — not SSOT; do not commit as Golden 40 replacement.",
        "compression_cases": cases,
    }
    report = evaluate_report(
        src_doc,
        source_input="golden_40_expansion_dryrun_ephemeral",
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
        domain_relaxed_max_saving_overrides=eval_relaxed or None,
        domain_relaxed_max_saving_case_allowlist=eval_allowlist,
        domain_relaxed_max_saving_exclude_case_ids=eval_exclude,
        include_cee_core=True,
    )
    apply_promoted_policy_floor_to_quality_gate(report)
    return report


def _tier_verdict(
    metrics: dict[str, Any],
    *,
    frozen_saving: float,
    frozen_jaccard: float,
    min_floor_saving: float,
    min_floor_jaccard: float,
) -> dict[str, Any]:
    saving = float(metrics.get("global_token_saving_rate") or 0.0)
    jaccard = float(metrics.get("avg_reconstruction_fidelity_jaccard") or 0.0)
    violations = int(metrics.get("sensitive_violation_count") or 0)
    floor_ok = saving >= min_floor_saving and jaccard >= min_floor_jaccard and violations == 0
    headline_meets_frozen = saving >= frozen_saving and jaccard >= frozen_jaccard
    return {
        "floor_regression_ok": floor_ok,
        "headline_meets_frozen_kpi": headline_meets_frozen,
        "headline_kpi_update": "HOLD" if not headline_meets_frozen else "WATCH_CANDIDATE",
        "would_change_active": False,
        "news_readiness": False,
        "delta_vs_frozen_headline_pp": {
            "saving": round((saving - frozen_saving) * 100.0, 2),
            "jaccard": round((jaccard - frozen_jaccard) * 100.0, 2),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Golden 40 expansion dry-run (B-track, ACTIVE untouched).")
    ap.add_argument(
        "--target-counts",
        default="40,80,120,200",
        help="Comma-separated case counts to evaluate (golden core + lane pool).",
    )
    ap.add_argument("--registry", type=Path, default=REGISTRY)
    ap.add_argument(
        "--pool-mode",
        choices=POOL_MODES,
        default="mixed_matrix",
        help="mixed_matrix | homogeneous_sasang_ko | homogeneous_logos_verse | homogeneous_full | golden_core_only",
    )
    ap.add_argument("--manifest", type=Path, default=HOMOGENEOUS_MANIFEST, help="Catalog pointer (optional).")
    ap.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-floor-saving", type=float, default=0.45)
    ap.add_argument("--min-floor-jaccard", type=float, default=0.87)
    ap.add_argument(
        "--plan-only",
        action="store_true",
        help="Build merge manifest only; skip evaluate_report (fast).",
    )
    ap.add_argument(
        "--write-input-snapshot",
        type=Path,
        default=None,
        help="Optional: write ephemeral merged input for largest target only.",
    )
    ap.add_argument(
        "--hypo-polar-sidecar",
        type=Path,
        default=None,
        help="B-track [HYPO]: attach polar hypo JSON path to output (does not alter compression KPI).",
    )
    ap.add_argument(
        "--hypo-cooc-sidecar",
        type=Path,
        default=None,
        help="B-track [HYPO]: attach prefix-gated cooc routing PoC JSON (metadata only; KPI unchanged).",
    )
    ap.add_argument(
        "--hypo-wire-gloss-sidecar",
        type=Path,
        default=None,
        help="B-track [HYPO]: attach wire gloss remediation/smoke JSON (metadata only; KPI unchanged).",
    )
    ap.add_argument(
        "--logos-verse-lane",
        type=Path,
        default=None,
        help="B-track sandbox: override logos verse lane JSON (default docs/final artifact).",
    )
    ap.add_argument(
        "--en-ops-lane",
        type=Path,
        default=None,
        help="B-track sandbox: override en_ops lane JSON (default docs/final artifact).",
    )
    ap.add_argument(
        "--per-lane-cap-policy",
        type=Path,
        default=None,
        help="B-track: logos per-lane SSOT cap policy JSON (default reports/logos_verse_per_lane_ssot_cap_policy_v1_latest.json).",
    )
    ap.add_argument(
        "--apply-per-lane-cap-policy",
        action="store_true",
        help="Apply --per-lane-cap-policy when pool-mode is allowed (clears signoff relaxed; binds general cap).",
    )
    args = ap.parse_args()

    for forbidden in FORBIDDEN_WRITES:
        if not forbidden.is_file():
            print(f"warn: expected SSOT present: {forbidden}", file=sys.stderr)

    lexicon = args.lexicon if args.lexicon.is_absolute() else ROOT / args.lexicon
    if not lexicon.is_file():
        print(f"error: missing lexicon: {lexicon}", file=sys.stderr)
        return 2

    registry_path = args.registry if args.registry.is_absolute() else ROOT / args.registry
    if not registry_path.is_file():
        print(f"error: missing registry: {registry_path}", file=sys.stderr)
        return 2

    try:
        targets = sorted({int(x.strip()) for x in args.target_counts.split(",") if x.strip()})
    except ValueError:
        print("error: --target-counts must be comma-separated integers", file=sys.stderr)
        return 2
    if not targets or min(targets) < 40:
        print("error: minimum target count is 40 (golden core)", file=sys.stderr)
        return 2

    registry = _load_json(registry_path)
    golden = _golden_cases()
    if len(golden) < 40:
        print(f"error: golden input has {len(golden)} cases, expected >= 40", file=sys.stderr)
        return 2

    logos_lane = args.logos_verse_lane
    if logos_lane and not logos_lane.is_absolute():
        logos_lane = ROOT / logos_lane
    en_ops_lane = args.en_ops_lane
    if en_ops_lane and not en_ops_lane.is_absolute():
        en_ops_lane = ROOT / en_ops_lane
    pool, lane_meta = _resolve_expansion_pool(
        args.pool_mode,
        registry,
        logos_lane=logos_lane,
        en_ops_lane=en_ops_lane,
    )
    if logos_lane:
        lane_meta["logos_verse_lane_override"] = str(logos_lane.relative_to(ROOT)).replace("\\", "/")
    if en_ops_lane:
        lane_meta["en_ops_lane_override"] = str(en_ops_lane.relative_to(ROOT)).replace("\\", "/")
    max_available = len(golden) + len(pool)
    if args.pool_mode == "golden_core_only":
        max_available = len(golden)

    ms_frozen, disk_remeasure = _frozen_headline_targets()
    frozen_saving = float(ms_frozen["global_token_saving_rate"])
    frozen_jaccard = float(ms_frozen["avg_reconstruction_fidelity_jaccard"])

    headline_policy_ref: dict[str, Any] | None = None
    if HEADLINE_POLICY.is_file():
        hp = _load_json(HEADLINE_POLICY)
        headline_policy_ref = {
            "path": str(HEADLINE_POLICY.relative_to(ROOT)).replace("\\", "/"),
            "headline_kpi_update": hp.get("headline_kpi_update"),
            "decision": hp.get("decision"),
        }

    domain_relaxed, allowlist, exclude = _load_signoff_relaxed()
    cap_overrides: dict[str, Any] | None = None
    per_lane_policy_ref: dict[str, Any] | None = None
    if args.apply_per_lane_cap_policy:
        from scripts.logos_verse_per_lane_ssot_cap_policy_v1 import (
            eval_cap_overrides,
            load_policy,
            policy_allows_pool_mode,
        )

        policy_path = args.per_lane_cap_policy
        if policy_path is None:
            policy_path = ROOT / "reports/logos_verse_per_lane_ssot_cap_policy_v1_latest.json"
        elif not policy_path.is_absolute():
            policy_path = ROOT / policy_path
        policy = load_policy(policy_path)
        if not policy_allows_pool_mode(policy, args.pool_mode):
            print(
                f"error: pool-mode {args.pool_mode!r} not in policy allowed_pool_modes",
                file=sys.stderr,
            )
            return 2
        cap_overrides = eval_cap_overrides(policy)
        per_lane_policy_ref = {
            "path": str(policy_path.relative_to(ROOT)).replace("\\", "/"),
            "lane_id": policy.get("lane_id"),
            "cap_bind": policy.get("cap_bind"),
        }
    tiers: list[dict[str, Any]] = []
    all_floor_ok = True

    for target in targets:
        merged = _merge_for_target(golden, pool, target)
        tier: dict[str, Any] = {
            "target_case_count": target,
            "actual_case_count": len(merged),
            "golden_core_count": min(40, len(merged)),
            "expansion_lane_count": max(0, len(merged) - min(40, len(merged))),
            "truncated_by_pool": len(merged) < target,
            "max_available_in_pool": max_available,
        }
        if args.plan_only:
            tier["plan_only"] = True
            tiers.append(tier)
            continue

        report = _run_eval(
            merged,
            lexicon_path=lexicon,
            domain_relaxed=domain_relaxed,
            relaxed_case_allowlist=allowlist,
            relaxed_case_exclude=exclude,
            cap_overrides=cap_overrides,
        )
        cm = report.get("compression_metrics") or {}
        cases = cm.get("cases") or []
        metrics = {
            "case_count": cm.get("case_count"),
            "global_token_saving_rate": cm.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
            "sensitive_violation_count": cm.get("sensitive_violation_count"),
            "min_reconstruction_fidelity_jaccard": cm.get("min_reconstruction_fidelity_jaccard"),
        }
        tier["aggregate_metrics"] = metrics
        tier["per_case_distribution"] = _distribution(cases)
        golden_only = _golden_core_metrics(cases)
        if golden_only:
            tier["golden_core_only_metrics"] = golden_only
            tier["golden_core_verdict"] = _tier_verdict(
                golden_only,
                frozen_saving=frozen_saving,
                frozen_jaccard=frozen_jaccard,
                min_floor_saving=args.min_floor_saving,
                min_floor_jaccard=args.min_floor_jaccard,
            )
        verdict = _tier_verdict(
            metrics,
            frozen_saving=frozen_saving,
            frozen_jaccard=frozen_jaccard,
            min_floor_saving=args.min_floor_saving,
            min_floor_jaccard=args.min_floor_jaccard,
        )
        tier.update(verdict)
        if not verdict["floor_regression_ok"]:
            all_floor_ok = False
        tiers.append(tier)

        if args.write_input_snapshot and target == max(targets):
            snap_path = (
                args.write_input_snapshot
                if args.write_input_snapshot.is_absolute()
                else ROOT / args.write_input_snapshot
            )
            snap_path.parent.mkdir(parents=True, exist_ok=True)
            snap_path.write_text(
                json.dumps(
                    {
                        "schema": "golden_40_expansion_dryrun_input_v1",
                        "generated_at_utc": _utc(),
                        "target_case_count": target,
                        "compression_cases": merged,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            tier["input_snapshot"] = str(snap_path.relative_to(ROOT)).replace("\\", "/")

    expansion_dilution = False
    if not args.plan_only:
        for tier in tiers:
            if int(tier.get("target_case_count") or 0) <= 40:
                continue
            gv = tier.get("golden_core_verdict") or {}
            if gv.get("floor_regression_ok") and not tier.get("floor_regression_ok"):
                expansion_dilution = True
                break

    out_doc: dict[str, Any] = {
        "schema": "golden_40_expansion_dryrun_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_wall": "B-track internal lab — no Track A ACTIVE write; no MS-PASTE merge; no news claim",
        "active_report_untouched": True,
        "golden_input_untouched": True,
        "would_change_active": False,
        "news_readiness": False,
        "bench_stack": "golden_40_full_v2_ultra_default_equivalent",
        "pool_mode": args.pool_mode,
        "homogeneous_manifest_pointer": (
            str(args.manifest.relative_to(ROOT)).replace("\\", "/")
            if args.manifest.is_file()
            else None
        ),
        "lexicon_path": str(lexicon.resolve()),
        "registry_path": str(registry_path.relative_to(ROOT)).replace("\\", "/"),
        "lane_pool": lane_meta,
        "frozen_headline_ms_paste": ms_frozen,
        "disk_remeasure_41658_pointer": disk_remeasure,
        "headline_policy_pointer": headline_policy_ref,
        "per_lane_cap_policy": per_lane_policy_ref,
        "floor_thresholds": {
            "min_global_token_saving_rate": args.min_floor_saving,
            "min_avg_jaccard": args.min_floor_jaccard,
            "note": "Slack floors aligned with check_compression_golden_bench_regression_v1.py",
        },
        "tiers": tiers,
        "summary": {
            "plan_only": bool(args.plan_only),
            "all_tiers_floor_regression_ok": all_floor_ok if not args.plan_only else None,
            "expansion_dilution_observed": expansion_dilution if not args.plan_only else None,
            "mixed_domain_dilution_observed": (
                expansion_dilution if not args.plan_only and args.pool_mode == "mixed_matrix" else None
            ),
            "promotion_recommendation": "HOLD",
            "headline_kpi_update": "HOLD",
            "interpretation": (
                "Larger N improves lab confidence only. Does not satisfy external news/SOTA/compare gates."
                + (
                    (
                        " Mixed Universal Matrix lanes dilute blended Jaccard — "
                        if args.pool_mode == "mixed_matrix"
                        else " Homogeneous expansion still dilutes blended vs golden_core — "
                    )
                    + "golden_core subset stays stable; do not treat expanded-N aggregate as Golden 40 headline."
                    if expansion_dilution
                    else ""
                )
            ),
        },
        "forbidden_write_paths": [str(p.relative_to(ROOT)).replace("\\", "/") for p in FORBIDDEN_WRITES],
    }
    _attach_hypo_sidecar(out_doc, "hypo_polar_sidecar", args.hypo_polar_sidecar)
    _attach_hypo_sidecar(out_doc, "hypo_cooc_sidecar", args.hypo_cooc_sidecar)
    _attach_hypo_sidecar(out_doc, "hypo_wire_gloss_sidecar", args.hypo_wire_gloss_sidecar)

    out_path = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"plan_only={args.plan_only} tiers={len(tiers)} promotion_recommendation=HOLD")
    if args.plan_only:
        return 0
    if not all_floor_ok:
        print("golden_40_expansion_dryrun: floor regression FAIL on one or more tiers", file=sys.stderr)
        return 1
    print("golden_40_expansion_dryrun: OK (floors pass; headline still HOLD)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
