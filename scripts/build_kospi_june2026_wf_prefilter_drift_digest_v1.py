#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Walk-forward prefilter vs snapshot/active-candidate drift digest [HYPO][RQ-032]."""

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

WF_BACKTEST = ROOT / "reports/kospi_multilens_walkforward_backtest_latest.json"
SNAP_VS_WF = ROOT / "reports/kospi_lens_ablation_snapshot_vs_walkforward_latest.json"
READINESS = ROOT / "reports/kospi_june2026_promotion_readiness_latest.json"
WEIGHT_COMPARE = ROOT / "reports/kospi_june2026_weight_candidate_compare_latest.json"
SNAPSHOT_BT = ROOT / "reports/kospi_multilens_blend_backtest_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_wf_prefilter_drift_digest_v1_latest.json"

ACTIVE_CANDIDATE = "v2_lens3_heavy"
WF_GATE_MIN_TOP1 = 0.52


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _variant_metrics(doc: dict[str, Any], variant_id: str) -> dict[str, Any] | None:
    for row in doc.get("variants") or []:
        if str(row.get("variant_id")) == variant_id:
            m = row.get("metrics")
            return m if isinstance(m, dict) else None
    best = doc.get("best_variant") if isinstance(doc.get("best_variant"), dict) else {}
    if str(best.get("variant_id")) == variant_id:
        m = best.get("metrics")
        return m if isinstance(m, dict) else None
    return None


def _fold_train_wins(wf: dict[str, Any], variant_id: str) -> int:
    n = 0
    for fold in wf.get("folds") or []:
        if str(fold.get("selected_from_train") or "") == variant_id:
            n += 1
    return n


