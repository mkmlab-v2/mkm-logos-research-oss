#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render `patient_care_bundle_v1` as a single Markdown document (patient-facing order)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _md_escape_title(s: str) -> str:
    return s.replace("\n", " ").strip()


def render_bundle_markdown(bundle: dict) -> str:
    lines: list[str] = []
    bid = bundle.get("bundle_id", "")
    gen = bundle.get("generated_at_utc", "")
    lines.append(
        f"# 환자 안내 번들\n\n- **bundle_id:** `{_md_escape_title(str(bid))}`\n"
        f"- **generated_at_utc:** `{_md_escape_title(str(gen))}`\n"
    )
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
    ap.add_argument("--out-md", type=Path, help="Write Markdown; default stdout")
    args = ap.parse_args()
    bundle = json.loads(args.bundle_json.read_text(encoding="utf-8-sig"))
    text = render_bundle_markdown(bundle)
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
