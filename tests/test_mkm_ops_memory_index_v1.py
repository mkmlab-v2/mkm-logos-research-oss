"""Tests for MKM ops memory index builder and must_keep gate ([HYPO])."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from mkm_ops_memory_index_lib_v1 import (  # noqa: E402
    build_index_document,
    extract_anchor_block,
    missing_must_keep_tags,
    truncate_anchor_slice,
    verify_index_sources,
)


def test_extract_anchor_block_by_markers() -> None:
    lines = [
        "# title\n",
        "## 🚀 전술 작전 보드\n",
        "line-a\n",
        "### 📦 핸드오ff\n",
        "skip-me\n",
    ]
    block, (start, end) = extract_anchor_block(
        lines,
        anchor_start="## 🚀 전술 작전 보드",
        anchor_end="### 📦 핸드오ff",
    )
    assert "line-a" in block
    assert "skip-me" not in block
    assert start == 2
    assert end == 3


def test_must_keep_gate_detects_missing_tag() -> None:
    missing = missing_must_keep_tags("hello world", ["hello", "FORBIDDEN_TAG"])
    assert missing == ["FORBIDDEN_TAG"]


def test_build_index_document_with_fixtures(tmp_path: Path) -> None:
    mission = tmp_path / "MISSION_LOG.md"
    mission.write_text(
        "# MISSION_LOG\n\n"
        "## 🚀 전술 작전 보드\n\n"
        "**금지:** offline_4d bulk 500 merge · Track A·실매매\n"
        "FAIL-COMP-004 active report only.\n"
        "SEND_GATE: HOLD\n\n"
        "### 📦 핸드오ff · 다른 채팅 융합\n\n"
        "handoff tail\n\n"
        "**다음 1타 (레인 · 새 채팅):**\n\n"
        "| 레인 | 다음 1타 |\n"
        "| Oracle | **금지:** Track A · **HOLD** |\n\n"
        "### 🧠 메타인지\n\n"
        "meta tail\n",
        encoding="utf-8",
    )
    central_dir = tmp_path / "docs" / "final"
    central_dir.mkdir(parents=True)
    central = central_dir / "CENTRAL_AGENT_MEMORY_V1.md"
    central.write_text(
        "# CENTRAL\n\n"
        "<!-- ATHENA_CHECKPOINT_V1_START -->\n"
        "- hygiene weekly MISSION_LOG\n"
        "- MCP lean profile\n"
        "<!-- ATHENA_CHECKPOINT_V1_END -->\n",
        encoding="utf-8",
    )

    doc = build_index_document(tmp_path)
    assert doc["research_only"] is True
    assert len(doc["nodes"]) == 3
    errors = verify_index_sources(tmp_path, doc)
    assert errors == []

    out = tmp_path / "storage" / "meta" / "index.json"
    out.parent.mkdir(parents=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["nodes"]["prism_ops_mission_log_board"]["line_range"][0] == 3


def test_gate_fails_when_tag_stripped(tmp_path: Path) -> None:
    mission = tmp_path / "MISSION_LOG.md"
    mission.write_text(
        "## 🚀 전술 작전 보드\n\n"
        "Track A only — bulk tag removed\n\n"
        "SEND_GATE: HOLD\n\n"
        "### 📦 핸드오ff · 다른 채팅 융합\n",
        encoding="utf-8",
    )
    central_dir = tmp_path / "docs" / "final"
    central_dir.mkdir(parents=True)
    (central_dir / "CENTRAL_AGENT_MEMORY_V1.md").write_text(
        "<!-- ATHENA_CHECKPOINT_V1_START -->\n"
        "- hygiene MISSION_LOG MCP lean\n"
        "<!-- ATHENA_CHECKPOINT_V1_END -->\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="must_keep_tags missing"):
        build_index_document(tmp_path)


def test_truncate_anchor_slice_marks_overflow() -> None:
    text = "a" * 200
    preview, truncated = truncate_anchor_slice(text, max_chars=50)
    assert truncated is True
    assert "HYPO slice truncated" in preview
    assert len(preview) <= 50
