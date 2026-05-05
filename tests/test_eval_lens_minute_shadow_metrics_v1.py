# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.eval_lens_minute_shadow_metrics_v1 import build_metrics  # noqa: E402
from scripts.run_lens_minute_shadow_eval_smoke_v1 import build_report  # noqa: E402


def test_metrics_from_smoke_report():
    rep = build_report(bars=5, interval_minutes=1, asset_id="T")
    m = build_metrics(rep)
    assert m["schema"] == "lens_minute_shadow_eval_metrics_v1"
    assert m["n_bars"] == 5
    assert m["label_gate"]["label_gate_ready"] is False
    assert m["aggregates"]["myeongni_direction_mean"] is not None


def test_metrics_rejects_wrong_input_schema():
    with pytest.raises(ValueError, match="lens_minute_shadow_eval_v1"):
        build_metrics({"schema": "other", "rows": []})


def test_metrics_output_matches_json_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema_path = _REPO / "docs" / "final" / "artifacts" / "schemas" / "lens_minute_shadow_eval_metrics_v1.schema.json"
    rep = build_report(bars=5, interval_minutes=1, asset_id="T")
    m = build_metrics(rep)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(m)
