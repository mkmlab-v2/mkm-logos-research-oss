#!/usr/bin/env python3
"""Re-ingest OSI xrefs with relaxed min_weight for coverage expansion [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_osi_xref_expand_coverage_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _count_jsonl(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open("r", encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--osi-dir", type=Path, default=ROOT / "storage/external_kg/osi_v1")
    ap.add_argument("--ack-license-mit-pd", action="store_true", required=False)
    ap.add_argument("--min-weight", type=float, default=0.05)
    ap.add_argument("--max-edges", type=int, default=200000)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    prior_report = _read_json(ROOT / "reports/logos_osi_xref_ingest_v1_latest.json")
    prior_edges = int(prior_report.get("edges_built") or 0)

    cmd = [
        PY,
        "scripts/ingest_logos_osi_xref_edges_v1.py",
        "--osi-dir",
        str(args.osi_dir),
        "--ack-license-mit-pd",
        "--min-weight",
        str(args.min_weight),
        "--max-edges",
        str(args.max_edges),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    after_report = _read_json(ROOT / "reports/logos_osi_xref_ingest_v1_latest.json")
    after_edges = int(after_report.get("edges_built") or 0)
    jsonl_lines = _count_jsonl(ROOT / "docs/final/artifacts/logos_osi_xref_edges_v1.jsonl")

    ok = proc.returncode == 0
    report = {
        "schema": "logos_osi_xref_expand_coverage_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "min_weight": args.min_weight,
        "max_edges": args.max_edges,
        "prior_edges_built": prior_edges,
        "after_edges_built": after_edges,
        "delta_edges": after_edges - prior_edges,
        "jsonl_lines": jsonl_lines,
        "ingest_ok": ok,
        "ingest_exit_code": proc.returncode,
        "ingest_tail": ((proc.stdout or "") + (proc.stderr or "")).strip()[-400:],
        "reproduce": f"py scripts/run_logos_osi_xref_expand_coverage_v1.py --min-weight {args.min_weight} --ack-license-mit-pd",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "prior": prior_edges, "after": after_edges, "delta": report["delta_edges"]}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
