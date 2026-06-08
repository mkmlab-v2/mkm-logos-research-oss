#!/usr/bin/env python3
"""Run all three A2A target-point pilots and refresh SSOT summary.

[HYPO] / research_only / B-track.

  py scripts/build_a2a_target_points_pilot_bundle_v1.py
  py scripts/build_a2a_target_points_pilot_bundle_v1.py --strict-exit --include-pytest
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "docs/final/artifacts/a2a_target_points_pilot_bundle_v1_latest.json"
TARGET_POINTS = ROOT / "docs/final/artifacts/a2a_target_points_v1_latest.json"

PILOT_STEPS: list[dict[str, str]] = [
    {
        "id": "tp01",
        "script": "scripts/build_mkm_chat_resume_a2a_pilot_v1.py",
        "artifact": "docs/final/artifacts/mkm_chat_resume_a2a_pilot_v1_latest.json",
    },
    {
        "id": "tp02",
        "script": "scripts/build_a2a_tp02_lexicon_dense_bench_v1.py",
        "artifact": "docs/final/artifacts/a2a_tp02_lexicon_dense_bench_v1_latest.json",
        "extra_args": "--strict-exit",
    },
    {
        "id": "tp03",
        "script": "scripts/build_a2a_tp03_chain_ref_pilot_v1.py",
        "artifact": "docs/final/artifacts/a2a_tp03_chain_ref_pilot_v1_latest.json",
        "extra_args": "--strict-exit",
    },
]

PYTEST_PATHS = [
    "tests/test_build_mkm_chat_resume_a2a_pilot_v1.py",
    "tests/test_build_a2a_tp02_lexicon_dense_bench_v1.py",
    "tests/test_build_a2a_tp03_chain_ref_pilot_v1.py",
    "tests/test_build_a2a_target_points_v1.py",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run_py(script: str, *extra: str) -> tuple[int, str]:
    cmd = [sys.executable, script, *extra]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _kpi_from_artifacts(root: Path) -> dict[str, Any]:
    tp01 = _read_json(root / "docs/final/artifacts/mkm_chat_resume_a2a_pilot_v1_latest.json") or {}
    tp02 = _read_json(root / "docs/final/artifacts/a2a_tp02_lexicon_dense_bench_v1_latest.json") or {}
    tp03 = _read_json(root / "docs/final/artifacts/a2a_tp03_chain_ref_pilot_v1_latest.json") or {}
    c1 = tp01.get("compress_result") or {}
    m1 = c1.get("compression_metrics") or {}
    h2 = tp02.get("kpi_headline") or {}
    a3 = tp03.get("aggregate_pointer_vs_full") or {}
    return {
        "tp01_resume_compress_savings_ratio": m1.get("savings_ratio"),
        "tp01_decision": c1.get("decision"),
        "tp02_mock_avg_savings_ratio": h2.get("mock_avg_savings_ratio"),
        "tp02_wire_env_vs_packet": h2.get("wire_avg_envelope_vs_packet_savings"),
        "tp03_reduction_percent_pointer_vs_full": a3.get("reduction_percent"),
        "tp03_tokens_saved_sum": a3.get("tokens_saved_sum"),
    }


def run_bundle(
    *,
    include_slice: bool = False,
    slice_max_chars: int = 1200,
    include_pytest: bool = False,
    strict_exit: bool = False,
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    all_ok = True

    for spec in PILOT_STEPS:
        extra = []
        extra_args = spec.get("extra_args") or ""
        if extra_args:
            extra.extend(extra_args.split())
        if spec["id"] == "tp01" and include_slice:
            extra.extend(["--include-slice", "--slice-max-chars", str(slice_max_chars)])
        code, log_tail = _run_py(spec["script"], *extra)
        ok = code == 0
        all_ok = all_ok and ok
        steps.append(
            {
                "id": spec["id"],
                "script": spec["script"],
                "exit_code": code,
                "ok": ok,
                "artifact": spec["artifact"],
                "log_tail": log_tail.splitlines()[-3:] if log_tail else [],
            }
        )
        if strict_exit and not ok:
            break

    if all_ok or not strict_exit:
        code, log_tail = _run_py("scripts/build_a2a_target_points_v1.py", "--strict-exit")
        ok = code == 0
        all_ok = all_ok and ok
        steps.append(
            {
                "id": "target_points_ssot",
                "script": "scripts/build_a2a_target_points_v1.py",
                "exit_code": code,
                "ok": ok,
                "artifact": str(TARGET_POINTS.relative_to(ROOT)).replace("\\", "/"),
                "log_tail": log_tail.splitlines()[-3:] if log_tail else [],
            }
        )

    pytest_row: dict[str, Any] | None = None
    if include_pytest and (all_ok or not strict_exit):
        cmd = [sys.executable, "-m", "pytest", *PYTEST_PATHS, "-q", "--tb=short"]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        ok = proc.returncode == 0
        all_ok = all_ok and ok
        pytest_row = {
            "exit_code": proc.returncode,
            "ok": ok,
            "paths": PYTEST_PATHS,
            "log_tail": ((proc.stdout or "") + (proc.stderr or "")).splitlines()[-5:],
        }

    target_doc = _read_json(TARGET_POINTS) or {}
    return {
        "schema": "a2a_target_points_pilot_bundle_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": "[HYPO] A2A tp01–tp03 pilot bundle. Not Track A SLA. No live trading.",
        "bundle_ok": all_ok,
        "final_action": target_doc.get("final_action"),
        "target_points_status": target_doc.get("status"),
        "options": {
            "include_slice": include_slice,
            "slice_max_chars": slice_max_chars if include_slice else None,
            "include_pytest": include_pytest,
        },
        "steps": steps,
        "pytest": pytest_row,
        "kpi_headline": _kpi_from_artifacts(ROOT),
        "evidence_paths": [
            "scripts/build_a2a_target_points_pilot_bundle_v1.py",
            "scripts/Invoke-A2aTargetPointsPilotBundle_v1.ps1",
            "docs/final/artifacts/a2a_target_points_v1_latest.json",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--include-slice", action="store_true", help="tp01 with --include-slice")
    ap.add_argument("--slice-max-chars", type=int, default=1200)
    ap.add_argument("--include-pytest", action="store_true")
    ap.add_argument("--strict-exit", action="store_true")
    args = ap.parse_args()

    doc = run_bundle(
        include_slice=args.include_slice,
        slice_max_chars=args.slice_max_chars,
        include_pytest=args.include_pytest,
        strict_exit=args.strict_exit,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"bundle_ok={doc.get('bundle_ok')} final_action={doc.get('final_action')}")
    kpi = doc.get("kpi_headline") or {}
    print(
        f"tp01_savings={kpi.get('tp01_resume_compress_savings_ratio')} "
        f"tp03_reduction={kpi.get('tp03_reduction_percent_pointer_vs_full')}%"
    )
    if args.strict_exit and not doc.get("bundle_ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
