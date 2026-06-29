#!/usr/bin/env python3
"""[HYPO] Run Step1 codec bench split then Step2 Path A product sign-off (ordered)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/ng40_sequential_codec_product_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(script: str, extra: list[str] | None = None) -> int:
    cmd = [sys.executable, str(ROOT / script), *(extra or [])]
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-path-b-sweep", action="store_true")
    ap.add_argument("--skip-auto-ops", action="store_true")
    args = ap.parse_args()

    extra1 = ["--skip-path-b-sweep"] if args.skip_path_b_sweep else []
    rc1 = _run("scripts/run_ng40_codec_bench_split_chain_v1.py", extra1)
    extra2 = ["--skip-auto-ops"] if args.skip_auto_ops else []
    rc2 = _run("scripts/run_ng40_path_a_product_signoff_chain_v1.py", extra2) if rc1 == 0 else 99

    doc = {
        "schema": "ng40_sequential_codec_product_chain_v1",
        "generated_at_utc": _utc(),
        "step1_exit_code": rc1,
        "step2_exit_code": rc2,
        "manifests": [
            "experiments/nextgen_clean_slate_cpu_v1/results/ng40_codec_bench_split_manifest_v1_latest.json",
            "reports/ng40_path_a_product_signoff_chain_v1_latest.json",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), **doc}, ensure_ascii=False))
    return 0 if rc1 == 0 and rc2 == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
