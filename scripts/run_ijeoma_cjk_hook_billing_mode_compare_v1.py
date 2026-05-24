#!/usr/bin/env python3
"""[HYPO] Compare operational hook (ascii_compact) vs billing hook (o200k_tight) — B-track only."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PILOT = ROOT / "reports/constitution/btrack_pilot"
CHUNK_TABLE = ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_table_v1.json"
BILLING_LANE = ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_cjk_o200k_tight_v1.json"
OUT = PILOT / "comp_ijeoma_cjk_hook_billing_mode_compare_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _sweep_mean(path: Path) -> float | None:
    doc = _load(path)
    if not doc:
        return None
    return (doc.get("profiles") or {}).get("economy", {}).get("mean")


def _run_py(script: str, *argv: str) -> int:
    cmd = [sys.executable, str(ROOT / script), *argv]
    proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
    return int(proc.returncode)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-cases", type=int, default=0, help="0 = all (parity uses full lane).")
    ap.add_argument("--skip-sweeps", action="store_true", help="Only parity + read existing sweep JSON.")
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    out_path = (ROOT / args.out_json).resolve() if not args.out_json.is_absolute() else args.out_json
    max_arg = ["--max-cases", str(args.max_cases)] if args.max_cases > 0 else []

    parity_ops = PILOT / "comp_ijeoma_cjk_bridge_vs_eval_hook_ascii_compact_v1.json"
    parity_bill = PILOT / "comp_ijeoma_cjk_bridge_vs_eval_hook_o200k_tight_v1.json"
    hook_ops = PILOT / "comp_universal_bench_matrix_sweep_ijeoma_chunk_eval_hook_ascii_compact_v1.json"
    hook_bill = PILOT / "comp_universal_bench_matrix_sweep_ijeoma_chunk_eval_hook_o200k_tight_v1.json"
    lane_bill_sweep = PILOT / "comp_universal_bench_matrix_sweep_ijeoma_chunk_cjk_o200k_tight_v1.json"

    steps: list[dict[str, Any]] = []

    if not args.skip_sweeps:
        rc = _run_py(
            "scripts/compare_ijeoma_cjk_bridge_vs_eval_hook_v1.py",
            "--marker-strategy",
            "ascii_compact",
            "--out-json",
            str(parity_ops.relative_to(ROOT)).replace("\\", "/"),
            *max_arg,
        )
        steps.append({"step": "parity_ascii_compact", "exit_code": rc})
        if rc != 0:
            print(json.dumps({"error": "parity_ascii_compact_failed", "exit_code": rc}, ensure_ascii=False))
            return rc

        rc = _run_py(
            "scripts/compare_ijeoma_cjk_bridge_vs_eval_hook_v1.py",
            "--marker-strategy",
            "o200k_tight",
            "--out-json",
            str(parity_bill.relative_to(ROOT)).replace("\\", "/"),
            *max_arg,
        )
        steps.append({"step": "parity_o200k_tight", "exit_code": rc})
        if rc != 0:
            print(json.dumps({"error": "parity_o200k_tight_failed", "exit_code": rc}, ensure_ascii=False))
            return rc

        env_ops = {**os.environ, "MKM_IJEOMA_CJK_MARKER_STRATEGY": "ascii_compact"}
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/run_universal_compression_bench_matrix_sweep_v1.py"),
                "--input",
                str(CHUNK_TABLE.relative_to(ROOT)).replace("\\", "/"),
                "--out-json",
                str(hook_ops.relative_to(ROOT)).replace("\\", "/"),
                "--eval-report-cjk-hook",
            ],
            cwd=str(ROOT),
            env=env_ops,
            check=False,
        )
        steps.append({"step": "hook_sweep_ascii_compact", "exit_code": proc.returncode})

        proc2 = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/run_universal_compression_bench_matrix_sweep_v1.py"),
                "--input",
                str(CHUNK_TABLE.relative_to(ROOT)).replace("\\", "/"),
                "--out-json",
                str(hook_bill.relative_to(ROOT)).replace("\\", "/"),
                "--eval-report-cjk-hook",
            ],
            cwd=str(ROOT),
            env={**os.environ, "MKM_IJEOMA_CJK_MARKER_STRATEGY": "o200k_tight"},
            check=False,
        )
        steps.append({"step": "hook_sweep_o200k_tight", "exit_code": proc2.returncode})

    p_ops = _load(parity_ops)
    p_bill = _load(parity_bill)
    diag_tight = _load(PILOT / "comp_ijeoma_cjk_o200k_diagnosis_o200k_tight_v1.json")

    out = {
        "schema": "comp_ijeoma_cjk_hook_billing_mode_compare_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "operational_hook": {
            "marker_strategy": "ascii_compact",
            "env_default": "MKM_IJEOMA_CJK_MARKER_STRATEGY=ascii_compact",
            "parity_ok": (p_ops or {}).get("parity_ok"),
            "hook_sweep_mean_proxy_90": _sweep_mean(hook_ops),
            "corpus_o200k_from_diagnosis": None,
        },
        "billing_hook_experiment": {
            "marker_strategy": "o200k_tight",
            "activate_via": "MKM_IJEOMA_CJK_MARKER_STRATEGY=o200k_tight (hook) OR billing lane file on disk",
            "parity_ok": (p_bill or {}).get("parity_ok"),
            "hook_sweep_mean_proxy_90": _sweep_mean(hook_bill),
            "billing_lane_baseline_sweep_mean": _sweep_mean(lane_bill_sweep),
            "corpus_o200k_tight_90": (diag_tight or {}).get("corpus_o200k_saving_rate"),
        },
        "alignment": {
            "hook_o200k_matches_billing_lane_sweep": (
                _sweep_mean(hook_bill) is not None
                and _sweep_mean(lane_bill_sweep) is not None
                and abs(float(_sweep_mean(hook_bill)) - float(_sweep_mean(lane_bill_sweep))) < 1e-6
            ),
            "note": "If true, on-the-fly hook with o200k_tight matches pre-materialized billing lane.",
        },
        "do_not_promote": [
            "Not Track A 47.5%",
            "Do not merge billing o200k % into MS-PASTE Golden headline",
        ],
        "steps": steps,
        "artifacts": {
            "parity_ascii_compact": str(parity_ops.relative_to(ROOT)).replace("\\", "/"),
            "parity_o200k_tight": str(parity_bill.relative_to(ROOT)).replace("\\", "/"),
            "hook_sweep_ascii_compact": str(hook_ops.relative_to(ROOT)).replace("\\", "/"),
            "hook_sweep_o200k_tight": str(hook_bill.relative_to(ROOT)).replace("\\", "/"),
            "billing_lane": str(BILLING_LANE.relative_to(ROOT)).replace("\\", "/"),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": out_path.name,
                "parity_ops": out["operational_hook"]["parity_ok"],
                "parity_billing": out["billing_hook_experiment"]["parity_ok"],
                "hook_aligned": out["alignment"]["hook_o200k_matches_billing_lane_sweep"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
