#!/usr/bin/env python3
"""Tranche-2 Qwen 7B 12-pack train ablation (MKM12 hier_12x75_hybrid lane).

B-track / research_only — distinct trained weights + attach latency for 12-pack lane.
Not Track A·live-trading GO. Follow-on after tranche-2 closure (TinyLlama 12-pack diversity).
"""

from __future__ import annotations

import atexit
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "reports/lora_tranche2_qwen12pack_v1/.qwen12pack_train_ablation.lock"


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _acquire_lock() -> None:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    if LOCK_PATH.is_file():
        try:
            old_pid = int(LOCK_PATH.read_text(encoding="utf-8").strip())
        except ValueError:
            old_pid = 0
        if _pid_alive(old_pid):
            raise SystemExit(
                f"qwen12pack ablation already running (pid={old_pid}). Lock: {LOCK_PATH}"
            )
        LOCK_PATH.unlink(missing_ok=True)
    LOCK_PATH.write_text(str(os.getpid()), encoding="utf-8")

    def _release() -> None:
        try:
            if LOCK_PATH.is_file() and LOCK_PATH.read_text(encoding="utf-8").strip() == str(
                os.getpid()
            ):
                LOCK_PATH.unlink(missing_ok=True)
        except OSError:
            pass

    atexit.register(_release)


def main() -> int:
    _acquire_lock()
    defaults = [
        "--train-steps",
        "8",
        "--rows-per-pack-cap",
        "40",
        "--eval-limit",
        "2",
        "--skip-if-adapter",
        "--skip-if-eval-report",
        "--shard-mode",
        "acode_state_deterministic_v1",
    ]
    cmd = [
        sys.executable,
        str(ROOT / "scripts/run_lora_tranche2_qwen4pack_train_ablation_v1.py"),
        "--pack-count",
        "12",
        "--architecture-target",
        "hier_12x75_hybrid",
        "--work-root",
        str(ROOT / "reports/lora_tranche2_qwen12pack_v1"),
        "--out-json",
        str(ROOT / "reports/lora_tranche2_qwen12pack_train_ablation_latest.json"),
        *defaults,
        *sys.argv[1:],
    ]
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
