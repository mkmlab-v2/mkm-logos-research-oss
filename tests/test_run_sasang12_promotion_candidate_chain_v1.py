from __future__ import annotations

import json
from pathlib import Path

from scripts import run_sasang12_promotion_candidate_chain_v1 as mod


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_chain_emits_v1_to_v9_artifacts(tmp_path: Path, monkeypatch) -> None:
    lens = tmp_path / "lens.json"
    gate_std = tmp_path / "gate_std.json"
    gate_strict = tmp_path / "gate_strict.json"
    out_sweep = tmp_path / "sweep.json"
    out_chain = tmp_path / "chain.json"

    _write_json(lens, {"scores": {"direction_score": 0.12, "confidence": 0.7}})
    _write_json(gate_std, {"decision": "PASS"})
    _write_json(gate_strict, {"decision": "HOLD"})

    monkeypatch.setattr(
        "sys.argv",
        [
            "run_sasang12_promotion_candidate_chain_v1.py",
            "--lens",
            str(lens),
            "--gate-standard",
            str(gate_std),
            "--gate-strict",
            str(gate_strict),
            "--sweep-out",
            str(out_sweep),
            "--chain-out",
            str(out_chain),
        ],
    )

    assert mod.main() == 0
    sweep_doc = json.loads(out_sweep.read_text(encoding="utf-8"))
    chain_doc = json.loads(out_chain.read_text(encoding="utf-8"))

    assert sweep_doc["schema"] == "sasang_selector_sweep_v1"
    assert len(sweep_doc["candidates"]) == 9
    assert chain_doc["version_range"] == "v1_to_v9"
    assert chain_doc["candidate_count"] == 9
