#!/usr/bin/env python3
"""Ops dynamical L3 — cross-fixture dual-plane isomorphism eval [HYPO · B-track]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ops_dynamical_bench_v1_lib import (  # noqa: E402
    DEFAULT_OUT,
    L3_BENCH_RUNNERS,
    L3_DOMAIN_PATHS,
    build_report,
    eval_l3_cross_fixture,
    load_l3_profiles,
)

OUT = ROOT / "reports/ops_dynamical_l3_eval_v1_latest.json"


def _ensure_artifacts() -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    # ops snapshot
    bench = build_report(fractal_level="L3_cross_domain")
    DEFAULT_OUT.write_text(json.dumps(bench, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    steps.append({"target": "ops_agent", "ok": True, "action": "build_report"})

    for domain_id, rel_script in L3_BENCH_RUNNERS.items():
        script = ROOT / rel_script
        if not script.is_file():
            steps.append({"target": domain_id, "ok": False, "error": "runner_missing"})
            continue
        proc = subprocess.run([sys.executable, str(script)], cwd=str(ROOT), capture_output=True, text=True)
        steps.append(
            {
                "target": domain_id,
                "ok": proc.returncode == 0,
                "exit_code": proc.returncode,
                "tail": (proc.stdout or proc.stderr or "").strip().splitlines()[-1:] or [],
            }
        )
    return steps


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate L3 cross-fixture dual-plane isomorphism")
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--ensure-artifacts", action="store_true", help="run missing dual-plane benches + ops bench")
    args = parser.parse_args()

    ensure_steps: list[dict[str, Any]] = []
    if args.ensure_artifacts:
        ensure_steps = _ensure_artifacts()

    profiles, missing = load_l3_profiles(L3_DOMAIN_PATHS)
    doc = eval_l3_cross_fixture(profiles, missing=missing)
    if ensure_steps:
        doc["ensure_artifacts_steps"] = ensure_steps

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["ok"],
                "out": str(args.out),
                "isomorphism_score": doc["metrics"]["isomorphism_score"],
                "checks_pass_count": doc["checks_pass_count"],
            }
        )
    )
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
