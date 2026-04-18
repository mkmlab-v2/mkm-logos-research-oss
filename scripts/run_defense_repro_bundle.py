#!/usr/bin/env python3
"""One-shot reproducibility bundle for defense benches (hybrid UAV + bridge A/B + snapshot + briefing + pitch JSON + code pack check).

Optional: L1 inverse decoder sweep (slow) via --l1-sweep; pytest regression via --pytest;
second hybrid run (main+stress → merged JSON) via --merged-hybrid.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _defense_pytest_paths() -> list[str]:
    paths = sorted((ROOT / "tests").glob("test_defense_*.py"))
    return [str(p) for p in paths]


def _run(label: str, args: list[str]) -> None:
    print(f"--- {label} ---", flush=True)
    subprocess.run([sys.executable, *args], check=True, cwd=str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description="Defense benchmark reproducibility bundle.")
    ap.add_argument(
        "--skip-all-modes-bridge",
        action="store_true",
        help="Skip run_multilens_bridge_policy_ab.py --all-modes (saves time).",
    )
    ap.add_argument(
        "--l1-sweep",
        action="store_true",
        help="Run L1 inverse decoder multi-seed sweep (slow).",
    )
    ap.add_argument(
        "--pytest",
        action="store_true",
        help="After --check, run pytest tests/test_defense_*.py (stress + artifact schemas).",
    )
    ap.add_argument(
        "--skip-pitch",
        action="store_true",
        help="Skip build_defense_codepack.py (defense_pitch_codepack_v1.json refresh).",
    )
    ap.add_argument(
        "--merged-hybrid",
        action="store_true",
        help="After the default hybrid bench, run again with --append-stress (→ defense_hybrid_compression_bench_merged_v0.json).",
    )
    args = ap.parse_args()

    _run("hybrid UAV bench", [str(ROOT / "scripts" / "run_defense_hybrid_compression_bench.py")])
    if args.merged_hybrid:
        _run(
            "hybrid UAV bench (merged + stress)",
            [
                str(ROOT / "scripts" / "run_defense_hybrid_compression_bench.py"),
                "--append-stress",
            ],
        )
    if not args.skip_all_modes_bridge:
        _run("bridge A/B all modes", [str(ROOT / "scripts" / "run_multilens_bridge_policy_ab.py"), "--all-modes"])
    _run("single-mode bridge summary (ultra-literal)", [str(ROOT / "scripts" / "run_multilens_bridge_policy_ab.py")])
    _run("Track A universal refresh", [
        str(ROOT / "scripts" / "run_ultra_compression_default.py"),
        "--mode",
        "universal",
        "--out",
        str(ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"),
    ])
    _run("snapshot table", [str(ROOT / "scripts" / "build_defense_bench_snapshot_table.py")])
    _run("briefing bullets", [str(ROOT / "scripts" / "build_defense_bench_briefing_bullets.py")])
    if not args.skip_pitch:
        _run("pitch codepack", [str(ROOT / "scripts" / "build_defense_codepack.py")])
    if args.l1_sweep:
        _run("L1 spike sweep", [str(ROOT / "scripts" / "run_l1_inverse_decoder_spike_test.py"), "--sweep"])
    _run("code pack check", [str(ROOT / "scripts" / "defense_code_pack_v1.py"), "--check"])
    if args.pytest:
        defense_tests = _defense_pytest_paths()
        if not defense_tests:
            print("ERROR: no tests/test_defense_*.py files found", file=sys.stderr)
            return 4
        print("--- pytest defense regression ---", flush=True)
        subprocess.run(
            [sys.executable, "-m", "pytest", *defense_tests, "-q", "--tb=short"],
            check=True,
            cwd=str(ROOT),
        )
    print("OK: defense repro bundle complete.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
