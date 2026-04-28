#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
OUT_DEFAULT = ART / "genesis_pointer_routing_control_chain_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _run(cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "cmd": cmd,
        "exit_code": cp.returncode,
        "stdout": cp.stdout.strip(),
        "stderr": cp.stderr.strip(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--go-cut", type=float, default=0.9)
    ap.add_argument("--watch-cut", type=float, default=0.5)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    steps = []
    py = sys.executable
    steps.append(_run([py, "scripts/run_genesis_sequence_compression_sweep_v1.py"]))
    steps.append(_run([py, "scripts/run_genesis_sequence_net_efficiency_model_v1.py"]))
    steps.append(_run([py, "scripts/run_genesis_sequence_net_efficiency_sensitivity_v1.py"]))
    steps.append(
        _run([py, "scripts/label_genesis_net_efficiency_operating_zone_v1.py", "--go-cut", str(args.go_cut), "--watch-cut", str(args.watch_cut)])
    )
    steps.append(_run([py, "scripts/decide_genesis_pointer_routing_v1.py"]))

    all_ok = all(s["exit_code"] == 0 for s in steps)
    out_doc = {
        "schema": "genesis_pointer_routing_control_chain_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "promotion_required": True,
        "all_ok": all_ok,
        "inputs": {"go_cut": args.go_cut, "watch_cut": args.watch_cut},
        "steps": steps,
    }
    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": all_ok, "out": str(out_path)}, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
