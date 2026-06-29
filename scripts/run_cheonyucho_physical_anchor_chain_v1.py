#!/usr/bin/env python3
"""P1 physical anchor chain: disk partials → index → fragment mine → gate ([HYPO])."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/constitution/btrack_pilot/cheonyucho_physical_anchor_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str]:
    print("+", " ".join(cmd), flush=True)
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
    tail = (cp.stdout or cp.stderr or "").strip().splitlines()
    return cp.returncode, tail[-1] if tail else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-network", action="store_true")
    ap.add_argument("--skip-fragment-mine", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    chain: list[tuple[str, list[str]]] = [
        ("disk_partials", [sys.executable, "scripts/ingest_cheonyucho_disk_partial_pastes_v1.py"]),
        ("proxy_index", [sys.executable, "scripts/build_cheonyucho_physical_proxy_index_v1.py"]),
    ]
    if not args.skip_network:
        chain.append(
            ("park1985_grep", [sys.executable, "scripts/run_cheonyucho_park1985_appendix_grep_v1.py"])
        )
    if not args.skip_fragment_mine:
        chain.append(("fragment_mine", [sys.executable, "scripts/run_cheonyucho_fragment_mine_v1.py"]))
    chain.append(("acquisition_gate", [sys.executable, "scripts/check_cheonyucho_acquisition_gate_v1.py"]))

    ok = True
    for step_id, cmd in chain:
        code, tail = _run(cmd)
        steps.append({"id": step_id, "exit_code": code, "ok": code == 0, "tail": tail})
        ok = ok and code == 0
        if code != 0:
            break

    report = {
        "schema": "cheonyucho_physical_anchor_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "hanja_canon_status": "not_acquired",
        "ok": ok,
        "steps": steps,
        "artifacts": {
            "physical_anchor": "reports/constitution/btrack_pilot/cheonyucho_physical_anchor_v1.json",
            "proxy_index": "reports/constitution/btrack_pilot/cheonyucho_physical_proxy_index_v1_latest.json",
            "acquisition_gate": "reports/constitution/btrack_pilot/cheonyucho_acquisition_gate_v1_latest.json",
        },
        "reproduce": "py scripts/run_cheonyucho_physical_anchor_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "steps": len(steps), "out": str(args.out)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
