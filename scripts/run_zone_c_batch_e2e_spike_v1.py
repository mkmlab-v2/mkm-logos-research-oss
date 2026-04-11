#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.55, K:0.75, M:0.45}
# Balance: 86
# Purpose: E2E spike — zone_c integrity rows × N batched via micro_payload_batch_v1 vs raw sum.
# Keywords: batch, capsule, zone_c, BEP, integrity
"""Zone_c batch E2E spike (v1).

Reads ``integrity_cost_model_v4`` JSON (``--integrity-json``), takes the listed cases in order,
cycles them to ``--batch-n`` (default 11) rows, and builds opaque payloads whose byte length equals
each row's ``total_wire_bytes`` (varint4 path from the artifact).

Metrics:
  - ``sum_raw_utf8``: sum of ``bytes_raw_utf8`` over the N cycled cases.
  - ``batch_wire_bytes``: ``len(encode_batch_v1(payloads))`` = capsule overhead + sum(wire_i).
  - ``s_real_batch_vs_raw``: ``1 - batch_wire_bytes / sum_raw_utf8``.
  - ``unbatched_sum_wire``: sum of per-case ``total_wire_bytes`` (no batch framing).
  - ``eleven_separate_capsules_bytes``: ``N * overhead_bytes_v1(1) + sum(wire_i)`` — same payloads,
    each in its own 1-payload MKM1 capsule (amortization baseline).

Payload bytes are zero-filled placeholders; only lengths matter for wire accounting.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.micro_payload_batch_v1 import (  # noqa: E402
    decode_batch_v1,
    encode_batch_v1,
    overhead_bytes_v1,
)


def _load_cases(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = list(data.get("cases") or [])
    out: list[dict[str, Any]] = []
    for r in rows:
        if r.get("exact_match"):
            continue
        out.append(r)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Zone_c batch E2E wire spike (MKM1 capsule).")
    ap.add_argument(
        "--integrity-json",
        type=Path,
        default=ROOT / "docs/final/artifacts/INTEGRITY_COST_V4_ZONE_C_HANGUL_GAP1_V1.json",
        help="integrity_cost_model_v4 JSON (zone_c cohort).",
    )
    ap.add_argument("--batch-n", type=int, default=11, help="Number of cycled cases (default 11).")
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "docs/final/artifacts/ZONE_C_BATCH_E2E_SPIKE_V1.json",
        help="Write JSON summary.",
    )
    args = ap.parse_args()

    path = Path(args.integrity_json).resolve()
    if not path.is_file():
        print(f"FAIL: not found {path}", file=sys.stderr)
        return 1
    if int(args.batch_n) < 1:
        print("FAIL: --batch-n must be >= 1", file=sys.stderr)
        return 1

    data = json.loads(path.read_text(encoding="utf-8"))
    cases = _load_cases(data)
    if not cases:
        print("FAIL: no non-exact cases in JSON", file=sys.stderr)
        return 1

    n_batch = int(args.batch_n)
    cycled: list[dict[str, Any]] = [cases[i % len(cases)] for i in range(n_batch)]

    sum_raw = sum(int(c["bytes_raw_utf8"]) for c in cycled)
    wires = [int(c["total_wire_bytes"]) for c in cycled]
    sum_wire = sum(wires)
    payloads = [bytes(w) for w in wires]

    capsule = encode_batch_v1(payloads)
    batch_wire = len(capsule)
    # Round-trip sanity
    cap = decode_batch_v1(capsule)
    assert len(cap.payloads) == n_batch and [len(p) for p in cap.payloads] == wires

    overhead_batch = overhead_bytes_v1(n_batch)
    assert overhead_batch + sum_wire == batch_wire

    per_capsule = overhead_bytes_v1(1)
    eleven_separate = n_batch * per_capsule + sum_wire

    s_real = 1.0 - (batch_wire / float(sum_raw)) if sum_raw else 0.0
    saving_vs_separate_capsules = eleven_separate - batch_wire

    payload_out: dict[str, Any] = {
        "schema": "zone_c_batch_e2e_spike_v1",
        "description": (
            "Cycled zone_c integrity cases; opaque payloads sized to total_wire_bytes (varint4); "
            "MKM1 batch capsule wire vs sum(raw)."
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_integrity_json": (
            str(path.relative_to(ROOT)).replace("\\", "/")
            if path.is_relative_to(ROOT)
            else str(path)
        ),
        "inputs": {
            "batch_n": n_batch,
            "cohort_case_count": len(cases),
            "cycled_ids": [str(c.get("id")) for c in cycled],
        },
        "bytes": {
            "sum_raw_utf8": int(sum_raw),
            "sum_per_case_wire_bytes": int(sum_wire),
            "batch_wire_bytes": int(batch_wire),
            "capsule_overhead_only_bytes": int(overhead_batch),
            "unbatched_sum_wire_only_bytes": int(sum_wire),
            "n_separate_one_payload_capsules_bytes": int(eleven_separate),
            "batch_vs_separate_capsules_savings_bytes": int(saving_vs_separate_capsules),
        },
        "rates": {
            "s_real_batch_wire_vs_raw": float(s_real),
            "s_real_batch_wire_vs_raw_percent": round(100.0 * s_real, 6),
        },
        "v4_snapshot": data.get("v4_config"),
        "integrity_summary_snapshot": data.get("summary"),
    }

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"OK: batch_n={n_batch} sum_raw={sum_raw} batch_wire={batch_wire} "
        f"S_real={s_real:.6f} wrote {out_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
