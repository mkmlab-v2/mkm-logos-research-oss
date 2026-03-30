from __future__ import annotations

import json
from pathlib import Path

from scripts import build_state_sasang_ops_bundle as bundle


def _dump(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_build_state_sasang_ops_bundle_emits_all_outputs_and_go_counts(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(bundle, "_root", lambda: tmp_path)

    backtest = tmp_path / "backtest_results"
    docs = tmp_path / "docs" / "final" / "artifacts"
    prefix = "TEST_STATE_SASANG"

    verse_ids = [f"v{i}" for i in range(1, 6)]
    _dump(
        backtest / "intersection.json",
        {"relaxed_gate": {"verse_ids": verse_ids}},
    )
    _dump(
        docs / "LOGOS_STATE_MAPPING_V1.json",
        {
            "assignments": [
                {"state_id": i, "verse_id": f"v{i}", "cosine_state_verse": 0.9 - i * 0.01}
                for i in range(1, 6)
            ]
        },
    )
    _dump(
        docs / "SASANG_CROSS_REF_DRAFT.json",
        {
            "entries": [
                {
                    "entry_id": f"e{i}",
                    "sasang_type": "taeyangin",
                    "state_candidate_id": i,
                    "canonical_ref": f"v{i}",
                }
                for i in range(1, 6)
            ]
        },
    )
    probe_doc = {
        "hits": [
            {"verse_id": f"v{i}", "cosine_to_regime_fingerprint_4d": 0.7 + i * 0.01}
            for i in range(1, 6)
        ]
    }
    for name in ("bull", "bear", "sideways", "capitulation"):
        _dump(backtest / f"{name}.json", probe_doc)

    monkeypatch.setattr(
        "sys.argv",
        [
            "build_state_sasang_ops_bundle.py",
            "--intersection",
            str(backtest / "intersection.json"),
            "--bull",
            str(backtest / "bull.json"),
            "--bear",
            str(backtest / "bear.json"),
            "--sideways",
            str(backtest / "sideways.json"),
            "--capitulation",
            str(backtest / "capitulation.json"),
            "--logos-map",
            str(docs / "LOGOS_STATE_MAPPING_V1.json"),
            "--sasang-draft",
            str(docs / "SASANG_CROSS_REF_DRAFT.json"),
            "--prefix",
            prefix,
        ],
    )
    assert bundle.main() == 0

    expected_files = [
        f"{prefix}_STATE_SASANG_BRIDGE.json",
        f"{prefix}_STATE_SASANG_PRIORITY_ANCHOR_ONLY.json",
        f"{prefix}_STATE_SASANG_OPS_SUMMARY.json",
        f"{prefix}_STATE_EXECUTION_PRIORITY_TOP5.json",
        f"{prefix}_STATE_EXECUTION_CHECKLIST_TOP5.json",
        f"{prefix}_STATE_EXECUTION_CHECKLIST_TOP5_EVALUATED.json",
        f"{prefix}_STATE_EXECUTION_APPROVAL_PACKET_TOP5.json",
    ]
    for name in expected_files:
        assert (backtest / name).is_file(), f"missing output: {name}"

    approval = _load(backtest / f"{prefix}_STATE_EXECUTION_APPROVAL_PACKET_TOP5.json")
    assert approval["go_count"] == 5
    assert approval["hold_count"] == 0
    assert len(approval["items"]) == 5
