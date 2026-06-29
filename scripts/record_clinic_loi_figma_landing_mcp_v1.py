#!/usr/bin/env python3
"""Record Figma MCP clinic LOI landing frame apply result."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/clinic_loi_figma_landing_mcp_v1_latest.json"
REPORT = ROOT / "reports/clinic_loi_figma_landing_mcp_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    raw = args.json.strip() or sys.stdin.read().strip()
    if not raw:
        print(json.dumps({"ok": False, "error": "missing_json"}), file=sys.stderr)
        return 2
    payload = json.loads(raw)
    ok = bool(payload.get("ok")) and bool(payload.get("frameId"))
    doc = {
        "schema": "clinic_loi_figma_landing_mcp_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "lane_status": "frozen_deferred",
        "file_key": "8Ey3MEkXhH8EliARQ9OydE",
        "landing_ok": ok,
        "mcp_result": payload,
        "html_preview": "reports/clinic_km_mmp_loi_preview_v1.html",
        "reproduce": "Figma MCP use_figma landing frame build",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "frameId": payload.get("frameId")}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
