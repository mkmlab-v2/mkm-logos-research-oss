from __future__ import annotations

from scripts.build_kospi_biblical_mode_divergence_report_v1 import build


def test_mode_divergence_alert_when_mode_changes():
    c = {
        "stage": "precommercial_ready",
        "blockers": [],
        "gates": {
            "external_reality_gate": {
                "mode": "equivalent_n",
                "active_metrics": {"accuracy": 0.4, "dominant_share": 0.4, "n_samples": 90},
            }
        },
    }
    r = {
        "stage": "research",
        "blockers": ["external_recent_class_bias"],
        "gates": {
            "external_reality_gate": {
                "mode": "recent",
                "active_metrics": {"accuracy": 0.52, "dominant_share": 0.75, "n_samples": 30},
            }
        },
    }
    out = build(c, r, accuracy_gap_th=0.08, dom_gap_th=0.08)
    assert out["alert"] is True
    assert out["diff"]["mode_changed"] is True
    assert "blocker_set_changed" in out["alert_reasons"]
