#!/usr/bin/env python3
"""Push universal root research pack to NotebookLM 14-universal-lexicon-dr via MCP add_source."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "reports" / "notebooklm_universal_root_research_pack_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/notebooklm_universal_root_research_pack_push_v1_latest.json"
NOTEBOOK_MCP_ID = "14-universal-lexicon-dr"

NOTEBOOKLM_JS = Path(
    os.environ.get(
        "NOTEBOOKLM_MCP_INDEX",
        r"C:/Users/PRO/AppData/Roaming/npm/node_modules/notebooklm-mcp/dist/index.js",
    )
)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _server_params() -> StdioServerParameters:
    env = {
        "NOTEBOOKLM_PROFILE": os.environ.get("NOTEBOOKLM_PROFILE", "full"),
        "HEADLESS": os.environ.get("HEADLESS", "false"),
        "STEALTH_ENABLED": os.environ.get("STEALTH_ENABLED", "false"),
    }
    return StdioServerParameters(command="node", args=[str(NOTEBOOKLM_JS)], env=env)


def _parse_result(tool_result) -> dict:
    if tool_result.isError:
        return {"success": False, "error": str(tool_result.content)}
    for block in tool_result.content or []:
        text = getattr(block, "text", None) or ""
        if not text.strip().startswith("{"):
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        inner = payload.get("data", payload)
        if isinstance(inner, dict) and "result" in inner:
            inner = inner["result"]
        if isinstance(inner, dict):
            return {
                "success": bool(inner.get("success", payload.get("success"))),
                "error": inner.get("error"),
                "sourceCountBefore": inner.get("sourceCountBefore"),
                "sourceCountAfter": inner.get("sourceCountAfter"),
            }
    return {"success": False, "error": "unparsed"}


def _cursor_mcp_already_running() -> bool:
    try:
        import subprocess

        out = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_Process -Filter \"name='node.exe'\" | "
                "Where-Object { $_.CommandLine -match 'notebooklm-mcp' }).Count",
            ],
            text=True,
            timeout=15,
        )
        return int(out.strip() or "0") >= 2
    except Exception:
        return False


async def _push(*, manifest_path: Path, dry_run: bool, sleep_s: float) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    pack_dir = ROOT / str(manifest.get("pack_dir") or "reports/notebooklm_universal_root_research_pack_v1")
    rows: list[dict] = []

    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            health_raw = await session.call_tool("get_health", {})
            auth = False
            for block in health_raw.content or []:
                t = getattr(block, "text", "") or ""
                if t.strip().startswith("{"):
                    h = json.loads(t)
                    d = h.get("data", h)
                    auth = d.get("authenticated") is True
            if not auth and not dry_run:
                return {"ok": False, "error": "authenticated_false", "rows": rows}

            sel = _parse_result(
                await session.call_tool("select_notebook", {"id": NOTEBOOK_MCP_ID})
            )
            if not sel.get("success") and not dry_run:
                return {"ok": False, "error": "select_notebook_failed", "select": sel, "rows": rows}

            for entry in manifest.get("entries") or []:
                if not entry.get("copied"):
                    continue
                pack_name = str(entry.get("pack_name") or "")
                src_path = pack_dir / pack_name
                if not src_path.is_file():
                    rows.append({"pack_name": pack_name, "success": False, "error": "missing_pack_file"})
                    continue
                body = src_path.read_text(encoding="utf-8", errors="replace")
                title = f"MKM_UR_{pack_name[:100]}"
                row = {
                    "pack_name": pack_name,
                    "source_path": entry.get("source_path"),
                    "title": title,
                    "chars": len(body),
                    "success": False,
                    "error": None,
                }
                if dry_run:
                    row["success"] = True
                    row["dry_run"] = True
                    rows.append(row)
                    continue
                try:
                    result = await session.call_tool(
                        "add_source",
                        {
                            "type": "text",
                            "content": body,
                            "title": title,
                            "notebook_id": NOTEBOOK_MCP_ID,
                        },
                    )
                    parsed = _parse_result(result)
                    row.update(parsed)
                except Exception as exc:  # noqa: BLE001
                    row["error"] = str(exc)
                rows.append(row)
                if sleep_s > 0:
                    time.sleep(sleep_s)

    ok = sum(1 for r in rows if r.get("success"))
    fail = sum(1 for r in rows if not r.get("success"))
    return {
        "schema": "notebooklm_universal_root_research_pack_push_v1",
        "generated_at_utc": _utc(),
        "notebook_mcp_id": NOTEBOOK_MCP_ID,
        "manifest": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
        "dry_run": dry_run,
        "authenticated": auth if not dry_run else None,
        "ok_count": ok,
        "fail_count": fail,
        "all_ok": fail == 0 and ok > 0,
        "rows": rows,
        "reproduce": "py scripts/push_notebooklm_universal_root_research_pack_mcp_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sleep", type=float, default=3.0)
    ap.add_argument(
        "--force-second-mcp",
        action="store_true",
        help="Allow stdio MCP while another notebooklm-mcp may be running",
    )
    args = ap.parse_args()

    if not args.manifest.is_file():
        print(json.dumps({"ok": False, "error": f"missing manifest: {args.manifest}"}), file=sys.stderr)
        return 2

    if not args.dry_run and not args.force_second_mcp and _cursor_mcp_already_running():
        print(
            json.dumps(
                {
                    "error": "notebooklm_mcp_already_running",
                    "hint": "Use Cursor-injected MCP add_source on 14-universal-lexicon-dr, "
                    "then record via scripts/record_notebooklm_universal_root_cursor_push_v1.py "
                    "and rerun phase11o with --cursor-mcp-results",
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 3

    doc = asyncio.run(_push(manifest_path=args.manifest, dry_run=args.dry_run, sleep_s=args.sleep))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(args.out),
                "all_ok": doc.get("all_ok"),
                "ok_count": doc.get("ok_count"),
                "fail_count": doc.get("fail_count"),
            },
            ensure_ascii=False,
        )
    )
    if doc.get("error"):
        return 2
    return 0 if doc.get("all_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
