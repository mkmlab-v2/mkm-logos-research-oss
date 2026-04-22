# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.84, L:0.88, K:0.55, M:0.42}
# Balance: 90
# Purpose: Build unified benchmark bundle for cpu/numba/cuda engine comparisons
# Keywords: benchmark, gpu, cuda, numba, backtest, sweep
#!/usr/bin/env python3
"""Run GPU-capable benchmark scripts and aggregate engine performance."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "gpu_engine_benchmark_bundle_v1_latest.json"
BTC_SCRIPT = ROOT / "scripts" / "run_btc_time_machine_fact_safe_backtest.py"
PROPHECY_SCRIPT = ROOT / "scripts" / "run_prophecy_instrument_combo_sweep_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_script(script: Path, args: list[str]) -> dict[str, Any]:
    cmd = [sys.executable, str(script), *args]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"script failed: {script.name}\n"
            f"exit={proc.returncode}\n"
            f"stdout={proc.stdout}\n"
            f"stderr={proc.stderr}"
        )
    return {"stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_summary(doc: dict[str, Any]) -> dict[str, Any]:
    perf = doc.get("performance", {}) if isinstance(doc.get("performance"), dict) else {}
    engine = doc.get("engine", {}) if isinstance(doc.get("engine"), dict) else {}
    return {
        "engine": engine,
        "performance": {
            "elapsed_ms": perf.get("elapsed_ms"),
            "bars_per_sec": perf.get("bars_per_sec"),
            "candidates_per_sec": perf.get("candidates_per_sec"),
            "benchmark_all_engines": perf.get("benchmark_all_engines"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build unified CPU/Numba/CUDA benchmark bundle.")
    ap.add_argument("--btc-start", default="2026-03-20")
    ap.add_argument("--btc-end", default="2026-04-18")
    ap.add_argument("--prophecy-top-k", type=int, default=5)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    with tempfile.TemporaryDirectory(prefix="gpu-benchmark-bundle-") as td:
        tmp_dir = Path(td)
        btc_out = tmp_dir / "btc_benchmark.json"
        prophecy_out = tmp_dir / "prophecy_benchmark.json"

        btc_log = _run_script(
            BTC_SCRIPT,
            [
                "--engine",
                "cuda",
                "--benchmark-all-engines",
                "--start",
                args.btc_start,
                "--end",
                args.btc_end,
                "--output",
                str(btc_out),
            ],
        )
        prophecy_log = _run_script(
            PROPHECY_SCRIPT,
            [
                "--engine",
                "cuda",
                "--benchmark-all-engines",
                "--top-k",
                str(args.prophecy_top_k),
                "--output",
                str(prophecy_out),
            ],
        )

        btc_doc = _read_json(btc_out)
        prophecy_doc = _read_json(prophecy_out)

    bundle = {
        "schema": "gpu_engine_benchmark_bundle_v1",
        "generated_at_utc": _utc_now(),
        "inputs": {
            "btc_start": args.btc_start,
            "btc_end": args.btc_end,
            "prophecy_top_k": args.prophecy_top_k,
        },
        "runs": {
            "btc_time_machine_fact_safe_backtest": {
                **_extract_summary(btc_doc),
                "stdout": btc_log["stdout"],
            },
            "prophecy_instrument_combo_sweep_v1": {
                **_extract_summary(prophecy_doc),
                "stdout": prophecy_log["stdout"],
            },
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.output.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
