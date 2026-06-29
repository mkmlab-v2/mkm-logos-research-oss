#!/usr/bin/env python3
"""Build L3 commander ack review packet for KOSPI Field band layer [HYPO]."""
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

DEFAULT_L2 = ROOT / "reports/kospi_field_band_extended_oos_v1_latest.json"
DEFAULT_JUNE_WF = ROOT / "reports/kospi_four_lens_conflict_band_coverage_wf_v1_latest.json"
DEFAULT_SHADOW = ROOT / "reports/kospi_field_band_shadow_replay_v1_latest.json"
DEFAULT_STACK = ROOT / "reports/kospi_field_band_stack_ensemble_v1_latest.json"
DEFAULT_RWC_SHADOW = ROOT / "reports/kospi_field_band_rwc_shadow_replay_v1_latest.json"
DEFAULT_STACK_COMPARE = ROOT / "reports/kospi_field_band_stack_compare_v1_latest.json"
DEFAULT_FINSTRESS = ROOT / "reports/kospi_finstress_ts_diagnostic_v1_latest.json"
DEFAULT_NESTED_REVAL = ROOT / "reports/kospi_field_band_nested_tune_revalidate_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/kospi_field_band_commander_ack_packet_v1_latest.json"
REPORT_OUT = ROOT / "reports/kospi_field_band_commander_ack_packet_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def build_commander_ack_packet(
    *,
    l2_doc: dict[str, Any],
    june_wf: dict[str, Any] | None,
    shadow: dict[str, Any] | None,
    tier2_chain: dict[str, Any] | None,
    stack_ensemble: dict[str, Any] | None = None,
    rwc_shadow: dict[str, Any] | None = None,
    stack_compare: dict[str, Any] | None = None,
    finstress: dict[str, Any] | None = None,
    nested_revalidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    l2_gates = l2_doc.get("l2_gates") or {}
    checks = l2_gates.get("checks") or {}
    panel = l2_doc.get("panel") or {}
    june_hold = ((june_wf or {}).get("holdout_pooled") or {}).get("band_conflict_vol_widen") or {}
    june_active = ((june_wf or {}).get("holdout_pooled") or {}).get("band_active") or {}
    june_cmp = (june_wf or {}).get("comparison") or {}

    nested_pass = (nested_revalidate or {}).get("revalidation_pass")
    checks["june_prophecy_nested_revalidate"] = nested_pass is True

    ack_ready = bool(l2_gates.get("l2_extended_oos_ready")) and all(
        checks.get(k) is True
        for k in (
            "holdout_n_ge_30",
            "multi_month_ge_2",
            "delta_vol_widen_ge_3pp",
            "direction_unchanged",
            "shadow_parity",
            "june_prophecy_nested_revalidate",
        )
    )

    caveats: list[str] = []
    if int(panel.get("science_backfill_rows") or 0) > 0:
        caveats.append(
            "Jan–Apr 81일은 science_core 균일 band [-2%,+2%] 백필 — May/June 예언 밴드와 혼합 패널."
        )
    if nested_pass is False:
        caveats.append("June prophecy nested revalidate 미통과 — pooled holdout tuned 수치 과대 가능.")
    caveats.append("direction fusion holdout 0.0pp — 방향 head 승격 금지 유지.")
    caveats.append("band_hit_rate ≠ PnL·드로다운 — 경제 지표 미측정.")
    caveats.append("Logos/명리/사상 Tier2는 digest·veto·router — 주문 경로 비주입.")
    caveats.append("RWC/CPTC conformal margin은 post-hoc 연구층 — 실매매 inject 아님.")
    if (finstress or {}).get("recommendation") == "late_condition_band_only_no_direction_fusion":
        caveats.append("FinStressTS: 방향 융합 재시도 금지·밴드 late conditioning 유지.")

    scope_if_ack = {
        "authorized": [
            "Field band_conflict_vol_widen shadow 계층 연구 배선 지속",
            "RWC-lite post-hoc shadow replay (Slot 2 Phase 2) 연구 로그",
            "premium/B-track 리포트에 band layer 요약 노출(연구 라벨)",
            "L4 Track A 후보 논의 착수(별도 ECC·CONSTITUTION 행)",
        ],
        "forbidden_until_L4": [
            "start_live_trading.py 패치·VPS auto-apply",
            "direction fusion 승격",
            "send_gate OPEN without separate ECC",
            "Track A compression KPI 합선",
        ],
    }

    return {
        "schema": "kospi_field_band_commander_ack_packet_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "ladder_stage": "L3_commander_ack_pending",
        "recommended_commander_action": "ACK_L3_BAND_SHADOW_RESEARCH" if ack_ready else "HOLD_FIX_GATES",
        "ack_ready": ack_ready,
        "metrics": {
            "june_prophecy_only": {
                "holdout_n": june_active.get("n_scored"),
                "band_active_rate": june_active.get("band_hit_rate"),
                "band_vol_widen_rate": june_hold.get("band_hit_rate"),
                "delta_pp": round(float(june_cmp.get("delta_conflict_vol_widen_minus_active_band_holdout") or 0.0) * 100.0, 2),
                "direction_soft_hit_rate": june_hold.get("direction_soft_hit_rate"),
            },
            "extended_oos_L2": {
                "holdout_n": l2_gates.get("holdout_n"),
                "n_months": l2_gates.get("n_months"),
                "band_active_rate": l2_gates.get("band_active_rate"),
                "band_vol_widen_rate": l2_gates.get("band_vol_widen_rate"),
                "delta_pp": l2_gates.get("delta_band_pp"),
                "direction_soft_hit_rate": l2_gates.get("direction_soft_hit_rate"),
                "science_backfill_rows": panel.get("science_backfill_rows"),
            },
            "shadow_replay": {
                "holdout_band_hit_rate": ((shadow or {}).get("summary") or {}).get("holdout_pooled", {}).get(
                    "band_hit_rate"
                ),
                "wf_parity": ((shadow or {}).get("summary") or {}).get("wf_parity"),
            },
            "conformal_stack_L2_extended": {
                "holdout_n": (
                    ((stack_ensemble or {}).get("summary") or {}).get("holdout_pooled", {}).get("stack") or {}
                ).get("n_scored"),
                "band_base_rate": (
                    ((stack_ensemble or {}).get("summary") or {}).get("holdout_pooled", {}).get("base") or {}
                ).get("band_hit_rate"),
                "band_rwc_rate": (
                    ((stack_ensemble or {}).get("summary") or {}).get("holdout_pooled", {}).get("rwc") or {}
                ).get("band_hit_rate"),
                "band_cptc_rate": (
                    ((stack_ensemble or {}).get("summary") or {}).get("holdout_pooled", {}).get("cptc") or {}
                ).get("band_hit_rate"),
                "band_stack_union_rate": (
                    ((stack_ensemble or {}).get("summary") or {}).get("holdout_pooled", {}).get("stack") or {}
                ).get("band_hit_rate"),
                "delta_stack_minus_base_pp": round(
                    float((stack_ensemble or {}).get("summary", {}).get("delta_stack_minus_base_holdout") or 0.0)
                    * 100.0,
                    2,
                ),
                "best_layer": (stack_compare or {}).get("stack", {}).get("best_band_layer"),
            },
            "rwc_shadow_replay": {
                "holdout_band_hit_rate": ((rwc_shadow or {}).get("summary") or {}).get("holdout_pooled", {}).get(
                    "band_hit_rate"
                ),
                "holdout_rwc_uplift_pp": round(
                    float((rwc_shadow or {}).get("summary", {}).get("holdout_rwc_uplift_pp") or 0.0) * 100.0, 2
                ),
                "rwc_parity_ok": ((rwc_shadow or {}).get("summary") or {}).get("rwc_parity", {}).get(
                    "within_tolerance"
                ),
            },
            "finstress_diagnostic": {
                "recommendation": (finstress or {}).get("recommendation"),
                "root_causes": (finstress or {}).get("root_cause_tags"),
            },
            "nested_tune_revalidate_june_prophecy": {
                "revalidation_pass": nested_pass,
                "june_holdout_n": (nested_revalidate or {}).get("june_holdout_prophecy_n"),
                "nested_delta_stack_pp": round(
                    float(
                        ((nested_revalidate or {}).get("june_holdout_metrics") or {})
                        .get("nested_tune", {})
                        .get("delta_stack_minus_base")
                        or 0.0
                    )
                    * 100.0,
                    2,
                ),
                "frozen_policy_june_delta_pp": round(
                    float(
                        ((nested_revalidate or {}).get("june_holdout_metrics") or {})
                        .get("frozen_pooled_holdout_policy", {})
                        .get("delta_stack_minus_base")
                        or 0.0
                    )
                    * 100.0,
                    2,
                ),
            },
        },
        "l2_checks": checks,
        "tier2_summary": (tier2_chain or {}).get("summary"),
        "caveats_ko": caveats,
        "scope_if_ack": scope_if_ack,
        "commander_checklist": [
            "band layer만 승격 후보임을 이해했는가 (direction head 제외)",
            "science_core 백필 구간 혼합 패널 한계를 인지했는가",
            "L3 ack가 실매매·VPS inject GO가 아님을 확인했는가",
            "send_gate HOLD 유지 및 Track A 격벽 동의",
        ],
        "approval_command": (
            "py scripts/record_kospi_field_band_commander_ack_v1.py "
            "--ack-reference COMMANDER-KOSPI-BAND-L3-ACK-YYYY-MM-DD"
        ),
        "evidence_pointers": {
            "extended_oos": _rel(DEFAULT_L2),
            "june_band_wf": _rel(DEFAULT_JUNE_WF),
            "shadow_replay": _rel(DEFAULT_SHADOW),
            "rwc_shadow_replay": _rel(DEFAULT_RWC_SHADOW),
            "stack_ensemble": _rel(DEFAULT_STACK),
            "stack_compare": _rel(DEFAULT_STACK_COMPARE),
            "finstress": _rel(DEFAULT_FINSTRESS),
            "nested_revalidate": _rel(DEFAULT_NESTED_REVAL),
            "tier2_chain": _rel(ROOT / "reports/kospi_four_lens_per_lens_tier2_chain_v1_latest.json"),
            "injection_plan": "docs/research/kospi_field_band_shadow_injection_plan_v1.md",
            "checklist_md": "docs/research/kospi_field_band_commander_ack_checklist_v1.md",
        },
        "track_wall": {
            "no_track_a_live_auto_merge": True,
            "auto_apply": False,
            "direction_fusion_promotion": False,
        },
        "reproduce": "py scripts/build_kospi_field_band_commander_ack_packet_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--l2-json", type=Path, default=DEFAULT_L2)
    ap.add_argument("--june-wf-json", type=Path, default=DEFAULT_JUNE_WF)
    ap.add_argument("--shadow-json", type=Path, default=DEFAULT_SHADOW)
    ap.add_argument("--stack-json", type=Path, default=DEFAULT_STACK)
    ap.add_argument("--rwc-shadow-json", type=Path, default=DEFAULT_RWC_SHADOW)
    ap.add_argument("--stack-compare-json", type=Path, default=DEFAULT_STACK_COMPARE)
    ap.add_argument("--finstress-json", type=Path, default=DEFAULT_FINSTRESS)
    ap.add_argument("--nested-revalidate-json", type=Path, default=DEFAULT_NESTED_REVAL)
    ap.add_argument("--tier2-chain-json", type=Path, default=ROOT / "reports/kospi_four_lens_per_lens_tier2_chain_v1_latest.json")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    l2 = _read(args.l2_json)
    if not l2:
        print(f"Missing L2 artifact: {args.l2_json}", file=sys.stderr)
        return 2

    doc = build_commander_ack_packet(
        l2_doc=l2,
        june_wf=_read(args.june_wf_json),
        shadow=_read(args.shadow_json),
        tier2_chain=_read(args.tier2_chain_json),
        stack_ensemble=_read(args.stack_json),
        rwc_shadow=_read(args.rwc_shadow_json),
        stack_compare=_read(args.stack_compare_json),
        finstress=_read(args.finstress_json),
        nested_revalidate=_read(args.nested_revalidate_json),
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(payload, encoding="utf-8")
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": True, "ack_ready": doc["ack_ready"], "action": doc["recommended_commander_action"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
