"""Committed L1 side-channel integrated spike JSON shape (Fact-Lock, no full sweep)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPIKE = ROOT / "docs" / "final" / "artifacts" / "l1_permutation_channel_integrated_spike_latest.json"


def test_l1_permutation_channel_integrated_spike_artifact_schema() -> None:
    assert SPIKE.is_file(), f"missing SSOT artifact: {SPIKE}"
    data = json.loads(SPIKE.read_text(encoding="utf-8"))
    assert data.get("schema") == "l1_permutation_channel_integrated_spike_v3"
    assert data.get("research_only") is True
    wc = data.get("wire_codecs") or {}
    for key in (
        "msgpack_available",
        "zstandard_available",
        "round_trip_restore_via_codec_checked",
        "round_trip_restore_via_codec_ok",
    ):
        assert key in wc, f"wire_codecs missing {key}"
    inp = data.get("inputs") or {}
    assert "zstd_min_raw_bytes" in inp
    assert isinstance(data.get("rows"), list)
    for row in data["rows"]:
        assert "mode" in row
        assert "exact_restore_rate" in row
        assert "samples" in row
        if wc.get("msgpack_available"):
            for k in (
                "overhead_msgpack_bytes_mean",
                "overhead_adaptive_tagged_wire_bytes_mean",
                "adaptive_zstd_choice_rate",
            ):
                assert k in row, f"row {row.get('mode')} missing {k}"
    chk = wc.get("round_trip_restore_via_codec_checked", 0)
    ok = wc.get("round_trip_restore_via_codec_ok", 0)
    if wc.get("msgpack_available") and chk:
        assert ok == chk, "adaptive codec round-trip must match all checked samples"
