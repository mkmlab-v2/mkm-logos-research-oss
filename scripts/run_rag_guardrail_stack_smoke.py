#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _run(cmd: str, cwd: Path) -> dict[str, Any]:
    t0 = time.perf_counter()
    p = subprocess.run(cmd, cwd=str(cwd), shell=True, capture_output=True, text=True)
    dt = time.perf_counter() - t0
    return {
        "command": cmd,
        "exit_code": p.returncode,
        "elapsed_sec": round(dt, 4),
        "stdout_tail": p.stdout[-800:],
        "stderr_tail": p.stderr[-800:],
        "ok": p.returncode == 0,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out = root / "reports" / "constitution" / "btrack_pilot" / "rag_guardrail_stack_smoke_latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    checks = [
        _run("python scripts/check_top_level_word_artifacts.py", root),
        _run("python scripts/enforce_backend_fact_engine_quantization_guard.py --scan-dir projects/bitcoin-trading/src --scan-dir scripts --skip-regex \"/scripts/run_rag_turboquant_poc_template.py\"", root),
        _run("python scripts/run_rag_turboquant_guarded_sweep.py --cwd . --runs 1", root),
        _run("python scripts/run_rag_turboquant_canary_monitor.py --cwd . --iterations 1 --interval-sec 0", root),
        _run("python scripts/run_vllm_ab_canary_repeat.py --base-url \"http://127.0.0.1:8000\" --baseline-model \"mkm12-lite\" --candidate-model \"mkm12-accelerated\" --runs 5 --allow-unavailable", root),
        _run("python scripts/emit_vllm_canary_rollback_flag.py", root),
    ]

    # Align smoke behavior with canary workflow:
    # always emit rollback-flag artifact before running the gate check.
    monitor_report = (
        root / "reports" / "constitution" / "btrack_pilot" / "rag_canary_monitor_latest.json"
    )
    rollback_flag = (
        root / "reports" / "constitution" / "btrack_pilot" / "rag_canary_rollback_flag_latest.json"
    )
    # If vLLM repeat already emitted rollback flag, keep it as authoritative for this smoke run.
    vllm_flag_emitted = False
    if rollback_flag.exists():
        try:
            flag_doc = json.loads(rollback_flag.read_text(encoding="utf-8"))
            reason = str(flag_doc.get("reason", ""))
            vllm_flag_emitted = reason.startswith("vllm_canary_")
        except Exception:
            vllm_flag_emitted = False
    if monitor_report.exists() and not vllm_flag_emitted:
        monitor_doc = json.loads(monitor_report.read_text(encoding="utf-8"))
        all_passed = bool(monitor_doc.get("guardrail_status", {}).get("all_passed", False))
        flag_doc = {
            "schema": "rag_turboquant_canary_rollback_flag_v1",
            "should_rollback": (not all_passed),
            "reason": "guardrail_failed" if not all_passed else "healthy",
            "source_report": "reports/constitution/btrack_pilot/rag_canary_monitor_latest.json",
        }
        rollback_flag.write_text(json.dumps(flag_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    checks.append(_run("python scripts/check_rag_canary_rollback_flag.py", root))

    overall_ok = all(c["ok"] for c in checks)
    payload = {
        "schema": "rag_guardrail_stack_smoke_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "overall_ok": overall_ok,
        "checks": checks,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out}")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
