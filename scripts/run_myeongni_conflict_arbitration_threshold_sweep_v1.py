#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.myeongri_rule_school_mkm_4d_v1 import (
    apply_myeongni_conflict_arbitration_v1,
    load_myeongni_conflict_arbitration_v1,
)
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "myeongni_conflict_arbitration_threshold_sweep_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _toy_cases() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "balanced_reference",
            "vector": {"S": 0.24, "L": 0.18, "K": 0.18, "M": 0.40},
            "surface": {"wood_strength": 0.2, "fire_strength": 0.2, "earth_strength": 0.2, "metal_strength": 0.2, "water_strength": 0.2},
            "jijangan": {"wood_strength": 0.2, "fire_strength": 0.2, "earth_strength": 0.2, "metal_strength": 0.2, "water_strength": 0.2},
        },
        {
            "case_id": "extreme_jogoo_fire",
            "vector": {"S": 0.20, "L": 0.10, "K": 0.25, "M": 0.45},
            "surface": {"wood_strength": 0.0, "fire_strength": 1.0, "earth_strength": 0.0, "metal_strength": 0.0, "water_strength": 0.0},
            "jijangan": {"wood_strength": 0.0, "fire_strength": 0.8, "earth_strength": 0.2, "metal_strength": 0.0, "water_strength": 0.0},
        },
        {
            "case_id": "surface_jijangan_conflict_high",
            "vector": {"S": 0.26, "L": 0.12, "K": 0.12, "M": 0.50},
            "surface": {"wood_strength": 0.5, "fire_strength": 0.0, "earth_strength": 0.0, "metal_strength": 0.5, "water_strength": 0.0},
            "jijangan": {"wood_strength": 0.0, "fire_strength": 0.0, "earth_strength": 1.0, "metal_strength": 0.0, "water_strength": 0.0},
        },
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="Sweep threshold candidates for myeongni conflict arbitration v1.")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    base = load_myeongni_conflict_arbitration_v1()
    rules = base.get("arbitration_rules") or {}
    r1 = rules.get("rule_1_eokbu_vs_jogoo") or {}
    r2 = rules.get("rule_2_surface_vs_jijangan") or {}
    r3 = rules.get("rule_3_gyukguk_vs_4d_vector") or {}

    jogoo_grid = [0.7, 0.8, 0.9]
    jijangan_weight_grid = [1.3, 1.5, 1.7]
    stability_grid = [
        {"l_min": 0.35, "l_max": 0.65, "k_min": 0.35, "k_max": 0.65},
        {"l_min": 0.4, "l_max": 0.6, "k_min": 0.4, "k_max": 0.6},
        {"l_min": 0.45, "l_max": 0.55, "k_min": 0.45, "k_max": 0.55},
    ]

    rows: list[dict[str, Any]] = []
    for jogoo_cut, jijangan_w, band in itertools.product(jogoo_grid, jijangan_weight_grid, stability_grid):
        pol = json.loads(json.dumps(base))
        pol["arbitration_rules"]["rule_1_eokbu_vs_jogoo"]["threshold"]["jogoo_imbalance_abs"] = jogoo_cut
        pol["arbitration_rules"]["rule_2_surface_vs_jijangan"]["weights"]["surface_stem"] = float((r2.get("weights") or {}).get("surface_stem", 1.0))
        pol["arbitration_rules"]["rule_2_surface_vs_jijangan"]["weights"]["jijangan_root"] = jijangan_w
        pol["arbitration_rules"]["rule_3_gyukguk_vs_4d_vector"]["stability_band"] = band

        case_results = []
        stable_count = 0
        watch_count = 0
        for case in _toy_cases():
            out, meta = apply_myeongni_conflict_arbitration_v1(
                case["vector"],
                ohang_surface=case["surface"],
                ohang_jijangan=case["jijangan"],
                policy=pol,
            )
            label = str(meta.get("vector_policy_label"))
            if label == str(r3.get("upgrade_label_if_stable", "GO_SPECIAL_CONTROLLED")):
                stable_count += 1
            if label == str((base.get("guardrail") or {}).get("fallback_action", "WATCH")):
                watch_count += 1
            case_results.append(
                {
                    "case_id": case["case_id"],
                    "label": label,
                    "jogoo_triggered": bool(meta.get("jogoo_triggered")),
                    "m_multiplier_applied": meta.get("m_multiplier_applied"),
                    "vector_arbitrated": out,
                }
            )

        rows.append(
            {
                "jogoo_cut": jogoo_cut,
                "jijangan_root_weight": jijangan_w,
                "stability_band": band,
                "summary": {"stable_count": stable_count, "watch_count": watch_count},
                "cases": case_results,
            }
        )

    out_doc = {
        "schema": "myeongni_conflict_arbitration_threshold_sweep_v1",
        "generated_at_utc": _now(),
        "grid": {
            "jogoo_cut": jogoo_grid,
            "jijangan_root_weight": jijangan_weight_grid,
            "stability_band": stability_grid,
        },
        "rows": rows,
    }

    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "rows": len(rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
