#!/usr/bin/env python3
"""Push clinician physician_gold sync pack to NotebookLM via stdio MCP."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "reports" / "notebooklm_clinician_sync_pack_v1"
URL_FILE = ROOT / "reports" / "notebooklm_clinician_notebook_url_v1.txt"
NOTEBOOKLM_JS = Path(
    os.environ.get(
        "NOTEBOOKLM_MCP_INDEX",
        r"C:/Users/PRO/AppData/Roaming/npm/node_modules/notebooklm-mcp/dist/index.js",
    )
)


def _server_params() -> StdioServerParameters:
    env = {
        "NOTEBOOKLM_PROFILE": os.environ.get("NOTEBOOKLM_PROFILE", "full"),
        "HEADLESS": os.environ.get("HEADLESS", "false"),
        "STEALTH_ENABLED": os.environ.get("STEALTH_ENABLED", "false"),
    }
    return StdioServerParameters(command="node", args=[str(NOTEBOOKLM_JS)], env=env)


def _parse_result(tool_result) -> dict:
    row = {"success": False, "sourceCountAfter": None, "error": None}
    if tool_result.isError:
        row["error"] = str(tool_result.content)
        return row
    for block in tool_result.content or []:
        text = getattr(block, "text", None)
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        inner = payload.get("data", payload)
        if isinstance(inner, dict) and "result" in inner:
            inner = inner["result"]
        if isinstance(inner, dict):
            row["success"] = bool(inner.get("success", payload.get("success")))
            row["sourceCountAfter"] = inner.get("sourceCountAfter")
            row["error"] = inner.get("error")
            return row
    row["error"] = "unparsed"
    return row


def _resolve_notebook_url(cli_url: str | None) -> str:
    if cli_url:
        return cli_url.strip()
    if URL_FILE.is_file():
        text = URL_FILE.read_text(encoding="utf-8").strip()
        if text and not text.startswith("("):
            return text
    index_path = PACK / "index.json"
    if index_path.is_file():
        idx = json.loads(index_path.read_text(encoding="utf-8"))
        url = (idx.get("notebook_url") or "").strip()
        if url and not url.startswith("("):
            return url
    raise SystemExit(
        "notebook URL missing: create NL notebook, then write share URL to "
        f"{URL_FILE} or pass --notebook-url"
    )


def _notebook_uuid(url: str) -> str:
    m = re.search(
        r"notebooklm\.google\.com/notebook/([0-9a-f-]{36})",
        url,
        re.I,
    )
    if not m:
        path = urlparse(url).path.rstrip("/")
        tail = path.split("/")[-1] if path else ""
        if re.fullmatch(r"[0-9a-f-]{36}", tail, re.I):
            return tail
        raise SystemExit(f"cannot parse notebook UUID from URL: {url}")
    return m.group(1)


async def push_pack(
    notebook_url: str, skip_titles: set[str], only_titles: set[str] | None = None
) -> list[dict]:
    index = json.loads((PACK / "index.json").read_text(encoding="utf-8"))
    files = [f for f in index.get("files", []) if isinstance(f, str) and f not in skip_titles]
    if only_titles:
        files = [f for f in files if f in only_titles]
    rows: list[dict] = []
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            session_id = ""
            for name in files:
                path = PACK / name
                if not path.is_file():
                    rows.append({"title": name, "success": False, "error": "missing"})
                    continue
                content = path.read_text(encoding="utf-8", errors="replace")
                args = {
                    "type": "text",
                    "title": name,
                    "content": content,
                    "notebook_url": notebook_url,
                }
                if session_id:
                    args["session_id"] = session_id
                row = {"title": name, "success": False}
                try:
                    result = await session.call_tool("add_source", args)
                    parsed = _parse_result(result)
                    row.update(parsed)
                except Exception as exc:  # noqa: BLE001
                    row["error"] = str(exc)
                rows.append(row)
                print(json.dumps(row, ensure_ascii=False), flush=True)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--notebook-url", default="", help="override URL file / index.json")
    ap.add_argument("--skip", default="", help="comma pack filenames already pushed")
    ap.add_argument("--only", default="", help="comma pack filenames to push only")
    ap.add_argument("--out", default=str(ROOT / "reports/notebooklm_clinician_push_latest.json"))
    args = ap.parse_args()

    if not PACK.is_dir() or not (PACK / "index.json").is_file():
        raise SystemExit(f"pack missing — run: py scripts/build_notebooklm_clinician_sync_pack_v1.py")

    notebook_url = _resolve_notebook_url(args.notebook_url or None)
    skip = {x.strip() for x in args.skip.split(",") if x.strip()}
    only = {x.strip() for x in args.only.split(",") if x.strip()} or None
    rows = asyncio.run(push_pack(notebook_url, skip, only))
    out_doc = {
        "schema": "notebooklm_clinician_push_latest",
        "notebook_url": notebook_url,
        "notebook_id": _notebook_uuid(notebook_url),
        "rows": rows,
    }
    Path(args.out).write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if all(r.get("success") for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
