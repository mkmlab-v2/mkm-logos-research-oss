"""Join prefers measured JSONL over stub."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.join_btrack_phase3_leading_sensors_score_v1 import _load_sensors, _resolve_sensor_path


def test_resolve_measured_over_stub() -> None:
    manifest = {
        "sensors": [
            {
                "sensor_id": "perp_funding_skew",
                "stub_jsonl_relpath": "perp_funding_skew_stub.jsonl",
                "measured_jsonl_relpath": "perp_funding_skew_measured.jsonl",
            }
        ]
    }
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "perp_funding_skew_stub.jsonl").write_text(
            json.dumps({"eval_date": "2026-01-01", "sensor_id": "perp_funding_skew", "features": {"signed_flow_z": 0.1}})
            + "\n",
            encoding="utf-8",
        )
        (d / "perp_funding_skew_measured.jsonl").write_text(
            json.dumps({"eval_date": "2026-01-01", "sensor_id": "perp_funding_skew", "features": {"signed_flow_z": 0.9}})
            + "\n",
            encoding="utf-8",
        )
        path, kind = _resolve_sensor_path(d, manifest["sensors"][0])
        assert kind == "measured"
        ids, by_date, sk = _load_sensors(manifest, d)
        assert by_date["2026-01-01"]["perp_funding_skew"]["features"]["signed_flow_z"] == 0.9
        assert sk["perp_funding_skew"] == "measured"
