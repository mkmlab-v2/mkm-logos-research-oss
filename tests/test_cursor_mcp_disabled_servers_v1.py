"""Unit tests for cursor MCP disabled-servers persistence lib."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from cursor_mcp_disabled_servers_v1_lib import merge_disabled, build_sync_payload  # noqa: E402


def test_merge_disabled_dedupes_preserving_order():
    out = merge_disabled(["a", "b"], ["b", "c"])
    assert out == ["a", "b", "c"]


def test_build_sync_payload_merges_plugins():
    data = {"disabledMcpServers": ["custom-server"]}
    out = build_sync_payload(data, ["plugin-a", "plugin-b"])
    assert out["disabledMcpServers"] == ["custom-server", "plugin-a", "plugin-b"]
    assert out["lastBrowserConnectionMode"] == "editor"
