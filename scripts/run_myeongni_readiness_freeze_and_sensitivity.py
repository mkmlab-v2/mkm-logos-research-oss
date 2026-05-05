#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
FREEZE_ROOT = ART / "freeze"

TARGET_FILES = [
    "myeongni_independent_lens_latest.json",
    "independent_lens_fusion_stub_latest.json",
    "independent_lens_shadow_gate_latest.json",
    "myeongni_eval_contract_latest.json",
    "myeongni_16state_data_quality_report_latest.json",
    "myeongni_commercialization_readiness_packet_latest.json",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(cmd: list[str]) -> int:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if cp.returncode != 0:
        sys.stderr.write(cp.stdout)
        sys.stderr.write(cp.stderr)
    return cp.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="Freeze readiness evidence and run threshold sensitivity.")
    ap.add_argument("--thresholds", nargs="*", type=float, default=[0.005, 0.01, 0.02])
    args = ap.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    freeze_dir = FREEZE_ROOT / f"myeongni_readiness_{stamp}"
    freeze_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: freeze current latest artifacts.
    copied: list[dict[str, Any]] = []
    for name in TARGET_FILES:
        src = ART / name
        if not src.is_file():
            continue
        dst = freeze_dir / name
        dst.write_bytes(src.read_bytes())
        copied.append(
            {
                "file": name,
                "source_path": str(src.resolve()),
                "freeze_path": str(dst.resolve()),
                "sha256": _sha256(dst),
            }
        )

    # Step 2: no-backfill rerun validation.
    no_backfill_cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "scripts/run_myeongni_shadow_monthly_catchup_v1.ps1",
    ]
    no_backfill_exit = _run(no_backfill_cmd)

    # Step 3: readiness sensitivity sweep.
    sweep_rows: list[dict[str, Any]] = []
    for th in args.thresholds:
        exit_code = _run(
            [
                sys.executable,
                "scripts/build_myeongni_commercialization_readiness_packet.py",
                "--max-shadow-override-ratio",
                str(th),
            ]
        )
        packet = _read_json(ART / "myeongni_commercialization_readiness_packet_latest.json")
        summary = packet.get("summary") if isinstance(packet.get("summary"), dict) else {}
        sweep_rows.append(
            {
                "threshold": th,
                "exit_code": exit_code,
                "readiness": packet.get("readiness"),
                "shadow_override_ratio": summary.get("shadow_override_ratio"),
                "shadow_override_ratio_exceeded": summary.get("shadow_override_ratio_exceeded"),
            }
        )

    # restore canonical threshold
    _run(
        [
            sys.executable,
            "scripts/build_myeongni_commercialization_readiness_packet.py",
            "--max-shadow-override-ratio",
            "0.01",
        ]
    )

    report = {
        "schema": "myeongni_readiness_freeze_and_sensitivity_v1",
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "freeze_dir": str(freeze_dir.resolve()),
        "frozen_files": copied,
        "no_backfill_validation": {
            "command": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_myeongni_shadow_monthly_catchup_v1.ps1",
            "exit_code": no_backfill_exit,
        },
        "sensitivity_sweep": sweep_rows,
        "note": "Track B observation evidence freeze; no auto-promotion to Track A/live.",
    }
    out_path = ART / "myeongni_readiness_sensitivity_report_latest.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
