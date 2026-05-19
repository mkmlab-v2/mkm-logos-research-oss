"""Registry seed from sweep summary."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "seed_btrack_effective_adjustments_registry_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("seed_reg", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_rows_from_sweep_shape() -> None:
    mod = _load()
    summary = {
        "generated_at_utc": "2026-05-16T00:00:00Z",
        "rows": [
            {
                "neutral_bps": 4.0,
                "lens_mean_test_accuracy": 0.52,
                "instrument_mean_test_accuracy": 0.54,
                "soft_passed": True,
            }
        ],
    }
    rows = mod._rows_from_sweep(summary, baseline_accuracy=0.5)
    assert len(rows) == 1
    assert rows[0]["adjustment_key"] == "neutral_bps:+4.000000"
    assert rows[0]["research_only"] is True


def test_seed_appends_once() -> None:
    mod = _load()
    with tempfile.TemporaryDirectory() as td:
        reg = Path(td) / "effective.jsonl"
        sweep = Path(td) / "sweep.json"
        sweep.write_text(
            json.dumps(
                {
                    "generated_at_utc": "2026-05-16T00:00:00Z",
                    "rows": [{"neutral_bps": 4.0, "lens_mean_test_accuracy": 0.5, "instrument_mean_test_accuracy": 0.5}],
                }
            ),
            encoding="utf-8",
        )
        import sys

        argv = [
            "seed",
            "--registry",
            str(reg),
            "--sweep-summary",
            str(sweep),
        ]
        old = sys.argv
        try:
            sys.argv = argv
            assert mod.main() == 0
            sys.argv = argv
            assert mod.main() == 0
        finally:
            sys.argv = old
        assert len(reg.read_text(encoding="utf-8").strip().splitlines()) == 1