def build_digest() -> dict[str, Any]:
    wf = _read_json(WF_BACKTEST)
    snap_wf = _read_json(SNAP_VS_WF)
    readiness = _read_json(READINESS)
    wcmp = _read_json(WEIGHT_COMPARE)
    snap_bt = _read_json(SNAPSHOT_BT)

    wf_summary = wf.get("summary") if isinstance(wf.get("summary"), dict) else {}
    selection_top1 = float(wf_summary.get("selection_top1_hit_rate") or 0.0)
    wf_top2 = list(wf_summary.get("recommended_prefilter_variants_top2") or [])
    wf_rank = wf_summary.get("variant_rank_by_test_mean_soft") or []

    gates = readiness.get("gates") if isinstance(readiness.get("gates"), dict) else {}
    wf_gate = gates.get("walkforward_prefilter") if isinstance(gates.get("walkforward_prefilter"), dict) else {}

    active_metrics = _variant_metrics(snap_bt, ACTIVE_CANDIDATE)
    active_4ai = _variant_metrics(snap_bt, f"{ACTIVE_CANDIDATE}_4ai_current")
    train_wins = _fold_train_wins(wf, ACTIVE_CANDIDATE)
    train_wins_4ai = _fold_train_wins(wf, f"{ACTIVE_CANDIDATE}_4ai_current")
    in_wf_rank = any(str(r.get("variant_id", "")).startswith("v2_lens3") for r in wf_rank)

    arm_deltas = snap_wf.get("arm_deltas") if isinstance(snap_wf.get("arm_deltas"), list) else []
    snapshot_bias_pp = None
    for row in arm_deltas:
        if row.get("arm_id") == "sasang_myeongni_only":
            snapshot_bias_pp = row.get("walkforward_minus_snapshot_pp")
            break

    root_causes: list[dict[str, Any]] = []
    if train_wins == 0 and train_wins_4ai == 0:
        root_causes.append(
            {
                "id": "active_never_wf_train_winner",
                "detail_ko": f"{ACTIVE_CANDIDATE}가 46-fold train 선택에서 0회 — WF prefilter rank에 미포함",
            }
        )
    if selection_top1 < WF_GATE_MIN_TOP1:
        root_causes.append(
            {
                "id": "low_selection_top1_hit_rate",
                "detail_ko": f"train→test top1 일치율 {selection_top1:.1%} < gate {WF_GATE_MIN_TOP1:.0%}",
            }
        )
    if snapshot_bias_pp is not None and float(snapshot_bias_pp) <= -3.0:
        root_causes.append(
            {
                "id": "snapshot_static_lens_bias",
                "detail_ko": f"sasang+명리 snapshot 대비 WF −{abs(float(snapshot_bias_pp)):.2f}pp — 정적 lens 편향",
            }
        )
    overlay = snap_wf.get("overlay_uplift_pp") if isinstance(snap_wf.get("overlay_uplift_pp"), dict) else {}
    if overlay.get("snapshot") is not None and overlay.get("walkforward") is not None:
        if float(overlay["snapshot"]) > 0 and float(overlay["walkforward"]) < 0:
            root_causes.append(
                {
                    "id": "four_ai_overlay_sign_flip",
                    "detail_ko": f"4AI overlay snapshot +{overlay['snapshot']}pp vs WF {overlay['walkforward']}pp",
                }
            )

    recommended_next: list[str] = [
        "WF grid에 v2_lens3_heavy(+4ai) test mean을 매 fold 강제 집계(run_backtest full variant rank)",
        "macro/logos per-date arm — walkforward_macro 확장 후 logos/field per-date PoC",
        "June n≥15 후 snapshot winner vs WF top2 forward shadow 비교 (apply 금지)",
        "R1 lens published 반영 — human sign-off 전 shadow-only 유지",
    ]

    return {
        "schema": "kospi_june2026_wf_prefilter_drift_digest_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "rq_pointer": "RQ-032",
        "active_candidate_id": ACTIVE_CANDIDATE,
        "walkforward_prefilter": {
            "selection_top1_hit_rate": selection_top1,
            "required_min_selection_top1": WF_GATE_MIN_TOP1,
            "pass": bool(wf_gate.get("pass")),
            "recommended_top2": wf_top2,
            "n_folds": wf_summary.get("n_folds"),
        },
        "active_candidate_vs_wf": {
            "snapshot_140d_soft_hr": (active_metrics or {}).get("soft_hit_rate"),
            "snapshot_140d_4ai_current_soft_hr": (active_4ai or {}).get("soft_hit_rate"),
            "wf_train_selection_wins": train_wins,
            "wf_train_selection_wins_4ai_current": train_wins_4ai,
            "appears_in_wf_test_mean_rank": in_wf_rank,
            "candidate_already_applied": bool(wcmp.get("candidate_status") == "applied_active"),
        },
        "snapshot_vs_walkforward_ablation": {
            "overlay_uplift_pp": overlay,
            "sasang_myeongni_snapshot_bias_pp": snapshot_bias_pp,
            "verdict_lines": snap_wf.get("verdict_lines") or [],
        },
        "root_causes": root_causes,
        "recommended_next_ko": recommended_next,
        "verdict_ko": (
            f"WF prefilter fail 구조적 — active {ACTIVE_CANDIDATE}는 snapshot 140d winner이나 "
            f"WF train winner 0회·top1={selection_top1:.1%}. evolution/promotion hold 유지."
        ),
        "sources": {
            "walkforward": str(WF_BACKTEST.relative_to(ROOT)).replace("\\", "/"),
            "snapshot_vs_walkforward": str(SNAP_VS_WF.relative_to(ROOT)).replace("\\", "/"),
            "readiness": str(READINESS.relative_to(ROOT)).replace("\\", "/"),
            "snapshot_backtest": str(SNAPSHOT_BT.relative_to(ROOT)).replace("\\", "/"),
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    doc = build_digest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    wf = doc.get("walkforward_prefilter") or {}
    active = doc.get("active_candidate_vs_wf") or {}
    print(
        f"WROTE: {args.output.resolve()} "
        f"wf_top1={wf.get('selection_top1_hit_rate')} "
        f"active_wf_train_wins={active.get('wf_train_selection_wins')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
