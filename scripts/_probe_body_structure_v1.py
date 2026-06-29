#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / (
    "reports/kstartup_startup_package_ai_attachments/"
    "(도약) [별첨 1] 2026년 창업도약패키지(AI 인재 실증형) 사업계획서 양식.docx"
)


def para_xml_texts(p) -> list[str]:
    return [t for t in re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p._element.xml) if t.strip()]


def has_blue(p) -> bool:
    return "0000FF" in p._element.xml or "0070C0" in p._element.xml


doc = Document(str(TEMPLATE))
for i, p in enumerate(doc.paragraphs):
    t = (p.text or "").strip()
    x = para_xml_texts(p)
    if t.startswith("□") or has_blue(p) or x:
        if t.startswith("□") or has_blue(p):
            print(f"P{i:03d} text={t[:60]!r} xml={x[:4]}")
