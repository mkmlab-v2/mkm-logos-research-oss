from __future__ import annotations

from scripts.core.gematria_to_4d_bridge import build_gematria_4d_bridge


def test_bridge_maps_to_valid_state_and_vector() -> None:
    meta = {
        "raw_combined_sum": 1234,
        "compressed_combined_sum": 1201,
        "reconstructed_combined_sum": 1220,
    }
    out = build_gematria_4d_bridge(gematria_metadata=meta)
    vec = out.get("vector_4d")
    assert isinstance(vec, dict)
    assert set(vec.keys()) == {"S", "L", "K", "M"}
    total = float(vec["S"]) + float(vec["L"]) + float(vec["K"]) + float(vec["M"])
    assert abs(total - 1.0) < 1e-9
    state = int(out.get("state16"))
    assert 1 <= state <= 16
    assert float(out.get("distance_to_state16")) >= 0.0
