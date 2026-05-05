from __future__ import annotations

from scripts.build_macro_fragility_inputs_v1 import _default_payload


def test_default_payload_shape() -> None:
    payload = _default_payload()
    assert "metrics" in payload
    assert "baselines" in payload
    for key in ("move", "vix", "hy_oas", "dxy_vol"):
        assert key in payload["metrics"]
        assert key in payload["baselines"]
