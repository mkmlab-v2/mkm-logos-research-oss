#!/usr/bin/env python3
"""Run dual-probe 4-agent ablation per register + compare report [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
REGISTER = ROOT / "docs/final/artifacts/sasang_4agent_dual_probe_ablation_register_v1.json"
OUT = ROOT / "reports/sasang_4agent_dual_probe_ablation_v1_latest.json"
REAL_SLICE_OUT = ROOT / "docs/final/artifacts/sasang_4agent_collision_btrack_protocol_real_slice_latest.json"
TIMESERIES_OUT = ROOT / "docs/final/artifacts/sasang_4agent_collision_btrack_protocol_timeseries_kospi_latest.json"
KOSPI_CSV = ROOT / "data/myeongni/sasang_kospi_proxy_timeseries_btrack_v1.csv"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--register", type=Path, default=REGISTER)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    reg = _load(args.register) if args.register.is_file() else {}
    steps: list[dict[str, Any]] = []

    for name, extra in (
        (
            "DP01_real_slice",
            ["--use-real-slice", "--out-json", str(REAL_SLICE_OUT), "--bootstrap-trials", "200"],
        ),
        (
            "DP02_timeseries_kospi",
            [
                "--use-timeseries-file",
                "--timeseries-file",
                str(KOSPI_CSV),
                "--out-json",
                str(TIMESERIES_OUT),
                "--bootstrap-trials",
                "200",
            ],
        ),
    ):
        t0 = time.perf_counter()
        cmd = [PY, str(ROOT / "scripts/run_sasang_4agent_collision_btrack_protocol_v1.py")] + extra
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        steps.append(
            {
                "probe_id": name,
                "exit_code": proc.returncode,
                "elapsed_sec": round(time.perf_counter() - t0, 2),
                "ok": proc.returncode == 0,
            }
        )
        if proc.returncode != 0:
            break

    compare_ok = False
    if all(s["ok"] for s in steps):
        t0 = time.perf_counter()
        proc = subprocess.run(
            [PY, str(ROOT / "scripts/build_sasang_4agent_dual_probe_compare_report_v1.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        compare_ok = proc.returncode == 0
        steps.append(
            {
                "probe_id": "compare",
                "exit_code": proc.returncode,
                "elapsed_sec": round(time.perf_counter() - t0, 2),
                "ok": compare_ok,
            }
        )

    compare = {}
    compare_path = ROOT / "reports/sasang_4agent_dual_probe_compare_v1_latest.json"
    if compare_path.is_file():
        compare = _load(compare_path)

    doc = {
        "schema": "sasang_4agent_dual_probe_ablation_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "register_path": str(args.register.resolve()).replace("\\", "/"),
        "rq_id": reg.get("rq_id"),
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "compare_ok": compare.get("compare_ok"),
        "delta_mdd": (compare.get("delta") or {}).get("mdd_reduction_abs_timeseries_minus_real_slice"),
        "reproduce": "py scripts/run_sasang_4agent_dual_probe_ablation_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_ok"], "compare_ok": doc.get("compare_ok")}))
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
