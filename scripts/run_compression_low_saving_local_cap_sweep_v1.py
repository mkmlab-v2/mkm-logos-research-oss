#!/usr/bin/env python3
"""B-track: audit low-saving / lexicon-miss cases and sweep local shard-cap knobs (RQ-016 A-plan).

Reads Track A active report for audit only. Writes only to
``compression_low_saving_local_cap_sweep_v1_latest.json`` (never Track A active).

Knobs (no 41k lexicon edits): per-domain min-saving floor, per-domain relaxed max-saving cap,
global hangul_max_saving_rate, router blend candidate.
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

from scripts.report_multilens_performance_eval import evaluate_report

INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
TRACK_A_ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
OUT_DEFAULT = ROOT / "docs/final/artifacts/compression_low_saving_local_cap_sweep_v1_latest.json"
POLICY_FLOOR = 0.47
TOP_N_LOW_SAVING = 5

FORBIDDEN_WRITE = frozenset(
    {
        (ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json").resolve(),
        (ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json").resolve(),
        (ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_ULTRA_LITERAL_V1.json").resolve(),
    }
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_safe_out(path: Path) -> Path:
    resolved = path.resolve()
    if resolved in FORBIDDEN_WRITE:
        raise SystemExit(f"Refusing to write Track A active report: {path}")
    return resolved


def _case_audit_row(c: dict[str, Any]) -> dict[str, Any]:
    route = c.get("route") or {}
    mcb = route.get("master_codebook_lexicon_v1") or {}
    return {
        "id": str(c.get("id", "")),
        "token_saving_rate": c.get("token_saving_rate"),
        "reconstruction_fidelity_jaccard": c.get("reconstruction_fidelity_jaccard"),
        "domain": route.get("domain"),
        "shard_id": route.get("shard_id"),
        "lexicon_hit_count": mcb.get("hit_count", 0),
        "lexicon_status": mcb.get("status"),
    }


def _audit_from_report(report: dict[str, Any]) -> dict[str, Any]:
    cases = (report.get("compression_metrics") or {}).get("cases") or []
    rows = [_case_audit_row(c) for c in cases]
    rows_sorted = sorted(rows, key=lambda r: float(r.get("token_saving_rate") or 0))
    top_low = rows_sorted[:TOP_N_LOW_SAVING]
    hit_zero = [r for r in rows if int(r.get("lexicon_hit_count") or 0) == 0]
    domains_hit_zero: dict[str, int] = {}
    for r in hit_zero:
        dom = str(r.get("domain") or "unknown")
        domains_hit_zero[dom] = domains_hit_zero.get(dom, 0) + 1
    return {
        "case_count": len(rows),
        "top_n_low_saving": top_low,
        "top_n_low_saving_ids": [r["id"] for r in top_low],
        "lexicon_hit_count_zero_cases": hit_zero,
        "lexicon_hit_count_zero_by_domain": domains_hit_zero,
        "note": (
            "Top-N low saving on V2 bench often routes to ssot (lexicon hits present). "
            "hit_count=0 clusters on health/hangul/scm — use domain_relaxed caps / hangul_max, not lexicon edits."
        ),
    }


def _subset_metrics(report: dict[str, Any], case_ids: frozenset[str]) -> dict[str, Any]:
    cases = (report.get("compression_metrics") or {}).get("cases") or []
    rows = [c for c in cases if str(c.get("id", "")) in case_ids]
    if not rows:
        return {"case_count": 0}
    n = len(rows)
    return {
        "case_count": n,
        "avg_token_saving_rate": sum(float(r.get("token_saving_rate") or 0) for r in rows) / n,
        "avg_jaccard": sum(float(r.get("reconstruction_fidelity_jaccard") or 0) for r in rows) / n,
        "min_jaccard": min(float(r.get("reconstruction_fidelity_jaccard") or 0) for r in rows),
        "by_id": {
            str(r.get("id")): {
                "token_saving_rate": r.get("token_saving_rate"),
                "jaccard": r.get("reconstruction_fidelity_jaccard"),
            }
            for r in rows
        },
    }


def _global_metrics(report: dict[str, Any]) -> dict[str, Any]:
    cm = report.get("compression_metrics") or {}
    saving = float(cm.get("global_token_saving_rate") or 0)
    return {
        "global_token_saving_rate": saving,
        "distance_to_policy_floor": round(abs(saving - POLICY_FLOOR), 6),
        "ultra_saving_policy_ok": saving >= POLICY_FLOOR,
        "avg_reconstruction_fidelity_jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
        "min_reconstruction_fidelity_jaccard": cm.get("min_reconstruction_fidelity_jaccard"),
    }


def _rank_key(row: dict[str, Any]) -> tuple:
    floor = 1 if row.get("ultra_saving_policy_ok") else 0
    saving = float(row.get("global_token_saving_rate") or 0)
    dist = float(row.get("distance_to_policy_floor") or 999)
    avg_j = float(row.get("avg_reconstruction_fidelity_jaccard") or 0)
    return (floor, saving, -dist, avg_j)


def _build_variants(base_hangul: float) -> list[tuple[str, dict[str, Any]]]:
    return [
        ("baseline", {}),
        (
            "ssot_relaxed_cap_0.45",
            {"domain_relaxed_max_saving_overrides": {"ssot": 0.45}},
        ),
        (
            "ssot_relaxed_cap_0.50",
            {"domain_relaxed_max_saving_overrides": {"ssot": 0.50}},
        ),
        (
            "ssot_min_floor_0.55",
            {"domain_min_saving_floor_overrides": {"ssot": 0.55}},
        ),
        (
            "ssot_combo_relaxed_0.50_floor_0.55",
            {
                "domain_relaxed_max_saving_overrides": {"ssot": 0.50},
                "domain_min_saving_floor_overrides": {"ssot": 0.55},
            },
        ),
        (
            "health_hangul_relaxed_cap_0.50",
            {
                "domain_relaxed_max_saving_overrides": {
                    "health": 0.50,
                    "hangul": 0.50,
                }
            },
        ),
        (
            "hangul_max_plus_0.05",
            {"hangul_max_saving_rate": min(1.0, base_hangul + 0.05)},
        ),
        (
            "hangul_max_plus_0.10",
            {"hangul_max_saving_rate": min(1.0, base_hangul + 0.10)},
        ),
        (
            "router_blend_conservative",
            {
                "enable_router_blend_candidate": True,
                "router_blend_allow_nonrisk_jaccard_drop_pp": 1.0,
                "router_blend_min_saving_gain_pp": 2.0,
            },
        ),
        (
            "ssot_combo_plus_hangul_router",
            {
                "domain_relaxed_max_saving_overrides": {"ssot": 0.50},
                "domain_min_saving_floor_overrides": {"ssot": 0.55},
                "hangul_max_saving_rate": min(1.0, base_hangul + 0.05),
                "domain_relaxed_max_saving_overrides_extra": {
                    "health": 0.50,
                    "hangul": 0.50,
                },
                "enable_router_blend_candidate": True,
                "router_blend_allow_nonrisk_jaccard_drop_pp": 1.0,
                "router_blend_min_saving_gain_pp": 2.0,
            },
        ),
    ]


def _normalize_variant_kw(raw: dict[str, Any]) -> dict[str, Any]:
    """Flatten combo helper keys into evaluate_report kwargs."""
    kw = dict(raw)
    extra = kw.pop("domain_relaxed_max_saving_overrides_extra", None)
    base_relax = kw.get("domain_relaxed_max_saving_overrides") or {}
    if extra:
        merged = dict(base_relax)
        merged.update(extra)
        kw["domain_relaxed_max_saving_overrides"] = merged
    return kw


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out-json",
        type=Path,
        default=OUT_DEFAULT,
        help="B-track sweep artifact only (Track A active path rejected).",
    )
    ap.add_argument(
        "--audit-source",
        type=Path,
        default=TRACK_A_ACTIVE,
        help="Read-only report for low-saving / hit_count audit (default Track A active).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Emit audit + variant plan only; skip evaluate_report.",
    )
    args = ap.parse_args()
    out_path = _assert_safe_out(args.out_json)

    audit_source = args.audit_source.resolve()
    if audit_source in FORBIDDEN_WRITE:
        audit_report = _load(audit_source)
    else:
        audit_report = _load(audit_source) if audit_source.is_file() else {}
    audit = _audit_from_report(audit_report) if audit_report else {"case_count": 0}
    top_ids = frozenset(audit.get("top_n_low_saving_ids") or [])
    hit_zero_ids = frozenset(
        str(r.get("id", "")) for r in (audit.get("lexicon_hit_count_zero_cases") or [])
    )

    src = _load(INPUT_V2)
    base = _load(BASELINE_V2)
    dec = _load(DECISION)
    sel = dec.get("selected_candidate") or {}
    baseline_j = float(base.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0))
    threshold_pp = float(dec.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))

    def _gms(x: Any) -> float | None:
        return float(x) if x is not None else None

    base_hangul = float(sel.get("hangul_max_saving_rate") or 0.6)
    common = dict(
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=str(sel.get("strategy", "A")),
        intensity=str(sel.get("intensity", "extreme")),
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_j,
        general_max_saving_rate=_gms(sel.get("general_max_saving_rate")),
        sensitive_max_saving_rate=_gms(sel.get("sensitive_max_saving_rate")),
        hangul_max_saving_rate=base_hangul,
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        include_cee_core=True,
        apply_gematria_4d_bridge_policy=False,
        bridge_policy_domain_allowlist=None,
    )

    variants = _build_variants(base_hangul)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "out_json": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                    "audit_source": str(args.audit_source.relative_to(ROOT)).replace("\\", "/"),
                    "policy_floor": POLICY_FLOOR,
                    "audit": audit,
                    "variant_ids": [v[0] for v in variants],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    results: list[dict[str, Any]] = []
    baseline_global: dict[str, Any] | None = None
    for vid, raw_kw in variants:
        kw = _normalize_variant_kw(raw_kw)
        rep = evaluate_report(src, **{**common, **kw})
        g = _global_metrics(rep)
        row = {
            "id": vid,
            "knobs": kw,
            **g,
            "top5_low_saving_subset": _subset_metrics(rep, top_ids),
            "lexicon_hit_zero_subset": _subset_metrics(rep, hit_zero_ids),
        }
        if baseline_global is None:
            baseline_global = g
            row["delta_global_saving_vs_baseline"] = 0.0
        else:
            row["delta_global_saving_vs_baseline"] = round(
                float(g.get("global_token_saving_rate") or 0)
                - float(baseline_global.get("global_token_saving_rate") or 0),
                6,
            )
        results.append(row)

    ranked = sorted(results, key=_rank_key, reverse=True)
    floor_pass = [r for r in results if r.get("ultra_saving_policy_ok")]
    best = floor_pass[0] if floor_pass else ranked[0]

    doc = {
        "schema": "compression_low_saving_local_cap_sweep_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "hypothesis_tier": "B",
        "track_wall": "b_track_research_only",
        "rq": "RQ-016-A-plan",
        "policy_floor": POLICY_FLOOR,
        "audit_source_readonly": str(args.audit_source.relative_to(ROOT)).replace("\\", "/"),
        "audit": audit,
        "variant_count": len(results),
        "floor_pass_count": len(floor_pass),
        "best_by_floor_then_saving": best,
        "top5_variants_by_rank": ranked[:5],
        "all_variants": results,
        "promotion_note": (
            "Does not replace MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json. "
            "Local cap / domain floor overrides only — no lexicon file edits."
        ),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                "floor_pass_count": doc["floor_pass_count"],
                "best_id": best.get("id"),
                "best_global_saving": best.get("global_token_saving_rate"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
