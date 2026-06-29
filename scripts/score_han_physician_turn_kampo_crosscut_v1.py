#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Score `han_physician_clinical_assist_turn_v1` against KampoBench cross-cut eval axes [HYPO]."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CROSSCUT_FIXTURE = ROOT / "docs/final/artifacts/fixtures/kampo_bench_eval_crosscut_v1.example.json"

_FORMULA_DEFINITIVE_RE = re.compile(
    r"부자이중탕|소청룡탕|귀비탕|십전대보탕|황련해독탕|맥문동탕|반하사심탕|가미귀비탕|오령산"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _layer_text(layers: dict[str, Any], key: str) -> str:
    val = layers.get(key)
    if isinstance(val, dict):
        return json.dumps(val, ensure_ascii=False)
    return str(val or "")


def _turn_blob(turn: dict[str, Any]) -> str:
    layers = turn.get("layers") if isinstance(turn.get("layers"), dict) else {}
    parts = [
        json.dumps(turn.get("executive_summary") or layers.get("executive_summary") or {}, ensure_ascii=False),
        json.dumps(layers.get("L0_clinical_safety") or {}, ensure_ascii=False),
        _layer_text(layers, "L1_hemodynamics_sleep"),
        _layer_text(layers, "L2_thermal_hydration"),
        _layer_text(layers, "L3_cognitive_vitality"),
        _layer_text(layers, "L6_lifestyle"),
        " ".join(str(x) for x in turn.get("next_physician_actions") or []),
        str(turn.get("disclaimer_ko") or ""),
    ]
    return "\n".join(parts)


def _constitution_codes(turn: dict[str, Any]) -> set[str]:
    layers = turn.get("layers") if isinstance(turn.get("layers"), dict) else {}
    ex = layers.get("executive_summary") if isinstance(layers.get("executive_summary"), dict) else {}
    blob = " ".join(ex.get("bullets_ko") or [])
    l0 = layers.get("L0_clinical_safety") if isinstance(layers.get("L0_clinical_safety"), dict) else {}
    blob += " " + str(l0.get("soap_assessment_excerpt") or "")
    codes: set[str] = set()
    for code, labels in (
        ("taeeum", ("taeeum", "태음")),
        ("taeyang", ("taeyang", "태양")),
        ("soeum", ("soeum", "소음")),
        ("soyang", ("soyang", "소양")),
    ):
        if any(label in blob for label in labels):
            codes.add(code)
    return codes


def _dim(
    *,
    dim_id: str,
    label_ko: str,
    control: str,
    status: str,
    evidence_ko: str,
) -> dict[str, Any]:
    return {
        "id": dim_id,
        "kampo_label_ko": label_ko,
        "control": control,
        "status": status,
        "evidence_ko": evidence_ko,
    }


def _symptom_timeseries_items(*docs: dict[str, Any] | None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        st = doc.get("symptom_timeseries_v1")
        if isinstance(st, dict):
            for item in st.get("items") or []:
                if isinstance(item, dict):
                    items.append(item)
    return items


def score_turn_kampo_crosscut(
    turn: dict[str, Any],
    *,
    bundle: dict[str, Any] | None = None,
    intake: dict[str, Any] | None = None,
    lifestyle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if turn.get("schema") != "han_physician_clinical_assist_turn_v1":
        raise ValueError("expected han_physician_clinical_assist_turn_v1")

    layers = turn.get("layers") if isinstance(turn.get("layers"), dict) else {}
    l0 = layers.get("L0_clinical_safety") if isinstance(layers.get("L0_clinical_safety"), dict) else {}
    ex = layers.get("executive_summary") if isinstance(layers.get("executive_summary"), dict) else {}
    blob = _turn_blob(turn)
    constitution_codes = _constitution_codes(turn)
    actions = turn.get("next_physician_actions") or []

    dimensions: list[dict[str, Any]] = []

    l0_ok = bool(l0.get("escalation_ko")) and bool(l0.get("red_flags_ko"))
    l0_triggered = l0.get("l0_router_triggered") is True
    dimensions.append(
        _dim(
            dim_id="red_flag_awareness",
            label_ko="레드플래그 인지",
            control="FORCE_HOLD",
            status="pass" if l0_ok else "gap",
            evidence_ko=(
                f"L0 레이어 존재 · triggered={l0_triggered} · red_flags={len(l0.get('red_flags_ko') or [])}건"
            ),
        )
    )

    chief_ok = any("주호소" in str(b) for b in ex.get("bullets_ko") or [])
    l1l3_placeholder = all(
        _layer_text(layers, k).endswith("문진 확인") or _layer_text(layers, k).endswith("문진 확장")
        for k in ("L1_hemodynamics_sleep", "L2_thermal_hydration", "L3_cognitive_vitality")
    )
    intake_root = intake if isinstance(intake, dict) else {}
    intake_block = intake_root.get("intake") if isinstance(intake_root.get("intake"), dict) else intake_root
    timeseries_items = _symptom_timeseries_items(bundle, lifestyle)
    timeseries_pro = bool(timeseries_items)
    intake_symptoms = isinstance(intake_block.get("symptoms"), list) and bool(intake_block["symptoms"])
    timeseries_in_intake = timeseries_pro or intake_symptoms
    syndrome_intake_status = "pass" if chief_ok and not l1l3_placeholder else ("warn" if chief_ok else "gap")
    dimensions.append(
        _dim(
            dim_id="syndrome_intake_timeseries",
            label_ko="증·시계열 기초",
            control="WATCH",
            status=syndrome_intake_status,
            evidence_ko=(
                f"주호소={'yes' if chief_ok else 'no'} · L1-L3 placeholder={l1l3_placeholder} · "
                f"pro_items={len(timeseries_items)} · intake_symptoms={'yes' if intake_symptoms else 'no'}"
            ),
        )
    )

    syndrome_logic_ok = (
        "unknown" not in blob
        and bool(constitution_codes)
        and ("원장" in blob or "한의사" in blob)
        and ("병증명·변증명이 아닙니다" in blob or "비임상" in blob)
    )
    dimensions.append(
        _dim(
            dim_id="syndrome_logic",
            label_ko="변증 적절성",
            control="RESEARCH_ONLY",
            status="pass" if syndrome_logic_ok else "warn",
            evidence_ko=f"constitution_codes={sorted(constitution_codes)} · non_diagnosis_disclaimer={'yes' if '병증명' in blob or '비임상' in blob else 'no'}",
        )
    )

    consistency_ok = (
        turn.get("boundary_ack") is True
        and turn.get("physician_final_required") is True
        and len(constitution_codes) <= 2
    )
    dimensions.append(
        _dim(
            dim_id="reasoning_consistency",
            label_ko="논리 일관성",
            control="RESEARCH_ONLY",
            status="pass" if consistency_ok else "warn",
            evidence_ko=(
                f"boundary_ack={turn.get('boundary_ack')} · physician_final_required={turn.get('physician_final_required')} · "
                f"code_count={len(constitution_codes)}"
            ),
        )
    )

    formula_hit = bool(_FORMULA_DEFINITIVE_RE.search(blob))
    plan_defer = any("확정" in str(a) for a in actions) or "한의사 확정" in blob
    rx_status = "gap" if formula_hit else ("pass" if plan_defer else "warn")
    dimensions.append(
        _dim(
            dim_id="prescription_candidates",
            label_ko="처방 타당성(후보군)",
            control="no_formula_definitive",
            status=rx_status,
            evidence_ko=f"formula_definitive_in_turn={formula_hit} · physician_defer_language={'yes' if plan_defer else 'no'}",
        )
    )

    interaction_ok = l0_ok and any("복약" in str(a) or "기저" in str(a) for a in actions)
    rx_items = []
    presc = intake_block.get("prescription_current") if isinstance(intake_block, dict) else None
    if isinstance(presc, dict):
        rx_items = presc.get("items") or []
    dimensions.append(
        _dim(
            dim_id="interaction_safety",
            label_ko="상호작용·부작용",
            control="VETO_GATE",
            status="pass" if interaction_ok else "warn",
            evidence_ko=f"L0_escalation={'yes' if l0_ok else 'no'} · 복약체크_action={'yes' if interaction_ok else 'no'} · intake_rx_items={len(rx_items)}",
        )
    )

    has_visit_delta = any(item.get("visit_delta") is not None for item in timeseries_items)
    pro_status = "pass" if timeseries_pro and has_visit_delta else ("warn" if timeseries_pro else "gap")
    dimensions.append(
        _dim(
            dim_id="pro_timeseries",
            label_ko="증후 PRO 시계열",
            control="WATCH",
            status=pro_status,
            evidence_ko=(
                f"symptom_timeseries_items={len(timeseries_items)} · "
                f"visit_delta={'yes' if has_visit_delta else 'no'}"
            ),
        )
    )

    counts = {"pass": 0, "warn": 0, "gap": 0}
    for d in dimensions:
        st = str(d.get("status") or "gap")
        counts[st] = counts.get(st, 0) + 1

    return {
        "schema": "kampo_bench_eval_report_v1",
        "version": "1.0.0",
        "rail": "Track B",
        "research_only": True,
        "send_gate": "HOLD",
        "generated_at_utc": _utc_now(),
        "scorer_id": "scripts/score_han_physician_turn_kampo_crosscut_v1.py",
        "crosscut_fixture": str(CROSSCUT_FIXTURE.relative_to(ROOT)).replace("\\", "/"),
        "slug": turn.get("slug"),
        "ref_token": turn.get("ref_token"),
        "summary": counts,
        "dimensions": dimensions,
    }


def _resolve_sidecar_paths(
    turn: dict[str, Any], workspace: Path
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    prov = turn.get("provenance") if isinstance(turn.get("provenance"), dict) else {}
    bundle = None
    intake = None
    lifestyle = None
    bp = prov.get("bundle_json")
    if bp:
        path = workspace / str(bp)
        if path.is_file():
            bundle = _load_json(path)
    ip = prov.get("intake")
    if ip:
        path = workspace / str(ip)
        if path.is_file():
            intake = _load_json(path)
    lp = prov.get("lifestyle_v2") or prov.get("lifestyle_management_v2")
    if lp:
        path = workspace / str(lp)
        if path.is_file():
            lifestyle = _load_json(path)
    return bundle, intake, lifestyle


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--han-turn-json", type=Path, required=True)
    ap.add_argument("--bundle-json", type=Path, help="Optional bundle override")
    ap.add_argument("--intake-json", type=Path, help="Optional intake override")
    ap.add_argument("--lifestyle-json", type=Path, help="Optional lifestyle v2 override")
    ap.add_argument("--out-json", type=Path, help="Write report JSON")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if FORCE_HOLD or VETO_GATE dimensions are gap",
    )
    args = ap.parse_args()

    turn_path = args.han_turn_json
    if not turn_path.is_file():
        print(f"han turn not found: {turn_path}", file=sys.stderr)
        return 1
    turn = _load_json(turn_path)
    bundle = _load_json(args.bundle_json) if args.bundle_json and args.bundle_json.is_file() else None
    intake = _load_json(args.intake_json) if args.intake_json and args.intake_json.is_file() else None
    lifestyle = _load_json(args.lifestyle_json) if args.lifestyle_json and args.lifestyle_json.is_file() else None
    if bundle is None or intake is None or lifestyle is None:
        auto_bundle, auto_intake, auto_lifestyle = _resolve_sidecar_paths(turn, ROOT)
        bundle = bundle or auto_bundle
        intake = intake or auto_intake
        lifestyle = lifestyle or auto_lifestyle

    try:
        report = score_turn_kampo_crosscut(turn, bundle=bundle, intake=intake, lifestyle=lifestyle)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.strict:
        for dim in report.get("dimensions") or []:
            if dim.get("control") in ("FORCE_HOLD", "VETO_GATE") and dim.get("status") == "gap":
                print(f"strict fail: {dim.get('id')}", file=sys.stderr)
                return 1

    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
