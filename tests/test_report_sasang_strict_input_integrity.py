from __future__ import annotations

import json
from pathlib import Path

from scripts import report_sasang_strict_input_integrity as mod


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_integrity_reports_paired_rows_root_cause(tmp_path: Path, monkeypatch) -> None:
    strict = tmp_path / "strict.json"
    shadow = tmp_path / "shadow.json"
    out = tmp_path / "integrity.json"

    _write_json(
        strict,
        {
            "decision": "HOLD",
            "snapshot": {"paired_rows": 64, "recall_macro": 0.8, "ece": 0.09, "brier_score": 0.1},
        },
    )
    _write_json(shadow, {"decision": "PASS"})

    monkeypatch.setattr(
        "sys.argv",
        [
            "report_sasang_strict_input_integrity.py",
            "--strict",
            str(strict),
            "--strict-shadow",
            str(shadow),
            "--out",
            str(out),
        ],
    )

    assert mod.main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["integrity"]["root_cause"] == "production_paired_rows_insufficient"
