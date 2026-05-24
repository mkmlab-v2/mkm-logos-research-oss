#!/usr/bin/env python3
"""Emit MCP-ready delta manifest for 06 smartfarm notebook (stdout JSON).

Does not call MCP; agent or operator uses titles + pack paths with notebooklm add_source.
SSOT pack: reports/notebooklm_smartfarm_geumsan_sync_pack_v1/index.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "reports" / "notebooklm_smartfarm_geumsan_sync_pack_v1"
INDEX = PACK / "index.json"
NOTEBOOK_MCP_ID = "06-2026q2"
MAX_BYTES = 120_000  # NL per-source practical limit for text paste


def main() -> int:
    if not INDEX.is_file():
        print(json.dumps({"error": "missing index", "path": str(INDEX)}), file=sys.stderr)
        return 1
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    deltas = idx.get("delta_upload_recommended") or []
    items = []
    for name in deltas:
        path = PACK / name
        if not path.is_file():
            items.append({"file": name, "status": "missing"})
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        items.append(
            {
                "file": name,
                "title": name.replace(".md", "").replace(".json", "")[:80],
                "bytes": path.stat().st_size,
                "status": "ok" if len(raw.encode("utf-8")) <= MAX_BYTES else "too_large",
                "notebook_id": NOTEBOOK_MCP_ID,
            }
        )
    out = {
        "schema": "notebooklm_smartfarm_delta_push_manifest_v1",
        "notebook_id": NOTEBOOK_MCP_ID,
        "notebook_url": idx.get("notebook_url"),
        "delta_count": len(items),
        "items": items,
        "nl_url_sources": idx.get("nl_url_sources") or [],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
