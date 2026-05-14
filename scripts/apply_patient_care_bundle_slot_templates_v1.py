#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply slot Markdown templates to a `patient_care_bundle_v1` JSON (title + body_markdown)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATES = ROOT / "docs" / "final" / "artifacts" / "patient_care_bundle_slot_templates_ko_v1.json"


def _substitute(template: str, mapping: dict[str, str]) -> str:
    out = template
    for k, v in mapping.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _subst_from_myeongni_report(report: dict[str, Any], report_rel_path: str) -> dict[str, str]:
    pillars = report.get("pillars") or {}
    dm = (report.get("day_master") or {}).get("stem_hangul") or ""
    return {
        "DAY_MASTER_STEM": dm,
        "YEAR_PILLAR": str(pillars.get("year", "")),
        "MONTH_PILLAR": str(pillars.get("month", "")),
        "DAY_PILLAR": str(pillars.get("day", "")),
        "HOUR_PILLAR": str(pillars.get("hour", "")),
        "MYEONGNI_REPORT_PATH": report_rel_path,
    }


def _build_subst(args: argparse.Namespace) -> dict[str, str]:
    if args.subst_json:
        raw = _load_json(args.subst_json)
        return {str(k): str(v) for k, v in raw.items()}
    if args.myeongni_json:
        rep = _load_json(args.myeongni_json)
        rel = args.myeongni_report_rel or str(args.myeongni_json)
        return _subst_from_myeongni_report(rep, rel)
    return {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply patient_care_bundle slot templates (KO v1)")
    ap.add_argument("--bundle-in", type=Path, required=True)
    ap.add_argument("--bundle-out", type=Path, required=True)
    ap.add_argument("--templates-json", type=Path, default=DEFAULT_TEMPLATES)
    ap.add_argument("--subst-json", type=Path, help="Flat string map for {{PLACEHOLDER}}")
    ap.add_argument("--myeongni-json", type=Path, help="Build subst from myeongni_full_report_v1")
    ap.add_argument(
        "--myeongni-report-rel",
        type=str,
        default="",
        help="Display path for MYEONGNI_REPORT_PATH when using --myeongni-json",
    )
    ap.add_argument(
        "--fill-empty-only",
        action="store_true",
        help="Only replace body/title when body_markdown is empty or whitespace",
    )
    args = ap.parse_args()

    bundle = _load_json(args.bundle_in)
    tmpl_doc = _load_json(args.templates_json)
    slots_tmpl = tmpl_doc.get("slots") or {}
    mapping = _build_subst(args)

    for slot in bundle.get("patient_slots") or []:
        sid = slot.get("slot_id")
        if not isinstance(sid, str) or sid not in slots_tmpl:
            continue
        tdef = slots_tmpl[sid]
        body_t = tdef.get("body_markdown_template") or ""
        title_d = tdef.get("title_default")
        body_cur = slot.get("body_markdown") or ""
        if args.fill_empty_only and body_cur.strip():
            continue
        slot["body_markdown"] = _substitute(body_t, mapping)
        if title_d:
            slot["title"] = title_d

    args.bundle_out.parent.mkdir(parents=True, exist_ok=True)
    args.bundle_out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "bundle_out": str(args.bundle_out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
