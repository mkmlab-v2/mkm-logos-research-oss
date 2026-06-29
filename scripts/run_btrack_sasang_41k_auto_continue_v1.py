#!/usr/bin/env python3
"""Auto-continue B-track Sasang-41k — hot-reload + Psi bridge + optional Logos pack [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
REPORTS = ROOT / "reports"
OUT_DEFAULT = REPORTS / "btrack_sasang_41k_auto_continue_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, timeout: int = 3600) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-300:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--skip-logos-pack", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    steps.append(_run("psi_refresh", [PY, "scripts/build_logos_psi_logic_extraction_v1.py"], timeout=120))
    hot_cmd = [PY, "scripts/run_btrack_sasang_41k_hot_reload_v1.py"]
    if args.verbose:
        hot_cmd.append("--verbose")
    steps.append(_run("sasang_hot_reload", hot_cmd, timeout=600))

    if not args.skip_logos_pack:
        steps.append(
            _run(
                "logos_research_commercial_pack",
                [PY, "scripts/run_logos_research_commercial_pack_v1.py", "--skip-phase-o"],
                timeout=300,
            )
        )

    hot = {}
    hot_path = REPORTS / "btrack_sasang_41k_hot_reload_v1_latest.json"
    if hot_path.is_file():
        hot = json.loads(hot_path.read_text(encoding="utf-8-sig"))

    overall_ok = all(s.get("ok") for s in steps) and hot.get("ok") is True

    doc = {
        "schema": "btrack_sasang_41k_auto_continue_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "delegation_scale": "L",
        "lane": "track_b_hypo",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_bridge": False,
        "theology_to_sales_forbidden": True,
        "completion_pass": hot.get("completion_pass"),
        "completion_score": hot.get("completion_score"),
        "mismatch_rate": hot.get("final_mismatch_rate"),
        "psi_bridge_ok": hot.get("psi_bridge_ok"),
        "ok": overall_ok,
        "steps": steps,
        "reproduce_cmd": "py scripts/run_btrack_sasang_41k_auto_continue_v1.py --verbose",
        "operator_board": hot.get("operator_board"),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": overall_ok, "mismatch_rate": doc["mismatch_rate"], "out": str(args.out)}, ensure_ascii=False))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
