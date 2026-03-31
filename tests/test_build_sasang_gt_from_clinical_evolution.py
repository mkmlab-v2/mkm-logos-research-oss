from __future__ import annotations

import json
from pathlib import Path

from scripts import build_sasang_gt_from_clinical_evolution as mod


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_build_gt_with_manual_map(tmp_path: Path, monkeypatch) -> None:
    features = tmp_path / "features.jsonl"
    labels = tmp_path / "labels.jsonl"
    out = tmp_path / "out.jsonl"
    mp = tmp_path / "map.json"

    _write_jsonl(
        features,
        [
            {"case_id": "c1", "symptoms_weekly": {"facial_flushing": 8, "insomnia": 8}},
            {"case_id": "c2", "symptoms_weekly": {"cold_hands_feet": 8}},
        ],
    )
    _write_jsonl(labels, [{"case_id": "c1", "event_type": "stable"}])
    mp.write_text(json.dumps({"c1": "SY"}, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "build_sasang_gt_from_clinical_evolution.py",
            "--features",
            str(features),
            "--labels",
            str(labels),
            "--manual-map",
            str(mp),
            "--out",
            str(out),
        ],
    )
    assert mod.main() == 0
    rows = _read_jsonl(out)
    assert rows[0]["sample_id"] == "C1"
    assert rows[0]["expected_parent"] == "SY"
    assert rows[1]["expected_parent"] == "UNLABELED"

