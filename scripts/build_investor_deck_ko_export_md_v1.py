#!/usr/bin/env python3
"""Build KO investor deck Markdown export from CSV (internal · print/PDF paste)."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "docs/research/MKM_UNIVERSAL_ROOT_INVESTOR_DECK_SLIDES_KO_V1.csv"
DEFAULT_OUT = ROOT / "docs/research/MKM_UNIVERSAL_ROOT_INVESTOR_DECK_EXPORT_KO_V1.md"
DEFAULT_REPORT = ROOT / "reports/investor_deck_ko_export_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_md(rows: list[dict[str, str]]) -> str:
    lines = [
        "# MKM Universal Root — Investor Deck Export (KO v1.1)",
        "",
        "**Status:** `[HYPO]` · `research_only` · internal print/PDF paste",
        "**Binding:** `MKM_UNIVERSAL_ROOT_INVESTOR_FACT_LOCK_CORRECTION_APPENDIX_EN_V1.md`",
        "**Note:** Slide 17 = internal checklist — remove before external PDF",
        "",
        "---",
        "",
    ]
    for row in rows:
        no = row.get("slide_no", "").strip()
        title = row.get("title", "").strip()
        body = row.get("body", "").strip()
        notes = row.get("speaker_notes", "").strip()
        tag = row.get("tag", "").strip()
        lines.append(f"## Slide {no} — {title}")
        lines.append("")
        if tag:
            lines.append(f"**Tag:** `{tag}`")
            lines.append("")
        if body:
            lines.append(body)
            lines.append("")
        if notes:
            lines.append(f"> **Speaker notes:** {notes}")
            lines.append("")
        lines.append("---")
        lines.append("")
    lines.append(f"*Generated {_utc()} · from CSV v1.1 · `send_gate: HOLD`*")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    csv_path = args.csv.resolve()
    if not csv_path.is_file():
        raise SystemExit(f"csv missing: {csv_path}")

    with csv_path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    md = build_md(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md, encoding="utf-8")

    try:
        out_md_rel = str(args.out.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        out_md_rel = str(args.out.resolve())

    doc = {
        "schema": "investor_deck_ko_export_v1",
        "ok": True,
        "generated_at_utc": _utc(),
        "slide_count": len(rows),
        "csv": str(csv_path.relative_to(ROOT)).replace("\\", "/"),
        "out_md": out_md_rel,
        "reproduce": "py scripts/build_investor_deck_ko_export_md_v1.py",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "slide_count": len(rows), "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
