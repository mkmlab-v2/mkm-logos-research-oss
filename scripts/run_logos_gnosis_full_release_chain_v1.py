#!/usr/bin/env python3
"""Fetch Gnosis v0.9.3 + full Strong's ingest + graph refresh [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_DEST = ROOT / "storage/external_kg/gnosis_v0.9.3"
DEFAULT_OUT = ROOT / "reports/logos_gnosis_full_release_chain_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(label: str, cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return {
        "label": label,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "tail": ((proc.stdout or "") + (proc.stderr or "")).strip()[-500:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    ap.add_argument("--max-edges", type=int, default=350000)
    ap.add_argument("--skip-download", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    fetch_cmd = [PY, "scripts/fetch_logos_gnosis_kg_release_v1.py", "--dest", str(args.dest)]
    if args.skip_download:
        fetch_cmd.append("--skip-download")

    steps = [
        _run("fetch_gnosis_release", fetch_cmd),
        _run(
            "gnosis_full_ingest",
            [
                PY,
                "scripts/ingest_logos_gnosis_kg_lemma_edges_v1.py",
                "--gnosis-dir",
                str(args.dest),
                "--ack-license-cc-by-sa-4",
                "--max-edges",
                str(args.max_edges),
            ],
        ),
        _run("cosmic_anchor_graph_bridge", [PY, "scripts/build_logos_cosmic_anchor_graph_bridge_v1.py"]),
        _run("subgraph_graphrag_router", [PY, "scripts/run_logos_subgraph_graphrag_router_v1.py"]),
        _run("external_kg_manifest", [PY, "scripts/build_logos_external_kg_ingest_manifest_v1.py"]),
        _run("graphrag_evidence_pack", [PY, "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"]),
    ]

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_smoke",
                [
                    PY,
                    "-m",
                    "pytest",
                    "tests/test_fetch_logos_gnosis_kg_release_v1.py",
                    "tests/test_ingest_logos_gnosis_kg_lemma_edges_v1.py",
                    "tests/test_build_logos_external_kg_ingest_manifest_v1.py",
                    "-q",
                    "--tb=short",
                ],
            )
        )

    all_ok = all(s["ok"] for s in steps)
    report = {
        "schema": "logos_gnosis_full_release_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "dest_dir": str(args.dest),
        "max_edges": args.max_edges,
        "steps": steps,
        "all_ok": all_ok,
        "reproduce": "py scripts/run_logos_gnosis_full_release_chain_v1.py --skip-download --max-edges 350000",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": all_ok, "out": str(args.out)}, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
