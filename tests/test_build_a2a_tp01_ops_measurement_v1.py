"""tp01 ops measurement smoke."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_a2a_tp01_ops_measurement_v1 import build_measurement_document

ROOT = Path(__file__).resolve().parents[1]


def test_build_measurement_document_ok():
    doc = build_measurement_document(ROOT, top_n=3)
    assert doc["schema"] == "a2a_tp01_ops_measurement_v1"
    assert doc["target_point_id"] == "tp01_cursor_ops_resume_handoff"
    assert doc["measurement_ok"] is True
    assert (doc.get("resume_pack_build") or {}).get("elapsed_ms") is not None
    assert (doc.get("token_bench") or {}).get("inject_off_tokens", 0) > 0


def test_emit_script_writes_json(tmp_path, monkeypatch):
    out = tmp_path / "measure.json"
    log = tmp_path / "log.jsonl"
    monkeypatch.setattr(
        "sys.argv",
        [
            "build_a2a_tp01_ops_measurement_v1.py",
            "--out",
            str(out),
            "--log",
            str(log),
            "--append-log",
        ],
    )
    from scripts.build_a2a_tp01_ops_measurement_v1 import main

    assert main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload.get("measurement_ok") is True
    assert log.is_file()
