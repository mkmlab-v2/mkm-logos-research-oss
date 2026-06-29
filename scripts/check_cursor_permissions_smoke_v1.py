#!/usr/bin/env python3
"""Smoke-check .cursor/permissions.json vs mcp.json (B-track ops, no auto-apply)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PERMS = ROOT / ".cursor/permissions.json"
DEFAULT_MCP = ROOT / ".cursor/mcp.json"
DEFAULT_META = ROOT / "docs/final/artifacts/fixtures/mkm_cursor_permissions_draft_meta_v1.json"
DEFAULT_OUT = ROOT / "reports/cursor_permissions_smoke_latest.json"

ALLOWED_TOP_KEYS = frozenset({"mcpAllowlist", "autoRun"})
ALLOWED_AUTORUN_KEYS = frozenset({"allow_instructions", "block_instructions"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mcp_server_names(mcp_doc: dict) -> set[str]:
    servers = mcp_doc.get("mcpServers") or {}
    return {str(k) for k in servers.keys()}


def _allowlist_servers(allowlist: list) -> set[str]:
    names: set[str] = set()
    for entry in allowlist:
        s = str(entry).split(":", 1)[0].strip()
        if s:
            names.add(s)
    return names


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--permissions-json", type=Path, default=DEFAULT_PERMS)
    ap.add_argument("--mcp-json", type=Path, default=DEFAULT_MCP)
    ap.add_argument("--meta-json", type=Path, default=DEFAULT_META)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    errors: list[str] = []
    if not args.permissions_json.is_file():
        errors.append(f"missing {args.permissions_json}")
    if not args.mcp_json.is_file():
        errors.append(f"missing {args.mcp_json}")

    perms: dict = {}
    mcp: dict = {}
    if not errors:
        perms = json.loads(args.permissions_json.read_text(encoding="utf-8-sig"))
        mcp = json.loads(args.mcp_json.read_text(encoding="utf-8-sig"))
        extra_keys = set(perms.keys()) - ALLOWED_TOP_KEYS
        if extra_keys:
            errors.append(f"non-official top-level keys: {sorted(extra_keys)}")
        allow = perms.get("mcpAllowlist")
        if not isinstance(allow, list) or not allow:
            errors.append("mcpAllowlist must be non-empty list")
        auto = perms.get("autoRun")
        if not isinstance(auto, dict):
            errors.append("autoRun must be object")
        else:
            bad = set(auto.keys()) - ALLOWED_AUTORUN_KEYS
            if bad:
                errors.append(f"autoRun unknown keys: {sorted(bad)}")
            for k in ALLOWED_AUTORUN_KEYS:
                if k not in auto or not isinstance(auto[k], list):
                    errors.append(f"autoRun.{k} must be list")

    mcp_names = _mcp_server_names(mcp) if mcp else set()
    allowed_names = _allowlist_servers(perms.get("mcpAllowlist") or []) if perms else set()
    unlisted = sorted(mcp_names - allowed_names) if mcp_names else []

    report = {
        "schema": "cursor_permissions_smoke_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "permissions_json": str(args.permissions_json).replace("\\", "/"),
        "mcp_server_count": len(mcp_names),
        "allowlist_server_names": sorted(allowed_names),
        "mcp_servers_not_in_allowlist": unlisted,
        "errors": errors,
        "ok": len(errors) == 0,
        "meta_fixture": str(args.meta_json).replace("\\", "/") if args.meta_json.is_file() else None,
        "note_ko": "통과=JSON·키 계약 OK. Run Mode UI는 Cursor 수동 확인.",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "errors": errors, "unlisted_mcp": unlisted}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
