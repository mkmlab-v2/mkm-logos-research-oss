from __future__ import annotations

import json
from pathlib import Path

from scripts import build_sasang_commercialization_readiness_packet as mod


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_build_packet_marks_not_yet_when_promotion_chain_missing(tmp_path: Path, monkeypatch) -> None:
    lens = tmp_path / "lens.json"
    gate_std = tmp_path / "gate_std.json"
    gate_strict = tmp_path / "gate_strict.json"

    out_contract = tmp_path / "contract.json"
    out_gate = tmp_path / "promotion_gate.json"
    out_failure = tmp_path / "failure.json"
    out_packet = tmp_path / "packet.json"
    out_shadow = tmp_path / "shadow_governance.json"

    _write_json(
        lens,
        {
            "scores": {"direction_score": 0.0, "confidence": 0.49},
            "sasang_stream_outputs": {"mapping_target": "sideways"},
        },
    )
    _write_json(gate_std, {"decision": "PASS"})
    _write_json(gate_strict, {"decision": "HOLD"})

    monkeypatch.setattr(
        "sys.argv",
        [
            "build_sasang_commercialization_readiness_packet.py",
            "--lens",
            str(lens),
            "--high-gate",
            str(gate_std),
            "--high-gate-strict",
            str(gate_strict),
            "--eval-contract-out",
            str(out_contract),
            "--promotion-gate-out",
            str(out_gate),
            "--failure-analysis-out",
            str(out_failure),
            "--readiness-packet-out",
            str(out_packet),
            "--shadow-governance-out",
            str(out_shadow),
        ],
    )

    assert mod.main() == 0

    gate_doc = json.loads(out_gate.read_text(encoding="utf-8"))
    packet_doc = json.loads(out_packet.read_text(encoding="utf-8"))
    failure_doc = json.loads(out_failure.read_text(encoding="utf-8"))
    shadow_doc = json.loads(out_shadow.read_text(encoding="utf-8"))

    assert gate_doc["status"] == "FAIL"
    assert gate_doc["track_wall"]["a_track_autobind_forbidden"] is True
    assert packet_doc["decision"] == "NOT_YET"
    assert "promotion_chain_coverage" in [x["axis"] for x in failure_doc["failure_axes"]]
    assert shadow_doc["decision"] == "KEEP_OBSERVATION_ONLY"
