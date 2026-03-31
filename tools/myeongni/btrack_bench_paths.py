"""Workspace-relative paths for B-track pilot bench JSONL outputs.

Canonical slot (``a_track_eval.jsonl`` / ``b_track_eval.jsonl``) is reserved for
the SSOT builder listed in ``CANONICAL_BENCH_POINTER_V1.json``. Other builders
default to suffixed filenames so they do not silently overwrite downstream inputs.
"""

from __future__ import annotations

from pathlib import Path

BENCH_DIR = Path("data") / "logos" / "btrack_pilot" / "bench"

# Downstream: recalibrate_worst5, collect_btrack_quality_metrics, build_candidate_subset, etc.
CANONICAL_A_TRACK_EVAL = BENCH_DIR / "a_track_eval.jsonl"
CANONICAL_B_TRACK_EVAL = BENCH_DIR / "b_track_eval.jsonl"

# build_btrack_bench_from_direct_logs.py defaults
DIRECT_A_TRACK_EVAL = BENCH_DIR / "a_track_eval_direct_v1.jsonl"
DIRECT_B_TRACK_EVAL = BENCH_DIR / "b_track_eval_direct_v1.jsonl"

# bootstrap_btrack_bench_from_cross_ref.py defaults
CROSS_REF_BOOTSTRAP_A_TRACK_EVAL = BENCH_DIR / "a_track_eval_cross_ref_bootstrap_v1.jsonl"
CROSS_REF_BOOTSTRAP_B_TRACK_EVAL = BENCH_DIR / "b_track_eval_cross_ref_bootstrap_v1.jsonl"

CANONICAL_BENCH_POINTER = BENCH_DIR / "CANONICAL_BENCH_POINTER_V1.json"
MANSERYEOK_SCOPE_MANIFEST = BENCH_DIR / "BENCH_MANSERYEOK_SCOPE_MANIFEST_V1.json"
