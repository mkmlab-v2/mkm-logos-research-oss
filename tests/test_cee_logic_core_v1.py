from __future__ import annotations

from scripts.core.cee_logic_core_v1 import CEEInput, run_cee_logic_core_v1


def test_cee_core_deterministic_and_invariant() -> None:
    payload = CEEInput(
        case_id="case_01",
        raw_text="בְּרֵאשִׁית αβγ",
        compressed_text="בְּרֵאשִׁית αβ",
        reconstructed_text="בְּרֵאשִׁית αβγ",
        corpus_type="dss",
        metadata={"probe": "x"},
    )
    out1 = run_cee_logic_core_v1(payload)
    out2 = run_cee_logic_core_v1(payload)
    assert out1["schema"] == "cee_logic_core_v1"
    assert out1 == out2
    vec = out1["vector_4d"]
    total = float(vec["S"]) + float(vec["L"]) + float(vec["K"]) + float(vec["M"])
    assert abs(total - 1.0) < 1e-9
    assert abs(float(out1["vector_sum"]) - 1.0) < 1e-9
    assert 1 <= int(out1["state_id"]) <= 16
    assert float(out1["lambda_deviation"]) >= 0.0
    assert out1["corpus_type"] == "dss"
    assert out1["metadata_post_it"]["lane"] == "B-track"


def test_cee_core_canonical_lane_marker() -> None:
    payload = CEEInput(
        case_id="case_02",
        raw_text="ברית שלום",
        compressed_text="ברית",
        reconstructed_text="ברית שלום",
        corpus_type="canonical",
    )
    out = run_cee_logic_core_v1(payload)
    assert out["metadata_post_it"]["lane"] == "A-track"
