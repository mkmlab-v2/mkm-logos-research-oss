#!/usr/bin/env python3
"""Sync NotebookLM MD wrapper from v23_latest.json SSOT."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
src = ROOT / "reports/research/logos_shadow_v1/logos_kospi_shadow_evaluation_bundle_v23_latest.json"
out = ROOT / "docs/final/artifacts/logos_kospi_shadow_evaluation_bundle_v23_notebooklm.md"

data = json.loads(src.read_text(encoding="utf-8"))
body = json.dumps(data, ensure_ascii=False, indent=2)
text = (
    "# logos_kospi_shadow_evaluation_bundle_v23 (JSON mirror for NotebookLM)\n\n"
    "**SSOT**: `reports/research/logos_shadow_v1/logos_kospi_shadow_evaluation_bundle_v23_latest.json` "
    "— 아래 fenced JSON은 동일 내용을 NotebookLM 파일 소스용으로 복제한 것이다.\n\n"
    "```json\n" + body + "\n```\n"
)
out.write_text(text, encoding="utf-8")
print(f"wrote {out} ({len(text)} chars)")
