#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build `han_physician_clinical_assist_turn_v1` JSON/MD from patient pointer + care bundle."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_TURN = ROOT / "docs" / "final" / "schemas" / "han_physician_clinical_assist_turn_v1.schema.json"
REGISTRY = ROOT / "docs" / "final" / "artifacts" / "patient_encounter_registry_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pointer_for_slug(slug: str) -> Path:
    return ROOT / "reports" / f"{slug}_intake_ssot_pointer_v1.json"


def _validate_turn(doc: dict[str, Any]) -> None:
    try:
        import jsonschema
    except ImportError:
        return
    schema = json.loads(SCHEMA_TURN.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)


def _soap_text(soap: dict[str, Any], key: str) -> str:
    block = soap.get(key)
    if isinstance(block, dict):
        return str(block.get("text") or "").strip()
    return str(block or "").strip()


_SASANG_CODE_PATTERNS: list[tuple[str, list[str]]] = [
    ("taeeum", ["태음인", "taeeum_in", "taeeum"]),
    ("taeyang", ["태양인", "taeyang_in", "taeyang"]),
    ("soeum", ["소음인", "soeum_in", "soeum"]),
    ("soyang", ["소양인", "soyang_in", "soyang"]),
]


def _match_sasang_code_in_text(text: str) -> str:
    blob = text or ""
    for code, patterns in _SASANG_CODE_PATTERNS:
        for pattern in patterns:
            if pattern in blob:
                return code
    return "unknown"


def _resolve_sasang_candidate(
    *,
    intake: dict[str, Any] | None,
    assess: str,
    sasang_slot_body: str,
) -> str:
    intake_root = intake if isinstance(intake, dict) else {}
    intake_block = intake_root.get("intake") if isinstance(intake_root.get("intake"), dict) else intake_root
    estimate = intake_block.get("sasang_estimate") if isinstance(intake_block.get("sasang_estimate"), dict) else {}
    label = str(estimate.get("label") or "").strip()
    if label:
        code = _match_sasang_code_in_text(label)
        if code != "unknown":
            return code
    scores = estimate.get("fit_scores_hypo") if isinstance(estimate.get("fit_scores_hypo"), dict) else {}
    if scores:
        best_key = max(scores, key=lambda k: float(scores[k] or 0))
        code = _match_sasang_code_in_text(str(best_key))
        if code != "unknown":
            return code
    code = _match_sasang_code_in_text(assess)
    if code != "unknown":
        return code
    head = sasang_slot_body[:1200] if sasang_slot_body else ""
    return _match_sasang_code_in_text(head)


def _build_l0_layer(
    *,
    bundle: dict[str, Any],
    intake: dict[str, Any] | None = None,
) -> dict[str, Any]:
    assess = _soap_text(bundle.get("clinical_soap_v1") or {}, "assessment")
    try:
        from scripts.l0_red_flag_router_v1 import (
            collect_l0_state_from_bundle,
            collect_l0_state_from_sequence,
            format_han_turn_l0_layer,
            load_sequence_for_bundle,
            merge_l0_states,
        )

        seq = load_sequence_for_bundle(bundle, workspace_root=ROOT)
        seq_state = collect_l0_state_from_sequence(seq) if seq else None
        bundle_state = collect_l0_state_from_bundle(bundle, intake)
        l0_state = merge_l0_states(seq_state, bundle_state)
        layer = format_han_turn_l0_layer(l0_state)
        layer["soap_assessment_excerpt"] = assess[:400] or layer.get("soap_assessment_excerpt", "")
        return layer
    except Exception:
        pass
    return {
        "red_flags_ko": ["번들·문진 기반 — 추가 red flag 문진 필요"],
        "escalation_ko": "응급 신호 시 대면/응급 경로 우선",
        "soap_assessment_excerpt": assess[:400] or "(평가 미기재)",
        "l0_router_triggered": False,
    }


