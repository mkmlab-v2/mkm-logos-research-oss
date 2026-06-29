#!/usr/bin/env python3
"""One-click Job topology wiring: seed bundle -> graph merge -> slice -> presets -> router.

Reproducible:
  py scripts/run_showroom_job_topology_wiring_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref  # noqa: E402


def _run(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, cwd=ROOT, check=False)
    return int(proc.returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-merge-graph", action="store_true")
    ap.add_argument("--max-nodes", type=int, default=320)
    ap.add_argument("--max-edges", type=int, default=220)
    args = ap.parse_args()
    py = sys.executable

    steps: list[tuple[str, list[str]]] = [
        ("layer_b_ux_markers", [py, "scripts/check_logos_graph_studio_layer_b_qa_v2_markers_v1.py"]),
        ("cosmic_meta_arch_ui", [py, "scripts/build_logos_cosmic_meta_architecture_ui_v1.py"]),
        (
            "job_seed_bundle",
            [
                py,
                "scripts/build_showroom_job_topology_seed_bundle_v1.py",
                "--include-psalm-stubs",
            ]
            + ([] if args.skip_merge_graph else ["--merge-meaning-graph"]),
        ),
        ("era_seed_bundle", [py, "scripts/build_showroom_chronology_era_topology_seed_bundle_v1.py"]),
        (
            "meaning_topology_slice",
            [
                py,
                "scripts/build_showroom_meaning_topology_graph_slice_v1.py",
                "--include-job-spine",
                "--include-chronology-era-spine",
                "--max-nodes",
                str(args.max_nodes),
                "--max-edges",
                str(args.max_edges),
            ],
        ),
        ("qa_presets", [py, "scripts/build_showroom_meaning_topology_qa_presets_v1.py"]),
        ("router_export", [py, "scripts/export_showroom_qa_router_paths_v1.py"]),
        ("qa_insight_cards",
            [py, "scripts/build_showroom_qa_node_insight_cards_v1.py"],
        ),
        ("era_insight_lattice", [py, "scripts/build_showroom_era_insight_lattice_v1.py"]),
    ]

    for name, cmd in steps:
        code = _run(cmd)
        if code != 0:
            print(f"FAIL: {name} exit={code}", file=sys.stderr)
            return code
        print(f"OK: {name}")

    bundle = ROOT / "docs/final/artifacts/showroom_job_topology_seed_bundle_v1_latest.json"
    slice_path = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
    if bundle.is_file() and slice_path.is_file():
        bdoc = json.loads(bundle.read_text(encoding="utf-8"))
        sdoc = json.loads(slice_path.read_text(encoding="utf-8"))
        forced = set(bdoc.get("node_ids") or [])
        in_slice = {str(n.get("id")) for n in sdoc.get("nodes") or []}
        missing = sorted(forced - in_slice)
        if missing:
            print(f"FAIL: job nodes missing from slice: {missing[:5]}", file=sys.stderr)
            return 1
        job_preset = None
        presets_path = (
            ROOT
            / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
            / "showroom_meaning_topology_qa_presets_v1.json"
        )
        if presets_path.is_file():
            pdoc = json.loads(presets_path.read_text(encoding="utf-8"))
            job_preset = next((p for p in pdoc.get("presets") or [] if p.get("id") == "job_job_suffering_reason"), None)
        if job_preset:
            hi = job_preset.get("highlight_node_ids") or []
            if len(hi) < 5:
                print(f"FAIL: job preset highlight too small: {len(hi)}", file=sys.stderr)
                return 1
            rp = job_preset.get("router_path_v1") or {}
            if not (rp.get("node_ids") or []):
                print("FAIL: job preset router_path_v1.node_ids empty", file=sys.stderr)
                return 1
            ps_refs = [canonical_verse_ref(r) for r in (rp.get("verse_refs") or []) if str(r).startswith("Ps")]
            if ps_refs:
                in_slice = {str(n.get("ref") or "") for n in sdoc.get("nodes") or []}
                missing_ps = [r for r in ps_refs if r not in in_slice]
                if missing_ps:
                    print(f"WARN: psalm refs not in slice refs: {missing_ps[:3]}", file=sys.stderr)

    cards_path = ROOT / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_qa_node_insight_cards_v1.json"
    if not cards_path.is_file():
        print("FAIL: insight cards missing", file=sys.stderr)
        return 1

    if cards_path.is_file():
        cdoc = json.loads(cards_path.read_text(encoding="utf-8"))
        if "showroom_psalm_verse::Ps.27.14" not in (cdoc.get("cards") or {}):
            print("FAIL: insight cards missing Ps.27.14 psalm anchor", file=sys.stderr)
            return 1
        if "theme::hope_endurance_psalm" not in (cdoc.get("cards") or {}):
            print("FAIL: insight cards missing hope_endurance_psalm theme", file=sys.stderr)
            return 1

    if not args.skip_pytest:
        code = _run(
            [
                py,
                "-m",
                "pytest",
                "tests/test_build_showroom_chronology_era_topology_seed_bundle_v1.py",
                "tests/test_build_showroom_job_topology_seed_bundle_v1.py",
                "tests/test_build_showroom_qa_node_insight_cards_v1.py",
                "tests/test_build_showroom_meaning_topology_graph_slice_v1.py",
                "tests/test_showroom_preset_routing_golden_v1.py",
                "tests/test_export_showroom_qa_router_paths_v1.py",
                "tests/test_logos_graph_studio_layer_b_qa_v2_markers_v1.py",
                "-q",
            ]
        )
        if code != 0:
            return code
        print("OK: pytest")

    print(
        json.dumps(
            {
                "ok": True,
                "bundle": str(bundle),
                "slice": str(slice_path),
                "max_nodes": args.max_nodes,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
