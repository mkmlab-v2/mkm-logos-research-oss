#!/usr/bin/env python3
"""Recover + strict-filter + timeline repair (in-place) + ingest (--skip-bridge) — prevents fixture overwrite of live CSV.

B-track · send_gate HOLD.

Reproducible:
  py scripts/run_bigset_topic_preserve_chain_v1.py --topic-slug benei_haelohim_cross_refs
  py scripts/run_bigset_topic_preserve_chain_v1.py --topic-slug nephilim_watcher_cross_refs --strict
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PY = sys.executable
MERGE = ROOT / "scripts/merge_bigset_live_rows_v1.py"
FILTER = ROOT / "scripts/filter_bigset_tier0_csv_by_topic_v1.py"
REPAIR = ROOT / "scripts/repair_bigset_tier0_timeline_order_v1.py"
INGEST = ROOT / "scripts/run_bigset_ingest_spike_chain_v1.py"
OUT_REPORT = ROOT / "reports/bigset_topic_preserve_chain_v1_latest.json"
OUT_ARTIFACT = ROOT / "docs/final/artifacts/bigset_topic_preserve_chain_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    tail = (proc.stdout or proc.stderr or "").strip()[-400:]
    return {"cmd": " ".join(cmd), "exit_code": proc.returncode, "ok": proc.returncode == 0, "stdout_tail": tail}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--topic-slug", required=True)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--skip-merge", action="store_true", help="skip dataset recovery merge")
    ap.add_argument("--skip-timeline-repair", action="store_true")
    ap.add_argument("--skip-ingest", action="store_true")
    args = ap.parse_args()

    slug = args.topic_slug.strip()
    csv_path = ROOT / "docs/research/raw" / f"bigset_{slug}_tier0_v1.csv"
    nodes: list[dict[str, Any]] = []
    ok_all = True

    if not args.skip_merge:
        nodes.append(
            _run(
                [
                    PY,
                    str(MERGE),
                    "--csv",
                    str(csv_path.relative_to(ROOT)).replace("\\", "/"),
                    "--topic-slug",
                    slug,
                ]
            )
        )
        if not nodes[-1]["ok"]:
            ok_all = False

    if ok_all and args.strict:
        nodes.append(
            _run(
                [
                    PY,
                    str(FILTER),
                    "--csv",
                    str(csv_path.relative_to(ROOT)).replace("\\", "/"),
                    "--topic-slug",
                    slug,
                    "--strict",
                ]
            )
        )
        if not nodes[-1]["ok"]:
            ok_all = False

    if ok_all and not args.skip_timeline_repair and csv_path.is_file():
        nodes.append(
            _run(
                [
                    PY,
                    str(REPAIR),
                    "--csv",
                    str(csv_path.relative_to(ROOT)).replace("\\", "/"),
                    "--in-place",
                ]
            )
        )
        if not nodes[-1]["ok"]:
            ok_all = False

    if ok_all and not args.skip_ingest:
        nodes.append(
            _run([PY, str(INGEST), "--skip-bridge", "--topic-slug", slug])
        )
        if not nodes[-1]["ok"]:
            ok_all = False

    row_count = 0
    if csv_path.is_file():
        import csv

        row_count = sum(1 for _ in csv.DictReader(csv_path.open(encoding="utf-8-sig")))

    completion = {
        "schema": "bigset_topic_preserve_chain_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "send_gate": "HOLD",
        "topic_slug": slug,
        "strict": args.strict,
        "quality_ok": ok_all,
        "exit_code": 0 if ok_all else 1,
        "csv_path": str(csv_path.relative_to(ROOT)).replace("\\", "/"),
        "row_count": row_count,
        "nodes": nodes,
        "reproduce": (
            f"py scripts/run_bigset_topic_preserve_chain_v1.py --topic-slug {slug}"
            + (" --strict" if args.strict else "")
        ),
    }
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_ARTIFACT.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok_all, "row_count": row_count, "report": str(OUT_REPORT)}, ensure_ascii=False))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
