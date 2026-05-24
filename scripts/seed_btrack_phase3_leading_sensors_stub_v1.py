#!/usr/bin/env python3
"""[HYPO] Calendar-dense stub JSONL for Phase 3 leading sensors (research_only).

Writes placeholder rows so downstream join/eval can wire paths before real feeds exist.
Does not touch prod score JSON or Track A.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/btrack_phase3_leading_sensors_manifest_v1.json"
DEFAULT_OUT_DIR = ROOT / "data/btrack/phase3_leading_sensors"


def _daterange(d0: date, d1: date) -> list[date]:
    out: list[date] = []
    cur = d0
    while cur <= d1:
        out.append(cur)
        cur += timedelta(days=1)
    return out


def _stub_row(sensor_id: str, d: date, i: int) -> dict:
    base = 0.5 + (i % 11) * 0.02
    return {
        "eval_date": d.isoformat(),
        "sensor_id": sensor_id,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "data_quality": "stub_calendar",
        "features": {
            "signed_flow_z": round((base - 0.55) * 2, 4),
            "level_pctile": round(min(0.95, max(0.05, base)), 4),
        },
        "note": "Replace with measured feed before any promotion claim.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2025-08-01")
    ap.add_argument("--end", default="2026-05-17")
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    sensors = manifest.get("sensors") or []
    d0 = date.fromisoformat(args.start)
    d1 = date.fromisoformat(args.end)
    days = _daterange(d0, d1)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for s in sensors:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("sensor_id") or "")
        if not sid:
            continue
        rel = s.get("stub_jsonl_relpath") or f"stub_{sid}.jsonl"
        out_path = args.out_dir / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [_stub_row(sid, d, i) for i, d in enumerate(days)]
        with out_path.open("w", encoding="utf-8") as f:
            for row in lines:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        written.append(str(out_path.relative_to(ROOT)).replace("\\", "/"))

    print(json.dumps({"ok": True, "n_days": len(days), "written": written}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
