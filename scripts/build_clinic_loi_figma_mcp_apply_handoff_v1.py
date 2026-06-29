#!/usr/bin/env python3
"""Handoff payload for Figma use_figma auto-apply (Clinic LOI tokens)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "projects/design/clinic_loi_figma_plugin/use_figma_apply.js"
OUT = ROOT / "docs/final/artifacts/clinic_loi_figma_mcp_apply_handoff_v1_latest.json"
FILE_KEY = "8Ey3MEkXhH8EliARQ9OydE"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    code = PLUGIN.read_text(encoding="utf-8")

    doc = {
        "schema": "clinic_loi_figma_mcp_apply_handoff_v1",
        "generated_at_utc": _utc(),
        "file_key": FILE_KEY,
        "figma_url": f"https://www.figma.com/design/{FILE_KEY}/mkm-20260624",
        "mcp_tool": "use_figma",
        "mcp_servers_try": ["figma", "figma-desktop", "plugin-figma-figma"],
        "skill_names": "resource:figma-use",
        "description": "Create Clinic LOI variables, color styles, reference frame",
        "use_figma_code": code,
        "setup_ko": [
            "Cursor 채팅에 /add-plugin figma 실행 후 Figma OAuth Allow",
            "또는 Figma 데스크톱: Preferences -> Enable Local MCP Server (3845)",
            "Cursor Settings -> MCP에서 figma 초록 확인 후 채팅에 '다시 자동적용' 입력",
        ],
        "fallback_ps1": "scripts/Run-ClinicLoiFigmaPluginImport_v1.ps1",
        "send_gate": "HOLD",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(OUT), "file_key": FILE_KEY}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
