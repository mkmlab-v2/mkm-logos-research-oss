from __future__ import annotations

import json
from pathlib import Path
import sys


def test_query_pack_loader_accepts_object_shape(tmp_path: Path) -> None:
    p = tmp_path / "pack.json"
    p.write_text(
        json.dumps(
            {
                "queries": [
                    {"id": "q1", "question": "A?"},
                    {"question": "B?", "tags": ["x"]},
                    {"id": "skip_no_question"},
                ]
            }
        ),
        encoding="utf-8",
    )
    from scripts.run_notebooklm_mega_insight_batch import _load_query_pack

    rows = _load_query_pack(p)
    assert len(rows) == 2
    assert rows[0]["id"] == "q1"
    assert rows[1]["id"].startswith("q")


def test_query_pack_loader_accepts_list_shape(tmp_path: Path) -> None:
    p = tmp_path / "pack.json"
    p.write_text(json.dumps([{"id": "q1", "question": "A?"}]), encoding="utf-8")
    from scripts.run_notebooklm_mega_insight_batch import _load_query_pack

    rows = _load_query_pack(p)
    assert len(rows) == 1
    assert rows[0]["question"] == "A?"


def test_main_writes_research_only_and_promotion_flags(tmp_path: Path, monkeypatch) -> None:
    pack = tmp_path / "pack.json"
    out_jsonl = tmp_path / "out.jsonl"
    out_summary = tmp_path / "summary.json"
    pack.write_text(json.dumps({"queries": [{"id": "q1", "question": "A?"}]}), encoding="utf-8")

    from scripts import run_notebooklm_mega_insight_batch as mod

    def _fake_run(*_args, **_kwargs):
        return {
            "answer": "ok",
            "conversation_id": "conv-1",
            "sources_used": [{"id": "s1"}],
            "citations": [],
            "references": [],
        }

    monkeypatch.setattr(mod, "_run_nlm_query", _fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_notebooklm_mega_insight_batch.py",
            "--query-pack",
            str(pack),
            "--jsonl-out",
            str(out_jsonl),
            "--summary-out",
            str(out_summary),
        ],
    )

    rc = mod.main()
    assert rc == 0

    summary = json.loads(out_summary.read_text(encoding="utf-8"))
    assert summary["research_only"] is True
    assert summary["promotion_required"] is True
    assert summary["a_track_autobind_forbidden"] is True
    assert summary["n_success"] == 1

    lines = out_jsonl.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["research_only"] is True
    assert row["promotion_required"] is True
    assert row["a_track_autobind_forbidden"] is True

