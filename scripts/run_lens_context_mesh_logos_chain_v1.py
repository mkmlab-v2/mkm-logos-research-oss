#!/usr/bin/env python3
"""Lens context mesh Logos chain — slice hop index + hub manifest (Strangler v1)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def _run(cmd: list[str]) -> int:
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr or r.stdout)
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-slice", action="store_true", help="Reuse existing graph slice artifact")
    ap.add_argument("--skip-studio-sync", action="store_true")
    args = ap.parse_args()

    steps: list[tuple[str, list[str]]] = []
    if not args.skip_slice:
        steps.append(
            (
                "graph_slice",
                [PY, "scripts/build_showroom_meaning_topology_graph_slice_v1.py"],
            )
        )
    steps.extend(
        [
            ("era_lattice", [PY, "scripts/build_showroom_era_insight_lattice_v1.py"]),
            ("hop_index", [PY, "scripts/build_lens_context_mesh_hop_index_v1.py"]),
            ("hub_manifest", [PY, "scripts/build_lens_context_mesh_hub_logos_v1.py"]),
        ]
    )
    if not args.skip_studio_sync:
        steps.append(
            (
                "studio_sync",
                ["node", "projects/no1kmedi/scripts/sync-logos-studio-data.mjs"],
            )
        )

    for name, cmd in steps:
        code = _run(cmd)
        if code != 0:
            print(json.dumps({"ok": False, "failed_step": name, "cmd": cmd}))
            return code

    out = {
        "ok": True,
        "hub": "docs/final/artifacts/lens_context_mesh_hub_logos_v1_latest.json",
        "hop_index": "docs/final/artifacts/lens_context_mesh_hop_index_logos_v1_latest.json",
        "reproduce": "py scripts/run_lens_context_mesh_logos_chain_v1.py",
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
