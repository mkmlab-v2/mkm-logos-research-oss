#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render `patient_care_bundle_v1` as a single Markdown document (patient-facing order)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

PATIENT_FACING_TRACK_B_BARRIER_KO = (
    "> **Track B · 학술 가설:** 본 문서에 포함된 알고리즘·수치·명리 표기는 연구·교육 목적의 휴리스틱일 수 있으며, "
    "임상 진단·처방·응급 처치의 근거로 사용될 수 없습니다. "
    "대외 노출·카피는 `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` 정합을 따릅니다.\n\n"
)


def _md_escape_title(s: str) -> str:
    return s.replace("\n", " ").strip()


def _resolve_encounter_sequence(bundle: dict, encounter_sequence: dict | None) -> dict | None:
    if encounter_sequence is not None:
        return encounter_sequence
    try:
        import importlib.util

        router_path = Path(__file__).resolve().parent / "l0_red_flag_router_v1.py"
        spec = importlib.util.spec_from_file_location("l0_red_flag_router_v1", router_path)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.load_sequence_for_bundle(bundle)
    except Exception:
        return None


def render_bundle_markdown(bundle: dict, *, encounter_sequence: dict | None = None) -> str:
    lines: list[str] = []
    bid = bundle.get("bundle_id", "")
    gen = bundle.get("generated_at_utc", "")
    lines.append(
        f"# 환자 안내 번들\n\n- **bundle_id:** `{_md_escape_title(str(bid))}`\n"
        f"- **generated_at_utc:** `{_md_escape_title(str(gen))}`\n"
    )
    lines.append(PATIENT_FACING_TRACK_B_BARRIER_KO)
    seq = _resolve_encounter_sequence(bundle, encounter_sequence)
    if seq is not None:
        try:
            import importlib.util

            router_path = Path(__file__).resolve().parent / "l0_red_flag_router_v1.py"
            spec = importlib.util.spec_from_file_location("l0_red_flag_router_v1", router_path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                l0_state = mod.collect_l0_state_from_sequence(seq)
                l0_block = mod.format_patient_markdown_block(l0_state)
                if l0_block:
                    lines.append(l0_block)
        except Exception:
            pass
    prov = bundle.get("provenance") or {}
    if prov:
        lines.append("## 출처\n\n")
        for k in sorted(prov.keys()):
            lines.append(f"- **{k}:** `{prov[k]}`\n")
        lines.append("\n")
    lines.append("---\n\n## SOAP (임상 기록 요약)\n\n")
    soap = bundle.get("clinical_soap_v1") or {}
    for label, key in (("S", "subjective"), ("O", "objective"), ("A", "assessment"), ("P", "plan")):
        t = (soap.get(key) or {}).get("text") or ""
        lines.append(f"### {label}. {key}\n\n{t}\n\n")
    lines.append("---\n\n## 환자 슬롯 (표시 순서)\n\n")
    slots = sorted(bundle.get("patient_slots") or [], key=lambda x: int(x.get("slot_order", 0)))
    for s in slots:
        inc = s.get("included", True)
        if not inc and s.get("slot_id") == "logos_opt":
            lines.append(f"### (생략) {s.get('title', '')}\n\n_Logos 슬롯은 포함되지 않았습니다._\n\n")
            continue
        if not inc:
            lines.append(f"### (생략) {s.get('title', '')}\n\n")
            continue
        title = s.get("title") or s.get("slot_id")
        tier = s.get("trust_tier", "")
        lines.append(f"### {_md_escape_title(str(title))}\n\n_`{tier}`_\n\n")
        lines.append((s.get("body_markdown") or "").strip() + "\n\n")
    lines.append("---\n\n## 면책\n\n")
    for d in bundle.get("disclaimers") or []:
        lines.append(f"- {d}\n")
    return "".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Render patient_care_bundle_v1 as Markdown")
    ap.add_argument("--bundle-json", type=Path, required=True)
    ap.add_argument("--encounter-sequence-json", type=Path, default=None, help="Optional encounter_sequence_v1 JSON")
    ap.add_argument("--out-md", type=Path, help="Write Markdown; default stdout")
    args = ap.parse_args()
    bundle = json.loads(args.bundle_json.read_text(encoding="utf-8-sig"))
    seq = None
    if args.encounter_sequence_json and args.encounter_sequence_json.is_file():
        seq = json.loads(args.encounter_sequence_json.read_text(encoding="utf-8-sig"))
    text = render_bundle_markdown(bundle, encounter_sequence=seq)
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
