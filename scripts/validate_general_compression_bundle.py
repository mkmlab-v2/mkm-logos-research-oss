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
    files = [
        m.get("evidence_bundle", {}).get("summary_json"),
        m.get("evidence_bundle", {}).get("timeseries_csv"),
        m.get("evidence_bundle", {}).get("repro_command_txt"),
        m.get("evidence_bundle", {}).get("kpi_gate_json"),
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
    print("OK: general compression bundle files present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
