#!/usr/bin/env python3
"""Sync nlm CLI cookies into notebooklm-mcp Playwright state.json (no browser)."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NLM_COOKIES = Path.home() / ".notebooklm-mcp-cli" / "profiles" / "default" / "cookies.json"
DEFAULT_MCP_STATE = (
    Path(os.environ.get("LOCALAPPDATA", ""))
    / "notebooklm-mcp"
    / "Data"
    / "browser_state"
    / "state.json"
)
OUT = ROOT / "reports" / "notebooklm_nlm_to_mcp_sync_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sync_cookies(nlm_cookies: Path, mcp_state: Path) -> dict:
    if not nlm_cookies.is_file():
        raise FileNotFoundError(f"nlm cookies missing: {nlm_cookies}")
    cookies = json.loads(nlm_cookies.read_text(encoding="utf-8"))
    if not isinstance(cookies, list) or not cookies:
        raise ValueError(f"unexpected cookies shape: {nlm_cookies}")

    state = {"cookies": cookies, "origins": []}
    mcp_state.parent.mkdir(parents=True, exist_ok=True)
    mcp_state.write_text(json.dumps(state), encoding="utf-8")

    meta_path = nlm_cookies.parent / "metadata.json"
    email = None
    if meta_path.is_file():
        try:
            email = json.loads(meta_path.read_text(encoding="utf-8")).get("email")
        except json.JSONDecodeError:
            email = None

    return {
        "schema": "notebooklm_nlm_to_mcp_sync_v1",
        "generated_at_utc": _utc(),
        "nlm_cookies_path": str(nlm_cookies),
        "mcp_state_path": str(mcp_state),
        "cookie_count": len(cookies),
        "account_email": email,
        "ok": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nlm-cookies", type=Path, default=DEFAULT_NLM_COOKIES)
    ap.add_argument("--mcp-state", type=Path, default=DEFAULT_MCP_STATE)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    doc = sync_cookies(args.nlm_cookies, args.mcp_state)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "cookie_count": doc["cookie_count"], "out": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
