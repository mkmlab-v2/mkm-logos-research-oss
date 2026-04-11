# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.6, L:0.5, K:0.55, M:0.4}
# Balance: 84
# Purpose: Smoke test for run_zone_c_batch_e2e_spike_v1 metrics invariants.
# Keywords: batch, e2e
from __future__ import annotations

import json
from pathlib import Path

from scripts.core.micro_payload_batch_v1 import encode_batch_v1, overhead_bytes_v1


def test_batch_wire_equals_overhead_plus_payloads(tmp_path: Path) -> None:
    integrity = {
        "cases": [
            {"id": "a", "bytes_raw_utf8": 100, "total_wire_bytes": 50, "exact_match": False},
            {"id": "b", "bytes_raw_utf8": 80, "total_wire_bytes": 40, "exact_match": False},
        ],
    }
    p = tmp_path / "integrity.json"
    p.write_text(json.dumps(integrity), encoding="utf-8")

    from scripts.run_zone_c_batch_e2e_spike_v1 import main as spike_main
    import sys

    out = tmp_path / "out.json"
    argv = [
        "run_zone_c_batch_e2e_spike_v1.py",
        "--integrity-json",
        str(p),
        "--batch-n",
        "3",
        "--out",
        str(out),
    ]
    old = sys.argv
    try:
        sys.argv = argv
        assert spike_main() == 0
    finally:
        sys.argv = old

    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["bytes"]["sum_raw_utf8"] == 100 + 80 + 100
    wires = [50, 40, 50]
    assert d["bytes"]["sum_per_case_wire_bytes"] == sum(wires)
    cap_len = len(encode_batch_v1([bytes(w) for w in wires]))
    assert d["bytes"]["batch_wire_bytes"] == cap_len
    assert cap_len == overhead_bytes_v1(3) + sum(wires)
