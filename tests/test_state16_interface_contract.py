from __future__ import annotations

import pytest

from scripts.core.state16_interface import NoopState16Adapter, State16Input, State16Output, validate_state16_output


def test_noop_adapter_returns_not_enabled() -> None:
    adapter = NoopState16Adapter()
    output = adapter.map_state(
        State16Input(
            case_id="x",
            raw_text="a",
            compressed_text="b",
            reconstructed_text="c",
            route_domain="ssot",
            route_shard_id="zone_d_ssot",
            metadata={},
        )
    )
    assert output.error_code == "STATE16_NOT_ENABLED"
    assert output.state_id is None


def test_validate_state16_output_range() -> None:
    validate_state16_output(State16Output(state_id=1, confidence=0.0))
    validate_state16_output(State16Output(state_id=16, confidence=1.0))
    with pytest.raises(ValueError):
        validate_state16_output(State16Output(state_id=17, confidence=0.5))
