#!/usr/bin/env python3
"""[HYPO] Triage chain: inventory → auto-digest priority raw → blocked claims rollup."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_SCRIPT = ROOT / "scripts/build_mkm_research_digestion_inventory_v1.py"
COMPRESSION_INGEST = ROOT / "scripts/build_compression_lit_tier0_auto_ingest_v1.py"
PRIORITY_S1_INGEST = ROOT / "scripts/build_priority_s1_lit_tier0_auto_ingest_v1.py"
BATCH_S1_INGEST = ROOT / "scripts/build_batch_s1_lit_tier0_auto_ingest_v1.py"
DIGEST_CHAIN = ROOT / "scripts/run_mkm_digestion_engine_chain_v1.py"
BLOCKED = ROOT / "scripts/build_mkm_digestion_blocked_public_claims_v1.py"
INVENTORY = ROOT / "reports/mkm_research_digestion_inventory_v1_latest.json"
OUT = ROOT / "reports/mkm_research_digestion_triage_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = (cp.stdout or "").strip().splitlines()
    parsed = None
    if tail:
        try:
            parsed = json.loads(tail[-1])
        except json.JSONDecodeError:
            parsed = {"raw_tail": tail[-1][:400]}
    return {"cmd": cmd, "exit_code": int(cp.returncode), "parsed": parsed}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-digest", type=int, default=3, help="Max raw files to digest this run")
    ap.add_argument("--min-priority", type=int, default=3, help="Min priority_score for auto-digest")
    ap.add_argument("--skip-digest", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    rc = 0

    steps.append(
        {
            "name": "compression_lit_tier0_ingest",
            **_run([sys.executable, str(COMPRESSION_INGEST)]),
        }
    )
    if steps[-1]["exit_code"] != 0:
        rc = steps[-1]["exit_code"]

    steps.append(
        {
            "name": "priority_s1_lit_tier0_ingest",
            **_run([sys.executable, str(PRIORITY_S1_INGEST)]),
        }
    )
    if steps[-1]["exit_code"] != 0:
        rc = steps[-1]["exit_code"]

    if BATCH_S1_INGEST.is_file():
        steps.append(
            {
                "name": "batch_s1_lit_tier0_ingest",
                **_run([sys.executable, str(BATCH_S1_INGEST)]),
            }
        )
        if steps[-1]["exit_code"] != 0:
            rc = steps[-1]["exit_code"]

    steps.append(
        {
            "name": "inventory_initial",
            **_run([sys.executable, str(INVENTORY_SCRIPT), "--json"]),
        }
    )
    if steps[-1]["exit_code"] != 0:
        rc = steps[-1]["exit_code"]

    inv = json.loads(INVENTORY.read_text(encoding="utf-8-sig")) if INVENTORY.is_file() else {}
    queue = inv.get("priority_queue_top10") or []
    digest_targets: list[str] = []
    for row in queue:
        if len(digest_targets) >= args.max_digest:
            break
        if int(row.get("priority_score") or 0) < args.min_priority:
            continue
        raw = row.get("raw_path")
        if not raw:
            continue
        if row.get("tier") not in ("S2", "S2b"):
            continue
        digest_targets.append(raw)

    if not args.skip_digest:
        for raw in digest_targets:
            s = _run(
                [
                    sys.executable,
                    str(DIGEST_CHAIN),
                    "--input",
                    raw,
                    "--offline",
                ]
            )
            steps.append({"name": f"digest_{Path(raw).stem[:48]}", **s})
            if s["exit_code"] != 0:
                rc = s["exit_code"]

    steps.append({"name": "inventory_final", **_run([sys.executable, str(INVENTORY_SCRIPT), "--json"])})
    steps.append({"name": "blocked_public", **_run([sys.executable, str(BLOCKED)])})

    final_inv = json.loads(INVENTORY.read_text(encoding="utf-8-sig")) if INVENTORY.is_file() else {}

    manifest = {
        "schema": "mkm_research_digestion_triage_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "digest_targets": digest_targets,
        "steps": steps,
        "summary_initial": inv.get("summary"),
        "summary_final": final_inv.get("summary"),
        "priority_queue_top10": final_inv.get("priority_queue_top10"),
        "rc": rc,
        "reproducible_command": (
            f"py scripts/run_mkm_research_digestion_triage_chain_v1.py --max-digest {args.max_digest}"
        ),
    }
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "rc": rc, "digested": digest_targets, "s3": final_inv.get("summary", {}).get("s3_count")}))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
