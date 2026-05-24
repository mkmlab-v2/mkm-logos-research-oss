#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline validate showroom trust slice + HTML (no HTTP)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SLICE = (
    ROOT
    / "projects"
    / "bitcoin-trading"
    / "ops"
    / "windows-rehearsal"
    / "jemaai-cloud-mvp"
    / "showroom_trust_visualization_slice_v0.json"
)
DEFAULT_HTML = (
    ROOT
    / "projects"
    / "bitcoin-trading"
    / "ops"
    / "windows-rehearsal"
    / "jemaai-cloud-mvp"
    / "public_showroom_trust_visualization_v0.html"
)


def validate(slice_path: Path, html_path: Path) -> list[str]:
    errors: list[str] = []
    if not slice_path.is_file():
        errors.append(f"missing slice: {slice_path}")
        return errors
    doc = json.loads(slice_path.read_text(encoding="utf-8-sig"))
    if doc.get("schema") != "showroom_trust_visualization_slice_v0":
        errors.append("schema mismatch")
    if doc.get("version") != "0.1.3":
        errors.append(f"expected version 0.1.3 got {doc.get('version')}")
    pit = doc.get("patient_intake_b_track_v0") or {}
    if not isinstance(pit, dict):
        errors.append("patient_intake_b_track_v0 missing")
    elif pit.get("auto_prescription_forbidden") is not True:
        errors.append("patient_intake: auto_prescription_forbidden must be true")
    tv = doc.get("trust_visualization_v0") or {}
    if not tv.get("final_action"):
        errors.append("trust_visualization_v0.final_action missing")

    if html_path.is_file():
        html = html_path.read_text(encoding="utf-8", errors="replace")
        for needle in (
            "showroom_trust_visualization_slice_v0.json",
            "patient_intake_b_track_v0",
            "Patient intake fusion",
        ):
            if needle not in html:
                errors.append(f"html missing: {needle}")
    else:
        errors.append(f"missing html: {html_path}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice", type=Path, default=DEFAULT_SLICE)
    ap.add_argument("--html", type=Path, default=DEFAULT_HTML)
    args = ap.parse_args()
    errs = validate(args.slice, args.html)
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "slice": str(args.slice), "html": str(args.html)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
