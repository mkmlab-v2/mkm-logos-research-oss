#!/usr/bin/env python3
"""SMB/file-bus latency probe via mapped share (e.g. Z:\\) — research_only."""
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/share_bus_probe_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round((pct / 100.0) * (len(ordered) - 1)))
    return ordered[max(0, min(idx, len(ordered) - 1))]


def _probe_round(target: Path, payload_kb: int) -> float:
    payload = os.urandom(payload_kb * 1024)
    target.parent.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    target.write_bytes(payload)
    back = target.read_bytes()
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    if back != payload:
        raise RuntimeError("share readback mismatch")
    return elapsed_ms


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--share-root", default="Z:/", help="Mapped aux share root")
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--payload-kb-grid", default="64,256,1024")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    share = Path(args.share_root.replace("\\", "/"))
    if not share.exists():
        print(f"error: share not mounted: {share}", file=os.sys.stderr)
        return 1

    grid_kb = [int(x.strip()) for x in args.payload_kb_grid.split(",") if x.strip()]
    rows = []
    for kb in grid_kb:
        samples: list[float] = []
        for i in range(args.rounds):
            path = share / "nextgen_cpu_aux" / "probe" / f"bus_{kb}k_{i}.bin"
            samples.append(_probe_round(path, kb))
        rows.append(
            {
                "payload_kb": kb,
                "rounds": args.rounds,
                "bus_ms": {
                    "p50": round(statistics.median(samples), 3),
                    "p95": round(_percentile(samples, 95), 3),
                    "max": round(max(samples), 3),
                    "mean": round(statistics.mean(samples), 3),
                },
            }
        )

    doc = {
        "schema": "nextgen_clean_slate_cpu_share_bus_probe_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "share_root": str(share),
        "note": "Write+read roundtrip on SMB; not socket RTT",
        "grid": rows,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"wrote": str(args.out_json), "share": str(share)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
