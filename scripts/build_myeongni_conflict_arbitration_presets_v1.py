#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SWEEP = ROOT / "docs" / "final" / "artifacts" / "myeongni_conflict_arbitration_threshold_sweep_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "myeongni_conflict_arbitration_presets_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _pick_by_targets(rows: list[dict[str, Any]], *, jogoo_cut: float, jijangan_weight: float, l_min: float, l_max: float, k_min: float, k_max: float) -> dict[str, Any] | None:
    for r in rows:
        b = r.get("stability_band") or {}
        if (
            float(r.get("jogoo_cut", -1)) == jogoo_cut
            and float(r.get("jijangan_root_weight", -1)) == jijangan_weight
            and float(b.get("l_min", -1)) == l_min
            and float(b.get("l_max", -1)) == l_max
            and float(b.get("k_min", -1)) == k_min
            and float(b.get("k_max", -1)) == k_max
        ):
            return r
    return None


def _preset_doc(name: str, row: dict[str, Any], rationale: str) -> dict[str, Any]:
    b = row.get("stability_band") or {}
    return {
        "preset_name": name,
        "recommended_policy_patch": {
            "rule_1_eokbu_vs_jogoo.threshold.jogoo_imbalance_abs": row.get("jogoo_cut"),
            "rule_2_surface_vs_jijangan.weights.jijangan_root": row.get("jijangan_root_weight"),
            "rule_3_gyukguk_vs_4d_vector.stability_band": {
                "l_min": b.get("l_min"),
                "l_max": b.get("l_max"),
                "k_min": b.get("k_min"),
                "k_max": b.get("k_max"),
            },
        },
        "sweep_summary": row.get("summary") or {},
        "rationale": rationale,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build conservative/neutral/aggressive preset recommendations from arbitration sweep.")
    ap.add_argument("--sweep-json", type=Path, default=DEFAULT_SWEEP)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    sweep_path = args.sweep_json if args.sweep_json.is_absolute() else ROOT / args.sweep_json
    doc = _read_json(sweep_path)
    rows = list(doc.get("rows") or [])
    if not rows:
        raise SystemExit("no rows in sweep result")

    conservative = _pick_by_targets(rows, jogoo_cut=0.7, jijangan_weight=1.7, l_min=0.45, l_max=0.55, k_min=0.45, k_max=0.55) or rows[0]
    neutral = _pick_by_targets(rows, jogoo_cut=0.8, jijangan_weight=1.5, l_min=0.4, l_max=0.6, k_min=0.4, k_max=0.6) or rows[min(1, len(rows)-1)]
    aggressive = _pick_by_targets(rows, jogoo_cut=0.9, jijangan_weight=1.3, l_min=0.35, l_max=0.65, k_min=0.35, k_max=0.65) or rows[-1]

    out = {
        "schema": "myeongni_conflict_arbitration_presets_v1",
        "generated_at_utc": _now(),
        "source_sweep_json": str(sweep_path.resolve()),
        "note": "현재 스윕 toy-case에서는 모든 조합이 WATCH로 나타나므로, 프리셋은 리스크 성향 기준으로 제안한다.",
        "presets": [
            _preset_doc(
                "conservative",
                conservative,
                "조후 민감도를 높이고(낮은 cut), 지장간 가중과 안정밴드를 엄격하게 둬 과잉 해석을 억제.",
            ),
            _preset_doc(
                "neutral",
                neutral,
                "현재 v1.1 기본 정책과 동일한 균형형.",
            ),
            _preset_doc(
                "aggressive",
                aggressive,
                "조후 트리거를 보수적으로(높은 cut) 두고 안정밴드를 넓혀 특수 GO 승격 가능성을 높임.",
            ),
        ],
    }

    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
