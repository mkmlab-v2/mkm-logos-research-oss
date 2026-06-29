#!/usr/bin/env python3
"""Ingest user-pasted Cheonyucho p.344 excerpt (사상체질과 임상편람 or other [PARTIAL])."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = ROOT / "data/corpus/ijeoma/originals/cheonyucho_partial"
MANIFEST = ROOT / "data/corpus/ijeoma/_inventory/cheonyucho_p344_partial_ingest_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True, help="Markdown paste file")
    ap.add_argument("--source", default="sasang_clinical_pyeonram_p344", help="provenance tag")
    args = ap.parse_args()

    if not args.input.is_file():
        print(json.dumps({"ok": False, "error": f"missing {args.input}"}))
        return 1

    text = args.input.read_text(encoding="utf-8")
    if len(text.strip()) < 80:
        print(json.dumps({"ok": False, "error": "paste too short (<80 chars)"}))
        return 1

    has_hanja = "闡幽" in text or "천유" in text
    if not has_hanja:
        print(json.dumps({"ok": False, "error": "no 闡幽/천유 in paste"}))
        return 1

    DEFAULT_OUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = DEFAULT_OUT_DIR / args.input.name
    if args.input.resolve() != dest.resolve():
        dest.write_text(text, encoding="utf-8")

    doc = {
        "schema": "cheonyucho_p344_partial_ingest_v1",
        "updated_at_utc": _utc(),
        "disk_path": str(dest.relative_to(ROOT)).replace("\\", "/"),
        "chars": len(text),
        "layer": "PARTIAL_INGEST",
        "send_gate": "HOLD",
        "hanja_ssot": "闡幽抄",
        "hanja_canon_status": "partial_excerpt_only",
        "glyph_in_paste": {"闡幽抄": "闡幽抄" in text, "闡幽草": "闡幽草" in text},
        "physical_verified": False,
        "provenance": args.source,
        "not_canon": True,
        "reproduce": f"py scripts/ingest_cheonyucho_p344_user_paste_v1.py --input {dest.relative_to(ROOT)}",
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "chars": len(text), "manifest": str(MANIFEST)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
