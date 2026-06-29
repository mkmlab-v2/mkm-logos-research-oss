#!/usr/bin/env python3
"""Offline verify no1kmedi encounter-sequence API wiring [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/no1kmedi_encounter_sequence_api_offline_smoke_v1_latest.json"
ROUTE = ROOT / "projects/no1kmedi/src/app/api/clinician/encounter-sequence-v1/route.ts"
BRIDGE = ROOT / "projects/no1kmedi/src/lib/km-encounter-sequence-python-bridge-v1.ts"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def verify(*, slug: str = "park_geumja") -> dict[str, Any]:
    route_ok = ROUTE.is_file() and "runEncounterSequenceClinicianChain" in ROUTE.read_text(encoding="utf-8")
    bridge_ok = BRIDGE.is_file()
    proc = subprocess.run(
        [PY, str(ROOT / "scripts/run_encounter_sequence_clinician_api_chain_v1.py"), "--slug", slug],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    py_chain_ok = proc.returncode == 0
    return {
        "schema": "no1kmedi_encounter_sequence_api_offline_smoke_v1",
        "generated_at_utc": _utc(),
        "offline_smoke_ok": route_ok and bridge_ok and py_chain_ok,
        "route_present": route_ok,
        "bridge_present": bridge_ok,
        "python_chain_ok": py_chain_ok,
        "slug": slug,
        "route_path": str(ROUTE).replace("\\", "/"),
        "send_gate": "HOLD",
        "note_ko": "HTTP :3010 live 호출 없음; route+bridge+python chain만 검증",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slug", default="park_geumja")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = verify(slug=args.slug)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["offline_smoke_ok"]}))
    return 0 if doc["offline_smoke_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
