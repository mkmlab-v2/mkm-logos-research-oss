from __future__ import annotations

import json
from pathlib import Path

from scripts import convert_btrack_eval_to_sasang_predictions as conv


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_converter_direction_mapping_and_confidence(tmp_path: Path, monkeypatch) -> None:
    src = tmp_path / "in.jsonl"
    out = tmp_path / "out.jsonl"
    _write_jsonl(
        src,
        [
            {"id": "a1", "direction": "up", "confidence": 0.91},
            {"id": "a2", "direction": "down", "confidence": 0.81},
            {"id": "a3", "direction": "flat", "confidence": 0.71},
        ],
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "convert_btrack_eval_to_sasang_predictions.py",
            "--input",
            str(src),
            "--out",
            str(out),
        ],
    )
    assert conv.main() == 0
    rows = _read_jsonl(out)
    assert [r["predicted_parent"] for r in rows] == ["SY", "TE", "SE"]
    assert rows[0]["confidence"] == 0.91


def test_converter_uses_state_map_when_provided(tmp_path: Path, monkeypatch) -> None:
    src = tmp_path / "in_state.jsonl"
    out = tmp_path / "out_state.jsonl"
    state_map = tmp_path / "state_map.json"
    _write_jsonl(src, [{"id": "x1", "state_id": 13, "direction": "down", "confidence": 0.5}])
    state_map.write_text(json.dumps({"13": "TY"}, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "convert_btrack_eval_to_sasang_predictions.py",
            "--input",
            str(src),
            "--out",
            str(out),
            "--state-map",
            str(state_map),
        ],
    )
    assert conv.main() == 0
    rows = _read_jsonl(out)
    assert rows[0]["predicted_parent"] == "TY"

