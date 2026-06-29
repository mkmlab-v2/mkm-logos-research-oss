"""bootstrap_compression_pilot_tenant_v1 — WTT turns[] flatten for PoC text field."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.bootstrap_compression_pilot_tenant_v1 import (  # noqa: E402
    _build_corpus,
    _ensure_compression_text_field,
    _strip_role_prefixes_from_text,
)


def test_ensure_compression_text_field_from_turns() -> None:
    row = {
        "session_id": "cs-001",
        "turns": [
            {"role": "user", "text": "hello"},
            {"role": "assistant", "text": "hi there"},
        ],
    }
    _ensure_compression_text_field(row)
    assert row["text"] == "[user] hello [assistant] hi there"
    assert row["wtt_session_id"] == "cs-001"


def test_ensure_compression_text_field_preserves_existing_text() -> None:
    row = {"text": "already flat", "turns": [{"role": "user", "text": "ignored"}]}
    _ensure_compression_text_field(row)
    assert row["text"] == "already flat"


def test_ensure_compression_text_field_strip_role_prefixes() -> None:
    row = {
        "turns": [
            {"role": "user", "text": "hello"},
            {"role": "assistant", "text": "hi"},
        ],
    }
    _ensure_compression_text_field(row, strip_role_prefixes=True)
    assert row["text"] == "hello hi"


def test_strip_role_prefixes_from_text() -> None:
    assert _strip_role_prefixes_from_text("[user] a [assistant] b") == "a b"


def test_build_corpus_writes_text_for_wtt_sessions(tmp_path: Path, monkeypatch) -> None:
    import scripts.bootstrap_compression_pilot_tenant_v1 as mod

    src = tmp_path / "wtt.jsonl"
    src.write_text(
        json.dumps(
            {
                "session_id": "s1",
                "turns": [{"role": "user", "text": "refund please"}],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    out_parent = tmp_path / "data" / "compression"
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    corpus = _build_corpus("test-tenant", src, 10)
    assert corpus.parent == out_parent
    line = json.loads(corpus.read_text(encoding="utf-8").strip())
    assert line["text"] == "[user] refund please"
    assert line["id"] == "prospect-test-tenant-000"


def test_build_corpus_strip_role_prefixes(tmp_path: Path, monkeypatch) -> None:
    import scripts.bootstrap_compression_pilot_tenant_v1 as mod

    src = tmp_path / "wtt.jsonl"
    src.write_text(
        json.dumps(
            {
                "session_id": "s2",
                "turns": [{"role": "user", "text": "refund"}],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    corpus = _build_corpus("t2", src, 10, strip_role_prefixes=True)
    line = json.loads(corpus.read_text(encoding="utf-8").strip())
    assert line["text"] == "refund"
    assert "btrack_cs_bodyonly_v1" in line["labels"]