def _intake_block(intake: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(intake, dict):
        return {}
    block = intake.get("intake")
    return block if isinstance(block, dict) else intake


def _symptom_list(intake: dict[str, Any] | None, subj: str) -> list[str]:
    block = _intake_block(intake)
    symptoms: list[str] = []
    raw = block.get("symptoms") or intake.get("symptoms") if isinstance(intake, dict) else None
    if isinstance(raw, list):
        symptoms.extend(str(x).strip() for x in raw if str(x).strip())
    elif isinstance(raw, str) and raw.strip():
        symptoms.append(raw.strip())
    if not symptoms and subj:
        for line in subj.splitlines():
            line = line.strip().lstrip("-").strip()
            if line and not line.startswith("#"):
                symptoms.append(line[:120])
                break
    return symptoms


def _match_symptoms(symptoms: list[str], keywords: tuple[str, ...]) -> list[str]:
    hits: list[str] = []
    for symptom in symptoms:
        if any(kw in symptom for kw in keywords):
            hits.append(symptom)
    return hits


def _format_layer_line(axis_ko: str, items: list[str], *, fallback: str) -> str:
    if not items:
        return fallback
    joined = " · ".join(items[:4])
    return f"{axis_ko}: {joined} (입력·문진 정리 — 원장 확정 전)"


def _build_l1_l3_layers(
    *,
    intake: dict[str, Any] | None,
    lifestyle: dict[str, Any] | None,
    subj: str,
) -> tuple[str, str, str]:
    symptoms = _symptom_list(intake, subj)
    block = _intake_block(intake)
    notes = str(block.get("subjective_notes") or block.get("situation") or "")
    if notes and not symptoms:
        symptoms = [notes[:160]]

    l1_items = _match_symptoms(
        symptoms,
        ("순환", "손발", "추위", "부종", "말초", "자율", "수면", "어지", "혈압", "심계"),
    )
    l2_items = _match_symptoms(
        symptoms,
        ("한열", "상열", "하한", "작열", "열감", "소화", "갈증", "입 마", "땀", "더운", "차고"),
    )
    l3_items = _match_symptoms(
        symptoms,
        ("피로", "활력", "인지", "통증", "어깨", "손목", "육아", "수유", "무겁", "집중"),
    )

    if lifestyle and isinstance(lifestyle.get("weekly_self_check_ko"), list):
        for item in lifestyle["weekly_self_check_ko"][:2]:
            text = str(item)
            if "수면" in text or "복용" in text:
                l1_items.append(text)
            elif "발한" in text or "굶" in text:
                l2_items.append(text)

    return (
        _format_layer_line("수면/자율 축", l1_items, fallback="수면/자율 축: 문진 확인"),
        _format_layer_line("한열·소화 축", l2_items, fallback="한열·소화 축: 문진 확인"),
        _format_layer_line("활력·인지 축", l3_items, fallback="활력·인지: 문진 확장"),
    )


def _build_l6_layer(lifestyle: dict[str, Any] | None) -> str:
    if not isinstance(lifestyle, dict):
        return "[HYPO] 생활 조정은 교육용 후보"
    checks = lifestyle.get("weekly_self_check_ko") or []
    if isinstance(checks, list) and checks:
        preview = " · ".join(str(x) for x in checks[:3])
        return f"[HYPO] 생활·자가점검 후보: {preview}"
    msg = str(lifestyle.get("patient_message_ko") or "").strip()
    if msg:
        return f"[HYPO] 생활 조정 후보: {msg[:160]}"
    return "[HYPO] 생활 조정은 교육용 후보"


def build_turn_from_bundle(
    *,
    slug: str,
    bundle: dict[str, Any],
    pointer: dict[str, Any] | None,
    intake: dict[str, Any] | None,
    lifestyle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    soap = bundle.get("clinical_soap_v1") or {}
    subj = _soap_text(soap, "subjective")
    assess = _soap_text(soap, "assessment")
    plan = _soap_text(soap, "plan")
    raw_slots = bundle.get("patient_slots") or []
    slot_by_id: dict[str, Any] = {}
    if isinstance(raw_slots, list):
        for item in raw_slots:
            if isinstance(item, dict) and item.get("slot_id"):
                slot_by_id[str(item["slot_id"])] = item
    elif isinstance(raw_slots, dict):
        slot_by_id = raw_slots

    sasang_slot = slot_by_id.get("sasang") or {}
    sasang_body = str(sasang_slot.get("body_markdown") or "") if isinstance(sasang_slot, dict) else ""
    candidate = _resolve_sasang_candidate(intake=intake, assess=assess, sasang_slot_body=sasang_body)

    chief = subj.split("。")[0].split(".")[0][:120] if subj else ""
    intake_block = _intake_block(intake)
    sym = intake_block.get("symptoms") or (intake.get("symptoms") if isinstance(intake, dict) else None)
    if isinstance(sym, list) and sym:
        chief = chief or str(sym[0])[:120]
    elif isinstance(sym, str):
        chief = chief or sym[:120]

    l1_text, l2_text, l3_text = _build_l1_l3_layers(intake=intake, lifestyle=lifestyle, subj=subj)

    ref_token = (pointer or {}).get("ref_token") or bundle.get("provenance", {}).get("encounter_ref") or f"{slug.upper()}-REF"
    display = (pointer or {}).get("display_label") or slug
    cohort = "senior"
    reg_slug = slug
    if REGISTRY.is_file():
        reg = _load_json(REGISTRY)
        for enc in reg.get("encounters") or []:
            if enc.get("slug") == slug:
                ref_token = enc.get("ref_token") or ref_token
                display = enc.get("display_label") or display
                tags = enc.get("cohort_tags") or []
                if tags:
                    cohort = str(tags[0])
                break

    layers = {
        "executive_summary": {
            "bullets_ko": [
                f"주호소: {chief or '문진·번들 기반'}",
                f"체질 후보(비확정): {candidate}",
                "임상 변증·처방·예후는 원장 확정",
            ],
            "trust_tags": ["FACT", "HYPO"],
        },
        "L0_clinical_safety": _build_l0_layer(bundle=bundle, intake=intake),
        "L1_hemodynamics_sleep": l1_text,
        "L2_thermal_hydration": l2_text,
        "L3_cognitive_vitality": l3_text,
        "L4_career_family": "[NON_GATING] 가족·역할 맥락은 참고만",
        "L5_myeongni_hypo": {
            "hypo_ack": "[HYPO] 명리는 임상 게이팅·처방 근거가 아님",
            "pillars_ko": "만세력: 번들·명리 JSON 대조",
            "annual_note_ko": "연운은 시기 힌트만",
            "season_note_ko": "예후·임신 단정 금지",
        },
        "L6_lifestyle": _build_l6_layer(lifestyle),
    }

    provenance: dict[str, Any] = {
        "generator_id": "scripts/build_han_physician_clinical_assist_turn_v1.py",
        "generated_at_utc": _utc_now(),
    }
    if pointer and pointer.get("paths"):
        provenance.update({k: v for k, v in pointer["paths"].items() if isinstance(v, str)})

    return {
        "schema": "han_physician_clinical_assist_turn_v1",
        "version": "1.0.0",
        "rail": "Track B",
        "ref_token": ref_token,
        "slug": reg_slug,
        "cohort_id": cohort,
        "display_label": display,
        "boundary_ack": True,
        "physician_final_required": True,
        "layers": layers,
        "next_physician_actions": [
            "SOAP A/P 최종 문구 확정",
            "red flag 추가 문진",
            "복약·기저질환 확인",
            plan[:80] if plan else "환자 전달 문구(가설/사실) 분리",
        ],
        "provenance": provenance,
        "disclaimer_ko": (
            "Track B CDS 보조 초안. 진단·처방·입원·예후 단정 없음. "
            "최종 판단은 면허 한의사. Track A·실매매·MS/B2B와 합선 금지."
        ),
    }


def render_turn_md(turn: dict[str, Any]) -> str:
    layers = turn.get("layers") or {}
    lines = [
        f"# 한의사 진료 보조 turn — {turn.get('display_label', '')}",
        "",
        f"- slug: `{turn.get('slug', '')}` · ref: `{turn.get('ref_token', '')}`",
        f"- rail: {turn.get('rail', '')} · {turn.get('disclaimer_ko', '')}",
        "",
        "## 0 한눈에",
        "",
    ]
    ex = layers.get("executive_summary") or {}
    for b in ex.get("bullets_ko") or []:
        lines.append(f"- {b}")
    lines.extend(["", "## L0 [FACT]", ""])
    l0 = layers.get("L0_clinical_safety") or {}
    for r in l0.get("red_flags_ko") or []:
        lines.append(f"- {r}")
    lines.append(f"- 에스컬레이션: {l0.get('escalation_ko', '')}")
    lines.append(f"- SOAP A 발췌: {l0.get('soap_assessment_excerpt', '')}")
    for key in ("L1_hemodynamics_sleep", "L2_thermal_hydration", "L3_cognitive_vitality", "L4_career_family", "L6_lifestyle"):
        val = layers.get(key)
        if val:
            lines.extend(["", f"## {key}", "", str(val)])
    l5 = layers.get("L5_myeongni_hypo")
    if isinstance(l5, dict):
        lines.extend(["", "## L5 [HYPO]", "", l5.get("hypo_ack", ""), l5.get("pillars_ko", "")])
    lines.extend(["", "## 다음 (원장)", ""])
    for a in turn.get("next_physician_actions") or []:
        lines.append(f"- {a}")
    return "\n".join(lines) + "\n"


def _update_pointer(slug: str, json_path: Path, md_path: Path) -> None:
    ptr = _pointer_for_slug(slug)
    if not ptr.is_file():
        return
    doc = _load_json(ptr)
    paths = doc.setdefault("paths", {})
    paths["physician_assist_turn_json"] = str(json_path.relative_to(ROOT)).replace("\\", "/")
    paths["physician_assist_turn_md"] = str(md_path.relative_to(ROOT)).replace("\\", "/")
    ptr.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", help="Patient slug (loads pointer + bundle paths)")
    ap.add_argument("--bundle-json", type=Path, help="Explicit care bundle JSON")
    ap.add_argument("--out-json", type=Path, help="Output JSON path")
    ap.add_argument("--out-md", type=Path, help="Output MD path")
    ap.add_argument("--update-pointer", action="store_true")
    ap.add_argument("--validate-schema", action="store_true")
    ap.add_argument("--all-active", action="store_true", help="Build for registry active encounters with bundle")
    args = ap.parse_args()

    if args.all_active:
        if not REGISTRY.is_file():
            print("registry missing", file=sys.stderr)
            return 1
        reg = _load_json(REGISTRY)
        rc = 0
        for enc in reg.get("encounters") or []:
            if enc.get("status") != "active":
                continue
            slug = str(enc.get("slug") or "")
            if not slug or slug in ("commander", "family_daughter"):
                continue
            sub = argparse.Namespace(
                slug=slug,
                bundle_json=None,
                out_json=None,
                out_md=None,
                update_pointer=True,
                validate_schema=args.validate_schema,
                all_active=False,
            )
            try:
                rc = max(rc, int(_run_one(sub)))
            except SystemExit as e:
                print(f"skip {slug}: {e}", file=sys.stderr)
                rc = max(rc, 1)
        return rc

    return _run_one(args)


def _run_one(args: argparse.Namespace) -> int:
    slug = (args.slug or "").strip()
    if not slug and not args.bundle_json:
        print("provide --slug or --bundle-json", file=sys.stderr)
        return 1

    pointer = _load_json(_pointer_for_slug(slug)) if slug else None
    bundle_path = args.bundle_json
    if bundle_path is None and pointer:
        bp = (pointer.get("paths") or {}).get("bundle_json")
        if bp:
            bundle_path = ROOT / bp
    if bundle_path is None or not bundle_path.is_file():
        print(f"bundle not found for {slug}", file=sys.stderr)
        return 1

    bundle = _load_json(bundle_path)
    intake_path = None
    if pointer:
        ip = (pointer.get("paths") or {}).get("intake")
        if ip:
            intake_path = ROOT / ip
    intake = _load_json(intake_path) if intake_path and intake_path.is_file() else None
    lifestyle_path = None
    if pointer:
        lp = (pointer.get("paths") or {}).get("lifestyle_v2")
        if lp:
            lifestyle_path = ROOT / lp
    lifestyle = _load_json(lifestyle_path) if lifestyle_path and lifestyle_path.is_file() else None

    turn = build_turn_from_bundle(
        slug=slug or "patient",
        bundle=bundle,
        pointer=pointer,
        intake=intake,
        lifestyle=lifestyle,
    )
    if args.validate_schema:
        _validate_turn(turn)

    out_json = args.out_json or (ROOT / "reports" / f"{slug}_han_physician_assist_turn_v1.json")
    out_md = args.out_md or (ROOT / "reports" / f"{slug}_han_physician_assist_turn_v1.md")
    latest_json = ROOT / "reports" / f"{slug}_han_physician_assist_turn_v1.latest.json"
    latest_md = ROOT / "reports" / f"{slug}_han_physician_assist_turn_v1.latest.md"

    for p in (out_json, latest_json):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(turn, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = render_turn_md(turn)
    for p in (out_md, latest_md):
        p.write_text(md, encoding="utf-8")

    if args.update_pointer and slug:
        _update_pointer(slug, out_json, out_md)

    print(json.dumps({"ok": True, "slug": slug, "out_json": str(out_json), "out_md": str(out_md)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
