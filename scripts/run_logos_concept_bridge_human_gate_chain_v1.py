#!/usr/bin/env python3
"""Concept bridge Human Gate chain: build queue + miswire guard ([HYPO], B-track).

Reproducible:
  py scripts/run_logos_concept_bridge_human_gate_chain_v1.py
"""

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
DEFAULT_OUT = ROOT / "reports/logos_concept_bridge_human_gate_chain_v1_latest.json"
MISWIRE_GUARD = ROOT / "scripts/check_logos_track_a_miswire_guard_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(label: str, cmd: list[str], *, optional: bool = False) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    ok = proc.returncode == 0
    row = {
        "label": label,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "ok": ok,
        "tail": ((proc.stdout or "") + (proc.stderr or "")).strip()[-500:],
    }
    if not ok and not optional:
        raise SystemExit(f"{label} failed rc={proc.returncode}")
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wave", type=int, default=1)
    ap.add_argument("--skip-miswire-guard", action="store_true")
    ap.add_argument("--optional-miswire-guard", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    steps.append(
        _run(
            "build_human_gate_queue",
            [
                PY,
                "scripts/build_logos_concept_bridge_human_gate_queue_v1.py",
                "--wave",
                str(args.wave),
            ],
        )
    )

    queue_path = ROOT / "docs/final/artifacts/logos_concept_bridge_human_gate_queue_v1_latest.json"
    queue_snapshot: dict[str, Any] = {}
    if queue_path.is_file():
        queue_snapshot = json.loads(queue_path.read_text(encoding="utf-8-sig"))

    if not args.skip_miswire_guard and MISWIRE_GUARD.is_file():
        steps.append(
            _run(
                "miswire_guard",
                [PY, "scripts/check_logos_track_a_miswire_guard_v1.py"],
                optional=args.optional_miswire_guard,
            )
        )

    all_ok = all(s.get("ok") for s in steps)
    report = {
        "schema": "logos_concept_bridge_human_gate_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "wave": args.wave,
        "queue_count": queue_snapshot.get("queue_count"),
        "queue_artifact": queue_path.relative_to(ROOT).as_posix() if queue_path.is_file() else None,
        "all_ok": all_ok,
        "steps": steps,
        "reproduce": "py scripts/run_logos_concept_bridge_human_gate_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "queue_count": queue_snapshot.get("queue_count"),
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
