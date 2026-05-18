"""Regression: neutral attribution classifier."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.analyze_btrack_neutral_attribution_v1 import build_report, classify_row


def test_classify_low_confidence_gate_from_meta() -> None:
    row = {
        "predicted_direction": "neutral",
        "weighted_score": 0.17,
        "confidence": 0.18,
        "preliminary_direction": "bull",
        "low_confidence_direction_gate": {
            "applied": True,
            "reason": "below_min_direction_confidence",
        },
    }
    assert classify_row(row, margin=0.03, conf_thresh=0.25) == "low_confidence_gate"


def test_classify_margin_band() -> None:
    row = {
        "predicted_direction": "neutral",
        "weighted_score": 0.005,
        "confidence": 0.41,
        "preliminary_direction": "neutral",
        "low_confidence_direction_gate": {"applied": False},
    }
    assert classify_row(row, margin=0.03, conf_thresh=0.25) == "margin_band_neutral"


def test_build_report_counts() -> None:
    doc = {
        "rows": [
            {
                "instrument": "btc",
                "eval_date": "2026-05-01",
                "predicted_direction": "bull",
                "weighted_score": 0.5,
                "confidence": 0.5,
                "preliminary_direction": "bull",
                "low_confidence_direction_gate": {"applied": False},
            },
            {
                "instrument": "btc",
                "eval_date": "2026-05-02",
                "predicted_direction": "neutral",
                "weighted_score": 0.17,
                "confidence": 0.18,
                "preliminary_direction": "bull",
                "low_confidence_direction_gate": {"applied": True},
            },
        ]
    }
    report = build_report(doc, ensemble_cfg={"rules": {"tie_break_min_margin": 0.03}})
    assert report["summary"]["n_neutral_predictions"] == 1
    assert report["summary"]["low_confidence_gate_neutrals"] == 1
    assert report["operator_lines"]
    assert "would_be_directional_if_threshold_0_20" in report["summary"]
