from __future__ import annotations

import json
from pathlib import Path

from scripts import report_sasang_high_reliability_gate as mod


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_sasang_high_reliability_gate_pass(tmp_path: Path, monkeypatch) -> None:
    ops = tmp_path / "ops.json"
    clinical = tmp_path / "clinical.json"
    out = tmp_path / "out.json"

    _write_json(ops, {"decision": "PASS"})
    _write_json(
        clinical,
        {
            "diagnostics": {"paired_rows": 64},
            "metrics": {
                "recall_macro": 0.72,
                "confidence": {"ece": 0.10, "brier_score": 0.15},
            },
        },
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "report_sasang_high_reliability_gate.py",
            "--ops-gate",
            str(ops),
            "--clinical",
            str(clinical),
            "--out",
            str(out),
        ],
    )

    assert mod.main() == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["decision"] == "PASS"
    assert report["checks"]["ops_gate_pass"] is True


def test_sasang_high_reliability_gate_hold_when_calibration_bad(tmp_path: Path, monkeypatch) -> None:
    ops = tmp_path / "ops.json"
    clinical = tmp_path / "clinical.json"
    out = tmp_path / "out.json"

    _write_json(ops, {"decision": "PASS"})
    _write_json(
        clinical,
        {
            "diagnostics": {"paired_rows": 64},
            "metrics": {
                "recall_macro": 0.72,
                "confidence": {"ece": 0.31, "brier_score": 0.15},
            },
        },
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "report_sasang_high_reliability_gate.py",
            "--ops-gate",
            str(ops),
            "--clinical",
            str(clinical),
            "--out",
            str(out),
        ],
    )

    assert mod.main() == 1
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["decision"] == "HOLD"
    assert report["checks"]["ece_lte_threshold"] is False

