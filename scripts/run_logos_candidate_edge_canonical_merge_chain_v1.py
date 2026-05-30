#!/usr/bin/env python3
"""Chain: pending → canonical merge (deduped) → corpus graph bundle refresh."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MERGE = ROOT / "scripts/apply_logos_approved_pending_to_canonical_v1.py"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_candidate_edge_canonical_merge_chain_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    return int(proc.returncode), out if out else err


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chain-out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    code, tail = _run(
        [
            sys.executable,
            str(MERGE),
            "--acknowledge-canonical-risk",
            "--refresh-bundle",
        ]
    )
    steps = [{"step": "canonical_merge_and_bundle", "exit_code": code, "tail": tail}]

    doc = {
        "schema": "logos_candidate_edge_canonical_merge_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "exit_code": code,
        "steps": steps,
        "artifacts": {
            "merge_report": "docs/final/artifacts/logos_candidate_edge_canonical_merge_v1_latest.json",
            "bundle_json": "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json",
        },
    }

    out_path = args.chain_out if args.chain_out.is_absolute() else ROOT / args.chain_out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
