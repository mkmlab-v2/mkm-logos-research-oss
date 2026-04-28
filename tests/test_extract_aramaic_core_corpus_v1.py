"""Contract tests for Biblical Aramaic verse selection and extract CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "extract_aramaic_core_corpus_v1.py"

from scripts.extract_aramaic_core_corpus_v1 import (  # noqa: E402
    is_biblical_aramaic_core,
    parse_verse_id,
    row_is_aramaic_core,
)


def test_parse_verse_id_numbered_book() -> None:
    assert parse_verse_id("1Kin.2.3") == ("1Kin", 2, 3)


def test_parse_verse_id_multi_dot_book() -> None:
    assert parse_verse_id("Song.1.1") == ("Song", 1, 1)


def test_parse_verse_id_invalid() -> None:
    assert parse_verse_id("") is None
    assert parse_verse_id("Dan") is None


def test_is_biblical_aramaic_core_daniel_window() -> None:
    assert is_biblical_aramaic_core("Dan", 2, 3) is False
    assert is_biblical_aramaic_core("Dan", 2, 4) is True
    assert is_biblical_aramaic_core("Dan", 7, 28) is True
    assert is_biblical_aramaic_core("Dan", 8, 1) is False


def test_is_biblical_aramaic_core_ezra() -> None:
    assert is_biblical_aramaic_core("Ezra", 4, 7) is False
    assert is_biblical_aramaic_core("Ezra", 4, 8) is True
    assert is_biblical_aramaic_core("Ezra", 6, 18) is True
    assert is_biblical_aramaic_core("Ezra", 6, 19) is False
    assert is_biblical_aramaic_core("Ezra", 7, 11) is False
    assert is_biblical_aramaic_core("Ezra", 7, 12) is True
    assert is_biblical_aramaic_core("Ezra", 7, 26) is True
    assert is_biblical_aramaic_core("Ezra", 7, 27) is False


def test_is_biblical_aramaic_core_jeremiah() -> None:
    assert is_biblical_aramaic_core("Jer", 10, 11) is True
    assert is_biblical_aramaic_core("Jer", 10, 10) is False


def test_row_is_aramaic_core() -> None:
    assert row_is_aramaic_core({"verse_id": "Dan.2.4", "text": "x"}) is True
    assert row_is_aramaic_core({"verse_id": "Ezra.1.1"}) is False


def test_extract_cli_writes_filtered_jsonl(tmp_path: Path) -> None:
    inp = tmp_path / "in.jsonl"
    out = tmp_path / "out.jsonl"
    rows = [
        {"verse_id": "Dan.2.3", "text": "hebrew"},
        {"verse_id": "Dan.2.4", "text": "aramaic"},
        {"verse_id": "Ezra.5.1", "text": "aramaic"},
    ]
    inp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--input-jsonl", str(inp), "--output-jsonl", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
    got = [json.loads(ln) for ln in lines]
    assert {r["verse_id"] for r in got} == {"Dan.2.4", "Ezra.5.1"}
