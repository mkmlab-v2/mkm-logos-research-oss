"""Smoke: rag_server/mcp_server.py tools (no stdio)."""
from __future__ import annotations

import json
import os
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytest.importorskip("mcp")


@pytest.fixture
def ragmod(tmp_path):
    os.environ["VAULT_PATH"] = str(tmp_path)
    os.environ["INDEX_PATH"] = str(tmp_path / "idx")
    os.environ["RAG_EXCLUDE_GLOBS"] = ""
    spec = spec_from_file_location("rag_mcp", ROOT / "rag_server" / "mcp_server.py")
    m = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(m)
    return m


def test_get_index_status(ragmod, tmp_path):
    s = json.loads(ragmod.get_index_status())
    assert s["ok"] is True
    assert s["vault_exists"] is True


def test_reindex_and_search(ragmod, tmp_path):
    (tmp_path / "a.md").write_text("hello world uniquexyz", encoding="utf-8")
    r = json.loads(ragmod.reindex_vault(max_files=100))
    assert r["ok"] is True
    assert r["indexed"] >= 1
    out = json.loads(ragmod.search_vault("uniquexyz", limit=5))
    assert out["ok"] is True
    assert out["count"] >= 1
