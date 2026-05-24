#!/usr/bin/env python3
"""S13+: re-ingest lexical fill, rebuild single-anchor stack, ANN, showroom/B2B."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CORPUS = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_single_anchor_v1_latest.jsonl"
CORPUS_MANIFEST = ROOT / "docs/final/artifacts/logos_verse_4d_single_anchor_corpus_v1_latest.json"


def _run(cmd: list[str]) -> int:
    print(" ".join(cmd), flush=True)
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-ingest", action="store_true")
    ap.add_argument("--skip-mt-policy", action="store_true")
    ap.add_argument("--skip-rebuild", action="store_true")
    ap.add_argument("--skip-ann", action="store_true")
    ap.add_argument("--skip-showroom", action="store_true")
    ap.add_argument("--skip-multi-orbit", action="store_true")
    ap.add_argument("--max-verses-ann", type=int, default=0, help="0 = all rows for ANN")
    args = ap.parse_args()

    py = sys.executable
    steps: list[tuple[str, list[str]]] = []

    if not args.skip_ingest:
        steps.append(("ingest_lexical", [py, str(ROOT / "scripts/ingest_logos_gap_original_text_v1.py")]))
        steps.append(
            ("merge_complete", [py, str(ROOT / "scripts/merge_logos_verse_decoded_complete_v1.py")])
        )
    if not args.skip_mt_policy:
        steps.append(
            (
                "mt_only_policy",
                [py, str(ROOT / "scripts/build_logos_gap_mt_only_policy_registry_v1.py")],
            )
        )
    if not args.skip_ingest:
        steps.append(
            (
                "coverage_diff_complete",
                [
                    py,
                    str(ROOT / "scripts/build_logos_verse_canon_coverage_diff_v1.py"),
                    "--v2",
                    str(ROOT / "data/logos/verse_decoded_v2_complete_v1.jsonl"),
                    "--output",
                    str(
                        ROOT
                        / "reports/constitution/btrack_pilot/logos_verse_canon_coverage_diff_complete_v1_latest.json"
                    ),
                ],
            )
        )
        steps.append(
            ("single_anchor", [py, str(ROOT / "scripts/build_logos_verse_single_anchor_unified_v1.py")])
        )

    if not args.skip_rebuild:
        steps.append(
            (
                "corpus",
                [
                    py,
                    str(ROOT / "scripts/build_logos_verse_4d_corpus_v1.py"),
                    "--input-jsonl",
                    str(ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl"),
                    "--out-jsonl",
                    str(CORPUS),
                    "--out-manifest",
                    str(CORPUS_MANIFEST),
                ],
            )
        )
        steps.append(
            (
                "graph",
                [
                    py,
                    str(ROOT / "scripts/build_logos_verse_4d_graph_v1.py"),
                    "--input-jsonl",
                    str(CORPUS),
                    "--out-edges",
                    str(
                        ROOT
                        / "reports/constitution/btrack_pilot/logos_verse_4d_single_anchor_graph_edges_v1_latest.jsonl"
                    ),
                    "--out-medoids",
                    str(ROOT / "docs/final/artifacts/logos_verse_4d_single_anchor_medoids_v1_latest.json"),
                ],
            )
        )

    if not args.skip_ann:
        ann_cmd = [
            py,
            str(ROOT / "scripts/build_logos_vector_index_ann_lite_v1.py"),
            "--verse-json",
            str(CORPUS),
            "--max-verses",
            str(args.max_verses_ann),
        ]
        steps.append(("ann_lite", ann_cmd))

    if not args.skip_showroom:
        steps.append(
            (
                "showroom_b2b",
                [
                    py,
                    str(ROOT / "scripts/run_logos_verse_4d_showroom_b2b_chain_v1.py"),
                ],
            )
        )
        steps.append(
            (
                "showroom_slice_single_anchor",
                [
                    py,
                    str(ROOT / "scripts/build_logos_verse_4d_showroom_slice_v1.py"),
                    "--corpus",
                    str(CORPUS_MANIFEST),
                    "--medoids",
                    str(ROOT / "docs/final/artifacts/logos_verse_4d_single_anchor_medoids_v1_latest.json"),
                    "--coverage-diff",
                    str(
                        ROOT
                        / "reports/constitution/btrack_pilot/logos_verse_canon_coverage_diff_complete_v1_latest.json"
                    ),
                ],
            )
        )

    if not args.skip_multi_orbit:
        steps.append(
            (
                "multi_orbit",
                [
                    py,
                    str(ROOT / "scripts/run_logos_multi_orbit_chain_v1.py"),
                    "--include-satellite-dev",
                    "--full-nt-tr",
                ],
            )
        )

    for name, cmd in steps:
        print(f"[post-lexical] {name}", flush=True)
        rc = _run(cmd)
        if rc != 0:
            return rc
    print("[post-lexical] done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
