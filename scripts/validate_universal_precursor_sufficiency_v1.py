#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _read_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def _strict_gate_from_tuning(tuning: dict[str, Any]) -> dict[str, Any]:
    rec = tuning.get("recommended_strict_gate") if isinstance(tuning.get("recommended_strict_gate"), dict) else {}
    return {
        "min_cluster_size": int(rec.get("min_cluster_size", 50)),
        "min_coherence_0_1": float(rec.get("min_coherence_0_1", 0.995)),
        "min_clusters_required": int(rec.get("min_clusters_required", 6)),
    }


def _apply_gate(clusters: list[dict[str, Any]], gate: dict[str, Any]) -> dict[str, Any]:
    kept = [
        c
        for c in clusters
        if int(c.get("size") or 0) >= gate["min_cluster_size"]
        and float(c.get("coherence_score_0_1") or 0.0) >= gate["min_coherence_0_1"]
    ]
    kept_count = len(kept)
    kept_verses = int(sum(int(c.get("size") or 0) for c in kept))
    decision = "GO_RESEARCH" if kept_count >= gate["min_clusters_required"] else "HOLD_RESEARCH"
    return {
        "kept_cluster_count": kept_count,
        "kept_total_verses": kept_verses,
        "decision": decision,
    }


def _split_even_odd(clusters: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    even: list[dict[str, Any]] = []
    odd: list[dict[str, Any]] = []
    for c in clusters:
        rep = str(c.get("representative_verse_id") or "")
        h = sum(ord(ch) for ch in rep) % 2
        if h == 0:
            even.append(c)
        else:
            odd.append(c)
    return even, odd


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate sufficiency for universal precursor ruleset.")
    ap.add_argument(
        "--ruleset-json",
        default="docs/final/artifacts/universal_precursor_ruleset_v1_latest.json",
    )
    ap.add_argument(
        "--digest-json",
        default="docs/final/artifacts/universal_precursor_cluster_digest_v1_latest.json",
    )
    ap.add_argument(
        "--tuning-json",
        default="docs/final/artifacts/universal_precursor_gate_tuning_v1_latest.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/universal_precursor_sufficiency_v1_latest.json",
    )
    ap.add_argument(
        "--robust-gate-json",
        default="",
        help="Optional robust gate artifact; if provided, overrides strict gate fields.",
    )
    args = ap.parse_args()

    ruleset = _read_json(_resolve(args.ruleset_json))
    digest = _read_json(_resolve(args.digest_json))
    tuning = _read_json(_resolve(args.tuning_json))

    clusters = digest.get("clusters") if isinstance(digest.get("clusters"), list) else []
    strict_gate = _strict_gate_from_tuning(tuning)
    if str(args.robust_gate_json).strip():
        robust = _read_json(_resolve(args.robust_gate_json))
        rec = robust.get("recommended_robust_gate") if isinstance(robust.get("recommended_robust_gate"), dict) else {}
        if rec:
            strict_gate = {
                "min_cluster_size": int(rec.get("min_cluster_size", strict_gate["min_cluster_size"])),
                "min_coherence_0_1": float(rec.get("min_coherence_0_1", strict_gate["min_coherence_0_1"])),
                "min_clusters_required": int(
                    rec.get("min_clusters_required", strict_gate["min_clusters_required"])
                ),
            }
    full = _apply_gate(clusters, strict_gate)

    even, odd = _split_even_odd(clusters)
    even_res = _apply_gate(even, strict_gate)
    odd_res = _apply_gate(odd, strict_gate)

    baseline_relaxed = int(((ruleset.get("gate") or {}).get("score") or {}).get("count_relaxed_gate", 0))
    baseline_join = int(((ruleset.get("gate") or {}).get("score") or {}).get("count_text_joined", 0))
    join_ratio = (baseline_join / baseline_relaxed) if baseline_relaxed > 0 else 0.0

    checks = {
        "join_coverage_ok": join_ratio >= 0.95,
        "strict_gate_full_ok": full["decision"] == "GO_RESEARCH",
        "strict_gate_even_ok": even_res["decision"] == "GO_RESEARCH",
        "strict_gate_odd_ok": odd_res["decision"] == "GO_RESEARCH",
        "cluster_count_floor_ok": len(clusters) >= 10,
    }
    pass_count = sum(1 for v in checks.values() if v)
    overall = "SUFFICIENT_RESEARCH" if pass_count == len(checks) else "NOT_YET_SUFFICIENT"

    out_doc = {
        "schema": "universal_precursor_sufficiency_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "a_track_binding_forbidden": True,
        "strict_gate": strict_gate,
        "baseline": {
            "count_relaxed_gate": baseline_relaxed,
            "count_text_joined": baseline_join,
            "join_coverage_ratio": round(join_ratio, 6),
            "cluster_count": len(clusters),
        },
        "validation": {
            "full": full,
            "split_even": even_res,
            "split_odd": odd_res,
        },
        "checks": checks,
        "pass_count": pass_count,
        "total_checks": len(checks),
        "overall_decision": overall,
        "note": "Sufficiency means robust for B-track research continuation, not production binding.",
    }
    out_path = _resolve(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    print(json.dumps({"overall_decision": overall, "pass_count": pass_count, "total_checks": len(checks)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
