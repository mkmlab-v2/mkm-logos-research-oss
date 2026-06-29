#!/usr/bin/env python3
"""Extract QuBICS PDF facts for ingest/MQTT spec validation."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pypdf

ROOT = Path(__file__).resolve().parents[1] / "reports" / "smartfarm_vendor_replies"
OUT = Path(__file__).resolve().parents[1] / "reports" / "qubics_pdf_extract_latest.json"

KEYWORDS = [
    "relay",
    "relay_ctl",
    "제어",
    "SUB Topic",
    "PUB Topic",
    "POST /",
    "soil_mtr",
    "th_mtr",
    "cid",
    "result",
    "ok",
    "ch",
    "val",
    "type",
]


def extract_pdf(path: Path) -> str:
    reader = pypdf.PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def snippets(text: str, keywords: list[str], window: int = 120) -> dict[str, str]:
    out: dict[str, str] = {}
    for kw in keywords:
        for match in re.finditer(re.escape(kw), text, flags=re.IGNORECASE):
            start = max(0, match.start() - window)
            end = min(len(text), match.end() + window)
            snip = re.sub(r"\s+", " ", text[start:end]).strip()
            out.setdefault(kw, snip)
            break
    return out


def json_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    for m in re.finditer(r"\{[^{}]{10,500}\}", text, flags=re.DOTALL):
        blocks.append(re.sub(r"\s+", " ", m.group(0)))
    return blocks[:20]


def main() -> int:
    report: dict[str, object] = {"pdfs": {}}
    for pdf in sorted(ROOT.glob("*.pdf")):
        if "QuBICS" not in pdf.name and "260520" not in pdf.name and "260522" not in pdf.name:
            continue
        text = extract_pdf(pdf)
        report["pdfs"][pdf.name] = {
            "chars": len(text),
            "snippets": snippets(text, KEYWORDS),
            "json_like_blocks": json_blocks(text),
            "full_text_preview": text[:4000],
        }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    for name, data in report["pdfs"].items():
        print(f"\n=== {name} ===")
        for k, v in data["snippets"].items():  # type: ignore[index]
            print(f"  {k}: {v[:200]}")
        blocks = data.get("json_like_blocks") or []
        if blocks:
            print("  json_blocks:")
            for b in blocks[:5]:
                print(f"    {b[:300]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
