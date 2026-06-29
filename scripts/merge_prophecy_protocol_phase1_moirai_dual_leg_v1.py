#!/usr/bin/env python3
"""Compare Phase1 harmonization (252d/5bps) vs Moirai dual-leg @ 2bps vs baselines [HYPO].

No Track A merge; protocols labeled explicitly.
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

DEFAULT_PHASE1 = ROOT / "reports/prophecy_protocol_harmonization_phase1_v1_latest.json"
DEFAULT_MOIRAI = ROOT / "reports/rq025_moirai2_dual_leg_wf_shadow_v1_latest.json"
DEFAULT_LANE_OPS = ROOT / "reports/prophecy_lens_lane_ops_board_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/prophecy_protocol_phase1_moirai_dual_leg_compare_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/prophecy_protocol_phase1_moirai_dual_leg_compare_v1_latest.json"

SCHEMA = "prophecy_protocol_phase1_moirai_dual_leg_compare_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _moirai_pooled(moirai: dict[str, Any], arm_id: str) -> dict[str, Any] | None:
    for arm in moirai.get("dual_leg_pooled_arms") or moirai.get("pooled_arms") or []:
        if arm.get("arm_id") == arm_id:
            return arm
    for panel in moirai.get("per_instrument") or []:
        for arm in panel.get("arms") or []:
            if arm.get("arm_id") == arm_id:
                return arm
    return None


def build_compare(
    *,
    phase1_path: Path,
    moirai_path: Path,
    lane_ops_path: Path,
) -> dict[str, Any]:
    phase1 = _read_json(phase1_path)
    moirai = _read_json(moirai_path)
    lane_ops = _read_json(lane_ops_path)

    p1_inst = (
        (phase1.get("recommended_chain_252d_5bps") or {}).get("instrument_combo_walkforward") or {}
    )
    p1_lens = (phase1.get("recommended_chain_252d_5bps") or {}).get("lens_walkforward_btc_target") or {}
    baseline_inst = (
        (phase1.get("recommended_chain_180d_2bps_baseline") or {}).get("instrument_walkforward") or {}
    )
    baseline_lens = (phase1.get("recommended_chain_180d_2bps_baseline") or {}).get("lens_walkforward") or {}
    rq025 = phase1.get("rq025_reference_kospi_252d_5bps") or {}

    moirai_arm = _moirai_pooled(moirai, "moirai2_median_quantile") or _moirai_pooled(
        moirai, "moirai2_quantile_shadow"
    ) or {}
    mom_arm = _moirai_pooled(moirai, "mom_20d") or {}
    moirai_proto = moirai.get("protocol") or {}

    quant_lane = ((lane_ops.get("lanes") or {}).get("quant") or {}).get("metrics_180d_2bps") or {}

    inst_5 = p1_inst.get("mean_test_accuracy")
    inst_2 = baseline_inst.get("mean_test_accuracy")
    moirai_pooled = moirai_arm.get("pooled_test_directional_hit_rate")
    quant_panel_hr = quant_lane.get("directional_hit_rate_active")

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "mission_line": "P2 baseline compare — Phase1 252d/5bps vs Moirai dual-leg 180d/2bps vs quant shadow",
        "rows": [
            {
                "row_id": "recommended_instrument_combo",
                "protocol": "dual_leg 252d / 5bps / 5-fold instrument WF",
                "hr": inst_5,
                "hr_kind": "mean_test_accuracy",
                "artifact": (phase1.get("chain_run") or {}).get("artifacts", {}).get("inst"),
            },
            {
                "row_id": "recommended_instrument_combo_baseline",
                "protocol": "dual_leg 180d / 2bps / 6-fold instrument WF",
                "hr": inst_2,
                "hr_kind": "mean_test_accuracy",
                "artifact": baseline_inst.get("artifact"),
            },
            {
                "row_id": "moirai2_dual_leg_pooled",
                "protocol": f"dual_leg {moirai_proto.get('last_n_intersection')}d / "
                f"{moirai_proto.get('neutral_bps')}bps / {moirai_proto.get('n_folds')}-fold TSFM",
                "hr": moirai_pooled,
                "hr_kind": "pooled_test_directional_hit_rate",
                "kospi_leg_hr": next(
                    (
                        p.get("pooled_test_directional_hit_rate")
                        for p in (moirai_arm.get("per_instrument") or [])
                        if p.get("instrument_id") == "kospi"
                    ),
                    None,
                ),
                "btc_leg_hr": next(
                    (
                        p.get("pooled_test_directional_hit_rate")
                        for p in (moirai_arm.get("per_instrument") or [])
                        if p.get("instrument_id") == "btc"
                    ),
                    None,
                ),
                "artifact": _rel(moirai_path),
            },
            {
                "row_id": "mom_20d_dual_leg_pooled",
                "protocol": moirai_proto,
                "hr": mom_arm.get("pooled_test_directional_hit_rate"),
                "hr_kind": "pooled_test_directional_hit_rate",
                "artifact": _rel(moirai_path),
            },
            {
                "row_id": "rq025_kospi_ensemble_252d_5bps",
                "protocol": "kospi_only 252d / 5bps",
                "hr": rq025.get("per_date_kospi_ensemble_pooled_hr"),
                "hr_kind": "pooled_test_directional_hit_rate",
                "artifact": rq025.get("artifact"),
            },
            {
                "row_id": "quant_arm_a_science_sasang",
                "protocol": "science_core panel 180d / 2bps shadow ablation",
                "hr": quant_panel_hr,
                "hr_kind": "directional_hit_rate_active",
                "artifact": (lane_ops.get("artifact_pointers") or {}).get("shadow_ablation_v2"),
                "note_ko": "Quant SSOT — 다른 프로토콜; TSFM/recommended chain으로 대체 금지",
            },
        ],
        "lens_baseline_compare": {
            "phase1_252d_5bps_lens_mean": p1_lens.get("mean_test_accuracy"),
            "baseline_180d_2bps_lens_mean": baseline_lens.get("mean_test_accuracy"),
        },
        "delta_pp": {
            "moirai_2bps_vs_recommended_inst_2bps": round((float(moirai_pooled) - float(inst_2)) * 100, 4)
            if moirai_pooled is not None and inst_2 is not None
            else None,
            "moirai_2bps_vs_quant_arm_a_panel": round((float(moirai_pooled) - float(quant_panel_hr)) * 100, 4)
            if moirai_pooled is not None and quant_panel_hr is not None
            else None,
            "recommended_inst_5bps_vs_rq025_ensemble": (
                phase1.get("cross_protocol_compare_pp") or {}
            ).get("instrument_5bps_dual_leg_vs_rq025_ensemble_pooled"),
        },
        "verdict_ko": [
            "Moirai dual-leg 57.4% pooled @ 2bps/180d — recommended instrument 54.0% @ 2bps/180d 대비 +3.4pp이나 "
            "모델·코호트·채점 경로 상이 → quant SSOT(Arm A 63.9%) 또는 Track A 승격 근거 아님",
            "KOSPI leg 66.2%는 100% bull pred 편향 caveat — rq025_tsfm_delta_arms 참조",
            "Phase1 instrument 57.7% @ 5bps/252d는 RQ-025 ensemble 55.2%보다 높으나 dual-leg vs kospi-only",
            "P2 결론: TSFM shadow 유지; Primary/quant 경로 무변경",
        ],
        "artifact_pointers": {
            "phase1_harmonization": _rel(phase1_path),
            "moirai_dual_leg": _rel(moirai_path),
            "lane_ops_board": _rel(lane_ops_path),
        },
        "ok": bool(phase1.get("ok")) and bool(moirai),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--phase1", type=Path, default=DEFAULT_PHASE1)
    ap.add_argument("--moirai", type=Path, default=DEFAULT_MOIRAI)
    ap.add_argument("--lane-ops", type=Path, default=DEFAULT_LANE_OPS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    payload = build_compare(
        phase1_path=args.phase1,
        moirai_path=args.moirai,
        lane_ops_path=args.lane_ops,
    )

    for path in (args.output, args.artifact_output):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not payload.get("ok"):
        print("FAIL: upstream artifacts missing", file=sys.stderr)
        return 1
    moirai_hr = next((r.get("hr") for r in payload.get("rows") or [] if r.get("row_id") == "moirai2_dual_leg_pooled"), None)
    print(f"OK moirai_pooled={moirai_hr} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
