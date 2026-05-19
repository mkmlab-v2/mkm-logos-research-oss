from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _core():
    spec = importlib.util.spec_from_file_location(
        "btrack_multilens_per_date_core_v1",
        ROOT / "scripts" / "btrack_multilens_per_date_core_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_causal_history_excludes_future_days() -> None:
    core = _core()
    by_day = {
        "2026-04-01": {"mapping_target": "bull", "ts_utc": "2026-04-01T00:00:00Z"},
        "2026-04-10": {"mapping_target": "bear", "ts_utc": "2026-04-10T00:00:00Z"},
        "2026-05-01": {"mapping_target": "bull", "ts_utc": "2026-05-01T00:00:00Z"},
    }
    hist = core.causal_rows_through(by_day, "2026-04-15")
    assert len(hist) == 2
    assert hist[-1]["mapping_target"] == "bear"


def test_build_document_smoke() -> None:
    core = _core()
    doc = core.build_document(
        [
            {
                "eval_date": "2026-04-02",
                "instrument": "btc",
                "predicted_direction": "bull",
                "actual_direction": "bear",
            }
        ],
        instrument="btc",
    )
    assert doc["schema"] == "btrack_multilens_per_date_lens_v1"
    assert len(doc["rows"]) == 1
    row = doc["rows"][0]
    assert row["loop_mode"] == "causal_calendar_jsonl_per_date_v1"
    assert "myeongni" in row["lenses"]
    assert row["lenses"]["logos"].get("non_gating") is True


def test_builder_cli(tmp_path: Path) -> None:
    from scripts.build_btrack_multilens_per_date_lens_v1 import main

    score = tmp_path / "s.json"
    score.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "eval_date": "2026-04-02",
                        "instrument": "btc",
                        "predicted_direction": "neutral",
                        "actual_direction": "bull",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out.json"
    assert main(["--score-json", str(score), "--output-json", str(out), "--skip-jsonl-compat"]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["n_rows"] == 1
