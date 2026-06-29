#!/usr/bin/env python3
"""Phase E — B2B hub apply + MACULA-themed ingest + reasoning pattern registry."""

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
OUT_DEFAULT = ROOT / "reports/logos_b2b_phase_e_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str]) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-200:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--skip-evolution-loop", action="store_true")
    ap.add_argument("--macula-tsv-dir", type=Path, default=None)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_evolution_loop:
        steps.append(
            _run("b2b_evolution_loop", [PY, "scripts/run_logos_b2b_proposal_evolution_loop_v1.py"])
        )

    steps.append(_run("apply_master_summary_to_hub", [PY, "scripts/apply_logos_b2b_master_summary_to_hub_v1.py"]))

    macula_cmd = [PY, "scripts/ingest_logos_macula_themed_lemma_edges_v1.py"]
    if args.macula_tsv_dir:
        macula_cmd.extend(["--macula-tsv-dir", str(args.macula_tsv_dir)])
    steps.append(_run("macula_themed_ingest", macula_cmd))

    steps.append(
        _run("reasoning_pattern_registry", [PY, "scripts/build_logos_reasoning_pattern_registry_v1.py"])
    )

    overall_ok = all(s["ok"] for s in steps)
    doc = {
        "schema": "logos_b2b_phase_e_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "steps": steps,
        "ok": overall_ok,
        "reproduce": "py scripts/run_logos_b2b_phase_e_v1.py",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": overall_ok, "out": str(args.out)}, ensure_ascii=False))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
