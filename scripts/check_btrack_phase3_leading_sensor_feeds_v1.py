#!/usr/bin/env python3
"""Validate Phase 3 leading-sensor feeds vs manifest (research_only gate)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/final/artifacts/btrack_phase3_leading_sensors_manifest_v1.json"
SENSOR_DIR = ROOT / "data/btrack/phase3_leading_sensors"
DEFAULT_OUT = ROOT / "reports/btrack_phase3_leading_sensor_feeds_check_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _count_jsonl(path: Path) -> int:
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--sensor-dir", type=Path, default=SENSOR_DIR)
    ap.add_argument("--min-rows", type=int, default=20)
    ap.add_argument("--require-measured", type=int, default=0, help="Min sensors with measured file.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict", action="store_true", help="Exit 1 if any sensor missing.")
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    sensors_report: list[dict[str, Any]] = []
    n_measured = 0
    for s in manifest.get("sensors") or []:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("sensor_id") or "")
        measured_rel = s.get("measured_jsonl_relpath") or f"{sid}_measured.jsonl"
        stub_rel = s.get("stub_jsonl_relpath") or f"{sid}_stub.jsonl"
        measured_path = args.sensor_dir / measured_rel
        stub_path = args.sensor_dir / stub_rel
        used = None
        n_rows = 0
        if measured_path.is_file():
            used = "measured"
            n_rows = _count_jsonl(measured_path)
            n_measured += 1
        elif stub_path.is_file():
            used = "stub"
            n_rows = _count_jsonl(stub_path)
        sensors_report.append(
            {
                "sensor_id": sid,
                "used": used,
                "n_rows": n_rows,
                "measured_path": str(measured_path) if measured_path.is_file() else None,
                "stub_path": str(stub_path) if stub_path.is_file() else None,
                "ok": used is not None and n_rows >= args.min_rows,
            }
        )

    ok = all(r["ok"] for r in sensors_report) and n_measured >= args.require_measured
    payload = {
        "schema": "btrack_phase3_leading_sensor_feeds_check_v1",
        "generated_at_utc": _utc_now(),
        "ok": ok,
        "n_measured_sensors": n_measured,
        "require_measured": args.require_measured,
        "sensors": sensors_report,
        "track_a_promotion": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out.resolve()} ok={ok}")
    if args.strict and not ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
