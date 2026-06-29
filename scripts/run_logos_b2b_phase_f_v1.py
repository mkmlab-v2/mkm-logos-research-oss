#!/usr/bin/env python3
"""Phase F — xref subgraph + router enrich + MS B2B appendix + registry refresh."""

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
OUT_DEFAULT = ROOT / "reports/logos_b2b_phase_f_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, timeout: int = 300) -> dict[str, Any]:
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
    ap.add_argument("--skip-phase-e", action="store_true")
    ap.add_argument("--xref-min-votes", type=int, default=10)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_phase_e:
        steps.append(_run("phase_e", [PY, "scripts/run_logos_b2b_phase_e_v1.py", "--skip-evolution-loop"]))

    steps.append(
        _run(
            "xref_subgraph",
            [
                PY,
                "scripts/build_logos_themed_xref_subgraph_v1.py",
                "--min-votes",
                str(args.xref_min_votes),
            ],
            timeout=600,
        )
    )
    steps.append(_run("router_xref_enrich", [PY, "scripts/enrich_logos_subgraph_router_with_xref_v1.py"]))
    steps.append(_run("reasoning_registry", [PY, "scripts/build_logos_reasoning_pattern_registry_v1.py"]))
    steps.append(_run("ms_b2b_appendix", [PY, "scripts/build_external_validation_ms_b2b_logic_appendix_v1.py"]))

    overall_ok = all(s["ok"] for s in steps)
    doc = {
        "schema": "logos_b2b_phase_f_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "steps": steps,
        "ok": overall_ok,
        "reproduce": "py scripts/run_logos_b2b_phase_f_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": overall_ok, "out": str(args.out)}, ensure_ascii=False))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
