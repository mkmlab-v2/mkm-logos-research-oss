#!/usr/bin/env python3
"""Refresh overlay version comparison SSOT from eval/fold/gate/routing-ab artifacts (research-only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
DEFAULT_OUT = ROOT / "reports/btrack_31k41k_overlay_version_comparison_v1_latest.json"
ROUTING_AB = ROOT / "reports/btrack_31k41k_v2_v2c_routing_ab_v1_latest.json"

VERSION_SPECS: list[dict[str, str]] = [
    {"overlay_version": "v1", "eval": "btrack_31k41k_prophecy_shadow_eval_v1_latest.json"},
    {"overlay_version": "v2", "eval": "btrack_31k41k_prophecy_shadow_eval_v2_latest.json", "fold": "btrack_31k41k_prophecy_shadow_fold_stability_v2_v1_latest.json"},
    {"overlay_version": "v2c", "eval": "btrack_31k41k_prophecy_shadow_eval_v2c_latest.json", "fold": "btrack_31k41k_prophecy_shadow_fold_stability_v2c_v1_latest.json", "gate": "btrack_31k41k_prophecy_shadow_gate_v2c_v1_latest.json"},
    {
        "overlay_version": "v2b",
        "eval": "btrack_31k41k_prophecy_shadow_eval_v2b_latest.json",
        "fold": "btrack_31k41k_prophecy_shadow_fold_stability_v1_latest.json",
        "gate": "btrack_31k41k_prophecy_shadow_gate_v1_latest.json",
    },
]


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc if isinstance(doc, dict) else {}


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _fold_summary(fold_doc: dict[str, Any]) -> dict[str, Any]:
    if not fold_doc:
        return {}
    agg = fold_doc.get("aggregates") or {}
    checks = fold_doc.get("checks") or {}
    pooled = fold_doc.get("pooled_panel") or {}
    return {
        "status": (fold_doc.get("summary") or {}).get("status"),
        "worst_fold_delta": agg.get("worst_fold_delta"),
        "positive_delta_folds": agg.get("positive_delta_folds"),
        "effective_folds": agg.get("effective_folds"),
        "pooled_delta": pooled.get("delta_hit_rate"),
        "stability_not_worse": checks.get("stability_not_worse"),
    }


def _eval_metrics(eval_doc: dict[str, Any]) -> dict[str, Any]:
    baseline = eval_doc.get("baseline") or {}
    shadow = eval_doc.get("shadow_probe") or {}
    inputs = eval_doc.get("inputs") or {}
    return {
        "baseline_hit_rate": baseline.get("price_directional_hit_rate"),
        "shadow_hit_rate": shadow.get("price_directional_hit_rate"),
        "delta_hit_rate": shadow.get("delta_hit_rate"),
        "overlay_applied_fraction": shadow.get("overlay_applied_fraction"),
        "probe_mode": inputs.get("probe_mode"),
    }


def _version_row(spec: dict[str, str]) -> dict[str, Any]:
    ver = spec["overlay_version"]
    eval_doc = _read(ART / spec["eval"])
    metrics = _eval_metrics(eval_doc)
    row: dict[str, Any] = {
        "overlay_version": ver,
        "eval_path": f"docs/final/artifacts/{spec['eval']}",
        "control_flags": eval_doc.get("control_flags") or {},
        **metrics,
    }
    if spec.get("fold"):
        fold_path = ART / spec["fold"]
        fold_doc = _read(fold_path)
        row["fold"] = {"path": f"docs/final/artifacts/{spec['fold']}", **_fold_summary(fold_doc)}
    if spec.get("gate"):
        gate_path = ART / spec["gate"]
        gate_doc = _read(gate_path)
        row["gate"] = {
            "path": f"docs/final/artifacts/{spec['gate']}",
            "decision": gate_doc.get("decision"),
            "all_passed": gate_doc.get("all_passed"),
        }
    if ver == "v2" and not row.get("fold", {}).get("status"):
        row.setdefault("fold", {})["drill_path"] = "reports/btrack_31k41k_prophecy_shadow_fold_drill_v2_fail_v1_latest.md"
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    versions = [_version_row(s) for s in VERSION_SPECS]
    baseline_hit = versions[0].get("baseline_hit_rate") if versions else None
    routing_ab = _read(ROUTING_AB)
    ab_summary = routing_ab.get("ab_summary") or {}

    out = {
        "schema": "btrack_31k41k_overlay_version_comparison_v1",
        "generated_at_utc": _iso_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "baseline_n": 30,
        "baseline_hit_rate": baseline_hit,
        "versions": versions,
        "routing_ab": {
            "path": _rel(ROUTING_AB),
            "disagreement_row_count": ab_summary.get("disagreement_row_count"),
            "pooled_hit_rate_delta_v2c_minus_v2": ab_summary.get("pooled_hit_rate_delta_v2c_minus_v2"),
            "overlay_fraction_delta_v2c_minus_v2": ab_summary.get("overlay_fraction_delta_v2c_minus_v2"),
        },
        "operator_recommendation": (
            "chain_ssot=v2b; v2_not_for_promotion_due_to_fold_fail; "
            "v2c_pooled_tie_v2b_different_overlay_fraction; v2_fold_preserved_separately"
        ),
        "track_wall": "No Track A / live / Track C ingress product claims",
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
