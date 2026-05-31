"""Tests for MISSION_LOG session rotation."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from rotate_mission_log_sessions_v1 import parse_session_prefix, rotate_sessions


def test_rotate_moves_oldest_sessions(tmp_path: Path) -> None:
    log = tmp_path / "MISSION_LOG.md"
    log.write_text(
        "# MISSION_LOG\n\n"
        "> **재개:** test\n"
        "> **세션 갱신 (a):** one\n"
        "> **세션 갱신 (b):** two\n"
        "> **세션 갱신 (c):** three\n"
        "## 🚀 전술 작전 보드\n\n| lane | next |\n",
        encoding="utf-8",
    )
    archive = tmp_path / "MISSION_LOG.sessions.md"
    lines = log.read_text(encoding="utf-8").splitlines(keepends=True)
    new_lines, stats = rotate_sessions(lines, max_keep=2, archive_path=archive)

    assert stats["session_total"] == 3
    assert stats["session_kept"] == 2
    assert stats["session_moved"] == 1
    assert archive.is_file()
    assert "> **세션 갱신 (c):** three" in archive.read_text(encoding="utf-8")

    body = "".join(new_lines)
    assert "> **세션 갱신 (a):** one" in body
    assert "> **세션 갱신 (b):** two" in body
    assert "> **세션 갱신 (c):** three" not in body


def test_parse_session_prefix_splits_meta() -> None:
    lines = [
        "# title\n",
        "> **재개:** x\n",
        "> **세션 갱신 (1):** y\n",
        "## 🚀 전술 작전 보드\n",
    ]
    meta, sessions, tail = parse_session_prefix(lines)
    assert any("재개" in m for m in meta)
    assert len(sessions) == 1
    assert tail[0].startswith("## 🚀")
