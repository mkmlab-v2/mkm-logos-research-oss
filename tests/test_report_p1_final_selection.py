from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import report_p1_final_selection as mod


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _profile(best: dict, profile: str) -> dict:
    return {
        "schema": f"multilens_p1_ab_{profile}_v1",
        "profile": profile,
        "summary": {"candidate_count": 12, "passing_count": 2},
        "gate_contract": {
            "saving_rate_min": 0.5,
            "jaccard_drop_pp_max": 1.5,
            "sensitive_integrity_min": 0.999,
        },
        "best_candidate": best,
    }


def test_pick_winner_prefers_balanced_when_gate_ok() -> None:
    rows = [
        {"profile_name": "efficiency_first", "best_candidate": {"gate_ok": True, "global_token_saving_rate": 0.7, "jaccard_drop_pp": 0.2}},
        {"profile_name": "intensity_first", "best_candidate": {"gate_ok": True, "global_token_saving_rate": 0.71, "jaccard_drop_pp": 0.3}},
        {"profile_name": "balanced", "best_candidate": {"gate_ok": True, "global_token_saving_rate": 0.6, "jaccard_drop_pp": 0.0}},
    ]
    picked = mod._pick_winner(rows)
    assert picked["winner_profile"] == "balanced"


def test_pick_winner_fallback_uses_best_gate_ok_saving_then_drop() -> None:
    rows = [
        {"profile_name": "efficiency_first", "best_candidate": {"gate_ok": True, "global_token_saving_rate": 0.7, "jaccard_drop_pp": 0.2}},
        {"profile_name": "intensity_first", "best_candidate": {"gate_ok": True, "global_token_saving_rate": 0.7, "jaccard_drop_pp": 0.1}},
        {"profile_name": "balanced", "best_candidate": {"gate_ok": False, "global_token_saving_rate": 0.9, "jaccard_drop_pp": 0.0}},
    ]
    picked = mod._pick_winner(rows)
    assert picked["winner_profile"] == "intensity_first"


def test_pick_winner_last_resort_uses_highest_saving() -> None:
    rows = [
        {"profile_name": "efficiency_first", "best_candidate": {"gate_ok": False, "global_token_saving_rate": 0.4, "jaccard_drop_pp": 0.2}},
        {"profile_name": "intensity_first", "best_candidate": {"gate_ok": False, "global_token_saving_rate": 0.45, "jaccard_drop_pp": 0.1}},
        {"profile_name": "balanced", "best_candidate": {"gate_ok": False, "global_token_saving_rate": 0.41, "jaccard_drop_pp": 0.0}},
    ]
    picked = mod._pick_winner(rows)
    assert picked["winner_profile"] == "intensity_first"


def test_main_writes_output_schema_and_selection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    eff = tmp_path / "eff.json"
    intn = tmp_path / "intn.json"
    bal = tmp_path / "bal.json"
    out = tmp_path / "out.json"

    _write(
        eff,
        _profile(
            {
                "strategy": "A",
                "intensity": "extreme",
                "use_hangul_principle": True,
                "global_token_saving_rate": 0.51,
                "avg_reconstruction_fidelity_jaccard": 0.88,
                "jaccard_drop_pp": 0.01,
                "avg_sensitive_integrity": 1.0,
                "gate_ok": True,
            },
            "efficiency_first",
        ),
    )
    _write(
        intn,
        _profile(
            {
                "strategy": "A",
                "intensity": "high",
                "use_hangul_principle": True,
                "global_token_saving_rate": 0.5,
                "avg_reconstruction_fidelity_jaccard": 0.87,
                "jaccard_drop_pp": 0.02,
                "avg_sensitive_integrity": 1.0,
                "gate_ok": True,
            },
            "intensity_first",
        ),
    )
    _write(
        bal,
        _profile(
            {
                "strategy": "A",
                "intensity": "balanced",
                "use_hangul_principle": True,
                "global_token_saving_rate": 0.49,
                "avg_reconstruction_fidelity_jaccard": 0.9,
                "jaccard_drop_pp": 0.0,
                "avg_sensitive_integrity": 1.0,
                "gate_ok": True,
                "balanced_composite": 0.63,
            },
            "balanced",
        ),
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "report_p1_final_selection.py",
            "--efficiency",
            str(eff),
            "--intensity",
            str(intn),
            "--balanced",
            str(bal),
            "--output",
            str(out),
        ],
    )
    assert mod.main() == 0

    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "multilens_p1_ab_final_selection_v1"
    assert set(doc["source_refs"].keys()) == {"efficiency", "intensity", "balanced"}
    assert len(doc["profiles"]) == 3
    assert doc["selection"]["winner_profile"] == "balanced"


def test_main_fails_when_required_input_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    eff = tmp_path / "missing_eff.json"
    intn = tmp_path / "missing_intn.json"
    bal = tmp_path / "missing_bal.json"
    out = tmp_path / "out.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "report_p1_final_selection.py",
            "--efficiency",
            str(eff),
            "--intensity",
            str(intn),
            "--balanced",
            str(bal),
            "--output",
            str(out),
        ],
    )
    with pytest.raises(FileNotFoundError):
        mod.main()
