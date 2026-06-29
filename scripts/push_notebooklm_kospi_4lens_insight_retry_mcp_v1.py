#!/usr/bin/env python3
"""Retry failed KOSPI 4-lens NL uploads via stdio MCP add_source."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "reports" / "notebooklm_kospi_4lens_insight_sync_pack_v1"
URL = (ROOT / "reports/notebooklm_kospi_4lens_insight_notebook_url_v1.txt").read_text(encoding="utf-8").strip()
NOTEBOOKLM_JS = Path(
    os.environ.get(
        "NOTEBOOKLM_MCP_INDEX",
        r"C:/Users/PRO/AppData/Roaming/npm/node_modules/notebooklm-mcp/dist/index.js",
    )
)

RETRIES = [
    ("premium_multilens_kospi_4lens_full_v2", PACK / "premium_btrack_multilens_report_v1.md"),
]


async def main() -> int:
    params = StdioServerParameters(
        command="node",
        args=[str(NOTEBOOKLM_JS)],
        env={
            "NOTEBOOKLM_PROFILE": os.environ.get("NOTEBOOKLM_PROFILE", "full"),
            "HEADLESS": os.environ.get("HEADLESS", "false"),
        },
    )
    rows: list[dict] = []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for title, path in RETRIES:
                content = path.read_text(encoding="utf-8")
                result = await session.call_tool(
                    "add_source",
                    {
                        "type": "text",
                        "content": content,
                        "title": title,
                        "notebook_url": URL,
                    },
                )
                ok = not result.isError
                rows.append({"title": title, "ok": ok, "bytes": len(content.encode("utf-8"))})
    out = ROOT / "reports/notebooklm_kospi_4lens_insight_push_mcp_retry_latest.json"
    out.write_text(json.dumps({"rows": rows, "notebook_url": URL}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": sum(1 for r in rows if r["ok"]), "fail": sum(1 for r in rows if not r["ok"]), "out": str(out)}))
    return 0 if all(r["ok"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
