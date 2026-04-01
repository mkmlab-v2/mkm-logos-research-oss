from __future__ import annotations

import sys
from pathlib import Path


_BT_ROOT = Path(__file__).resolve().parents[1]
if str(_BT_ROOT) not in sys.path:
    sys.path.insert(0, str(_BT_ROOT))

from src.strategy.crypto_nitro_live_strategy import _resolve_state_id_with_source  # noqa: E402


def test_state_id_resolution_prefers_myeongni_state_id_ssot() -> None:
    signal_data = {
        "state_id": 9,
        "risk_assessment": {
            "myeongni_state_id": 4,
            "state_id": 7,
            "jema12_trinity": {"myeongni_state_id": 12, "state_id": 13},
        },
    }
    state_id, source = _resolve_state_id_with_source(signal_data)
    assert state_id == 4
    assert source == "risk_assessment.myeongni_state_id"


def test_state_id_resolution_fallback_order() -> None:
    signal_data = {
        "state_id": "6",
        "risk_assessment": {
            "state_id": 8,
            "jema12_trinity": {"myeongni_state_id": 10, "state_id": 11},
        },
    }
    state_id, source = _resolve_state_id_with_source(signal_data)
    assert state_id == 6
    assert source == "signal_data.state_id"


def test_state_id_resolution_ignores_invalid_and_preserves_legacy_none() -> None:
    signal_data = {
        "state_id": "invalid",
        "risk_assessment": {
            "myeongni_state_id": 20,
            "state_id": 0,
            "jema12_trinity": {"myeongni_state_id": -1, "state_id": "x"},
        },
    }
    state_id, source = _resolve_state_id_with_source(signal_data)
    assert state_id is None
    assert source == "none"

