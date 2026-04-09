#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "docs" / "final" / "artifacts" / "general_compression_benchmark_manifest_v1.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate general compression benchmark bundle files.")
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = ap.parse_args()

    m = json.loads(args.manifest.read_text(encoding="utf-8"))
    evidence = m.get("evidence_bundle", {}) or {}
    files = [
        evidence.get("summary_json"),
        evidence.get("timeseries_csv"),
        evidence.get("repro_command_txt"),
        evidence.get("kpi_gate_json"),
    ]
    missing = []
    for rel in files:
        if not isinstance(rel, str):
            missing.append(str(rel))
            continue
        p = (ROOT / rel).resolve()
        if not p.is_file():
            missing.append(str(p))
    if missing:
        print("FAIL: missing bundle files")
        for p in missing:
            print(f"- {p}")
        return 1

    # Hard lock: if stress benchmark explicitly marks high-compression NO_GO,
    # block bundle validation to prevent accidental promotion.
    stress_rel = evidence.get("restore_stress_json") or "docs/final/artifacts/general_compression_restore_stress_v1.json"
    stress_path = (ROOT / str(stress_rel)).resolve()
    if stress_path.is_file():
        stress = json.loads(stress_path.read_text(encoding="utf-8"))
        decision = (
            (stress.get("aggregate_gate") or {}).get("decision")
            or stress.get("decision")
            or ""
        )
        if str(decision).strip() == "NO_GO_HIGH_COMPRESSION_LOCK":
            print("FAIL: hard lock triggered by restore stress decision")
            print(f"- decision: {decision}")
            print(f"- source: {stress_path}")
            return 1
    else:
        print(f"WARN: restore stress file not found, skip hard-lock check: {stress_path}")
    print("OK: general compression bundle files present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
