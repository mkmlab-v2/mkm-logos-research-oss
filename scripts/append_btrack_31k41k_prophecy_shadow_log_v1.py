#!/usr/bin/env python3
"""Append one-line shadow eval/gate snapshot to JSONL history."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVAL_V2B_STRICT = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_eval_v2b_strict_latest.json"
DEFAULT_EVAL_V2B = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_eval_v2b_latest.json"
DEFAULT_EVAL_V2C = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_eval_v2c_latest.json"
DEFAULT_EVAL_V2 = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_eval_v2_latest.json"
DEFAULT_EVAL_V1 = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_eval_v1_latest.json"
DEFAULT_GATE = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_gate_v1_latest.json"
DEFAULT_LOG = ROOT / "reports/btrack_31k41k_prophecy_shadow_log_v1.jsonl"
DEFAULT_AB_MULTI = ROOT / "docs/final/artifacts/btrack_31k41k_shadow_v2b_ab_multi_v1_latest.json"


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return doc if isinstance(doc, dict) else {}


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _f(v: Any, d: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _b(v: Any) -> bool:
    return bool(v)


def _resolve_eval_path(explicit: Path | None) -> Path:
    if explicit is not None and explicit.is_file():
        return explicit
    if DEFAULT_EVAL_V2B_STRICT.is_file():
        return DEFAULT_EVAL_V2B_STRICT
    if DEFAULT_EVAL_V2B.is_file():
        return DEFAULT_EVAL_V2B
    if DEFAULT_EVAL_V2C.is_file():
        return DEFAULT_EVAL_V2C
    if DEFAULT_EVAL_V2.is_file():
        return DEFAULT_EVAL_V2
    return DEFAULT_EVAL_V1


def _row_from_eval_gate(eval_doc: dict[str, Any], gate_doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "btrack_31k41k_prophecy_shadow_log_row_v1",
        "logged_at_utc": _iso_now(),
        "research_only": True,
        "non_gating": True,
        "eval_generated_at_utc": eval_doc.get("generated_at_utc"),
        "gate_generated_at_utc": gate_doc.get("generated_at_utc"),
        "n_evaluated": ((eval_doc.get("baseline") or {}).get("n_evaluated")),
        "delta_hit_rate": _f(((eval_doc.get("shadow_probe") or {}).get("delta_hit_rate"))),
        "baseline_hit_rate": _f(((eval_doc.get("baseline") or {}).get("price_directional_hit_rate"))),
        "shadow_hit_rate": _f(((eval_doc.get("shadow_probe") or {}).get("price_directional_hit_rate"))),
        "eval_schema": eval_doc.get("schema"),
        "feature_summary": eval_doc.get("feature_summary"),
        "control_flags": eval_doc.get("control_flags"),
        "probe_mode": (eval_doc.get("inputs") or {}).get("probe_mode"),
        "overlay_version": (eval_doc.get("inputs") or {}).get("overlay_version"),
        "panel_merge_policy": (eval_doc.get("control_flags") or {}).get("panel_merge_policy"),
        "overlay_applied_count": (eval_doc.get("shadow_probe") or {}).get("overlay_applied_count"),
        "overlay_applied_fraction": (eval_doc.get("shadow_probe") or {}).get("overlay_applied_fraction"),
        "min_n_ok": _b(((eval_doc.get("checks") or {}).get("min_n_ok"))),
        "delta_ok": _b(((eval_doc.get("checks") or {}).get("delta_ok"))),
        "ssot_contract_ok": _b(((gate_doc.get("gate_checks") or {}).get("ssot_contract_ok"))),
        "gate_mode": (gate_doc.get("inputs") or {}).get("gate_mode"),
        "promotion_tier": gate_doc.get("promotion_tier"),
        "technical_passed": _b(((gate_doc.get("gate_checks") or {}).get("technical_passed"))),
        "all_passed": _b(gate_doc.get("all_passed")),
        "decision": gate_doc.get("decision"),
    }


def _contrast_audit_row(multi_doc: dict[str, Any]) -> dict[str, Any] | None:
    profiles = multi_doc.get("profiles") if isinstance(multi_doc.get("profiles"), dict) else {}
    contrast = profiles.get("contrast_zero_density")
    if not isinstance(contrast, dict):
        return None
    variants = contrast.get("variants") if isinstance(contrast.get("variants"), dict) else {}
    vmax = variants.get("v2b_max_merge") if isinstance(variants.get("v2b_max_merge"), dict) else {}
    vstrict = variants.get("v2b_strict_per_row") if isinstance(variants.get("v2b_strict_per_row"), dict) else {}
    ev_max = vmax.get("eval") if isinstance(vmax.get("eval"), dict) else {}
    ev_strict = vstrict.get("eval") if isinstance(vstrict.get("eval"), dict) else {}
    cmp_ = contrast.get("comparison") if isinstance(contrast.get("comparison"), dict) else {}
    return {
        "schema": "btrack_31k41k_prophecy_shadow_log_contrast_audit_v1",
        "logged_at_utc": _iso_now(),
        "research_only": True,
        "non_gating": True,
        "audit_profile": "contrast_zero_density",
        "source_ab_multi_json": str(DEFAULT_AB_MULTI),
        "lesson": "per_row_density_zero_blocks_strict_not_max",
        "gate_rule": "anchor_density_zero",
        "overlay_v2b_max_merge": ev_max.get("overlay_applied_count"),
        "overlay_v2b_strict": ev_strict.get("overlay_applied_count"),
        "delta_hit_rate_v2b_max": ev_max.get("delta_hit_rate"),
        "delta_hit_rate_v2b_strict": ev_strict.get("delta_hit_rate"),
        "delta_diff_strict_minus_max": cmp_.get("delta_hit_rate_diff_strict_minus_max"),
        "overlay_diff_strict_minus_max": cmp_.get("overlay_count_diff_strict_minus_max"),
        "strict_reduces_overlay_vs_max": cmp_.get("strict_reduces_overlay_vs_max"),
        "per_row_density_scale": (contrast.get("panel_inputs") or {}).get("per_row_density_scale"),
    }


def _append_row(log_path: Path, row: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, default=None)
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument(
        "--append-contrast-audit",
        action="store_true",
        help="Append contrast_zero_density row from ab_multi artifact.",
    )
    ap.add_argument(
        "--ab-multi-json",
        type=Path,
        default=DEFAULT_AB_MULTI,
        help="Source for --append-contrast-audit.",
    )
    ap.add_argument(
        "--contrast-only",
        action="store_true",
        help="Only append contrast audit (skip SSOT eval/gate row).",
    )
    args = ap.parse_args()

    appended = 0

    if not args.contrast_only:
        eval_path = _resolve_eval_path(args.eval_json)
        eval_doc = _read(eval_path)
        gate_doc = _read(args.gate_json)
        if not eval_doc or not gate_doc:
            print("[FATAL] missing eval or gate artifact")
            return 1
        row = _row_from_eval_gate(eval_doc, gate_doc)
        _append_row(args.log_jsonl, row)
        appended += 1
        print(f"APPENDED SSOT row: {args.log_jsonl}")
        print(
            f"decision={row['decision']} delta_hit_rate={row['delta_hit_rate']:.6f} "
            f"overlay_version={row.get('overlay_version')}"
        )

    if args.append_contrast_audit or args.contrast_only:
        multi_doc = _read(args.ab_multi_json)
        audit_row = _contrast_audit_row(multi_doc)
        if not audit_row:
            print(f"[WARN] no contrast_zero_density block in {args.ab_multi_json}")
            return 1 if args.contrast_only else 0
        _append_row(args.log_jsonl, audit_row)
        appended += 1
        print(f"APPENDED contrast audit: {args.log_jsonl}")
        print(
            f"overlay max={audit_row.get('overlay_v2b_max_merge')} "
            f"strict={audit_row.get('overlay_v2b_strict')} "
            f"delta_diff={audit_row.get('delta_diff_strict_minus_max')}"
        )

    if appended == 0:
        print("[FATAL] nothing appended")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
