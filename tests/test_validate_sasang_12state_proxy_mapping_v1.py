import json
from pathlib import Path

from scripts.validate_sasang_12state_proxy_mapping_v1 import main


def _write_mapping(tmp_path: Path, payload: dict) -> Path:
    p = tmp_path / "mapping.json"
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def _base_payload() -> dict:
    constitutions = ("taeyang", "soyanga", "taeeum", "soeum")
    stages = ("onset", "peak", "exhaustion")
    states = []
    for c in constitutions:
        for s in stages:
            states.append(
                {
                    "state_id": f"{c}_{s}",
                    "constitution": c,
                    "stage": s,
                    "direction_profile": "x",
                    "proxy_rules": {"k": "v"},
                    "veto_watchlist": s == "exhaustion",
                }
            )
    return {
        "schema": "sasang_12state_proxy_mapping_v1",
        "fixed_params": {"adx_period": 14, "rsi_period": 14},
        "states": states,
        "validation_contract": {"walkforward": {}, "promotion_gate": {}},
    }


def test_validate_sasang_12state_mapping_ok(monkeypatch, tmp_path: Path) -> None:
    p = _write_mapping(tmp_path, _base_payload())
    monkeypatch.setattr("sys.argv", ["validate_sasang_12state_proxy_mapping_v1.py", "--mapping-json", str(p)])
    assert main() == 0


def test_validate_sasang_12state_mapping_rejects_bad_count(monkeypatch, tmp_path: Path) -> None:
    payload = _base_payload()
    payload["states"] = payload["states"][:-1]
    p = _write_mapping(tmp_path, payload)
    monkeypatch.setattr("sys.argv", ["validate_sasang_12state_proxy_mapping_v1.py", "--mapping-json", str(p)])
    assert main() == 4
