"""Shield threshold sweep picks best but may not beat baseline."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "btrack_phase3_leading_sensors_lib_v1",
    ROOT / "scripts" / "btrack_phase3_leading_sensors_lib_v1.py",
)
_lib = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_lib)
hit_metrics = _lib.hit_metrics
rows_baseline = _lib.rows_baseline
rows_for_shield = _lib.rows_for_shield


def test_shield_never_beats_if_all_neutralized_wrong() -> None:
    rows = [
        {
            "predicted_direction": "bull",
            "actual_direction": "bull",
            "leading_composite_signed_flow_z": -0.5,
        },
        {
            "predicted_direction": "bear",
            "actual_direction": "bear",
            "leading_composite_signed_flow_z": 0.5,
        },
    ]
    base = hit_metrics(rows_baseline(rows))["price_directional_hit_rate"]
    shield = hit_metrics(rows_for_shield(rows, threshold=0.05))["price_directional_hit_rate"]
    assert base == 1.0
    assert shield == 0.0
