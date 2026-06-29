#!/usr/bin/env python3
"""[HYPO] Main-side: workspace bundle → aux sync → fresh shard1 → distributed merge."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/nextgen_aux_workspace_sync_and_shard_chain_v1_latest.json"
SHARE = Path("Z:/nextgen_cpu_aux")
STAMP = SHARE / "ng40_shard1_publish_from_main_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(script: str, extra: list[str] | None = None, timeout_s: int = 900) -> dict[str, Any]:
    cmd = [sys.executable, str(ROOT / script), *(extra or [])]
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout_s)
        tail = (proc.stdout or "").strip().splitlines()
        parsed: Any = None
        if tail:
            try:
                parsed = json.loads(tail[-1])
            except json.JSONDecodeError:
                parsed = tail[-1][:400]
        return {
            "script": script,
            "args": extra or [],
            "exit_code": int(proc.returncode),
            "parsed": parsed,
        }
    except subprocess.TimeoutExpired:
        return {"script": script, "args": extra or [], "exit_code": 124, "timed_out": True}


def _run_ps1(name: str, extra: list[str] | None = None) -> dict[str, Any]:
    path = ROOT / "scripts" / name
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(path), *(extra or [])],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=900,
    )
    return {"script": name, "args": extra or [], "exit_code": int(proc.returncode)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wait-sec", type=int, default=180)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    if STAMP.is_file():
        try:
            STAMP.unlink()
        except OSError:
            pass

    steps.append(_run("scripts/build_nextgen_aux_workspace_bundle_v1.py"))
    steps.append(
        _run(
            "scripts/deploy_nextgen_clean_slate_cpu_aux_drop_v1.py",
            ["--share-root", str(SHARE), "--merge-only"],
            120,
        )
    )
    steps.append(
        _run_ps1(
            "Invoke-NextGenAuxAutomation_v1.ps1",
            ["-UseAux", "-WaitSec", str(args.wait_sec)],
        )
    )
    steps.append(_run("scripts/run_nextgen_ng40_golden40_distributed_chain_v1.py", ["--skip-shard0"]))
    steps.append(_run("scripts/run_nextgen_golden40_distributed_readiness_v1.py"))

    merged = ROOT / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_golden40_merged_v1_latest.json"
    aux_result = SHARE / "aux_job_result_v1_latest.json"
    shard1_aux = SHARE / "ng40_golden40_shard1_v1_latest.json"

    aux_doc: dict[str, Any] | None = None
    if aux_result.is_file():
        try:
            aux_doc = json.loads(aux_result.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            aux_doc = None

    merged_doc: dict[str, Any] | None = None
    if merged.is_file():
        merged_doc = json.loads(merged.read_text(encoding="utf-8-sig"))

    shard1_fresh = bool(
        aux_doc
        and (aux_doc.get("ng40_shard1") or {}).get("status") == "ok"
        and not STAMP.is_file()
    )

    manifest = {
        "schema": "nextgen_aux_workspace_sync_and_shard_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "steps": steps,
        "shard1_fresh_from_aux": shard1_fresh,
        "publish_stamp_absent": not STAMP.is_file(),
        "aux_ng40_shard1": (aux_doc or {}).get("ng40_shard1"),
        "merged_beat_frozen": (merged_doc or {}).get("beat_check", {}).get("beat_frozen"),
        "merged_aggregate": (merged_doc or {}).get("aggregate"),
        "forbidden": ["--apply-active"],
        "reproducible_command": (
            "py scripts/run_nextgen_aux_workspace_sync_and_shard_chain_v1.py --wait-sec 180"
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    hard_fail = any(s.get("exit_code") not in (0, None) for s in steps)
    print(
        json.dumps(
            {
                "wrote": str(OUT),
                "hard_fail": hard_fail,
                "shard1_fresh_from_aux": shard1_fresh,
                "beat_frozen": manifest["merged_beat_frozen"],
            },
            ensure_ascii=False,
        )
    )
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
