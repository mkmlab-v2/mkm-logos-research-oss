#!/usr/bin/env python3
"""Phase L — Ollama themed deep push (when up) + Phase K closure (graph_paths + MS bundle)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
REPORTS = ROOT / "reports"
OUT_DEFAULT = REPORTS / "logos_track_b_phase_l_v1_latest.json"
SMOKE_PATH = REPORTS / "ollama_local_smoke_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, timeout: int = 3600) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-300:],
        "ok": proc.returncode == 0,
    }


def _smoke_fresh(max_age_sec: int = 3600) -> bool:
    if not SMOKE_PATH.is_file():
        return False
    try:
        doc = json.loads(SMOKE_PATH.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return False
    if doc.get("ok") is not True:
        return False
    ts = doc.get("generated_at_utc") or ""
    try:
        then = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - then).total_seconds()
        return age <= max_age_sec
    except ValueError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--skip-ollama", action="store_true")
    ap.add_argument("--reuse-ollama-smoke", action="store_true")
    ap.add_argument("--skip-phase-j", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    ollama_ok = False
    deep_push_ok: bool | None = None

    if args.skip_ollama:
        steps.append({"name": "ollama_skipped_flag", "ok": True, "note": "--skip-ollama"})
    elif args.reuse_ollama_smoke and _smoke_fresh():
        ollama_ok = True
        steps.append({"name": "ollama_smoke_reused", "ok": True, "path": str(SMOKE_PATH)})
    else:
        smoke = _run("ollama_smoke", [PY, "scripts/ollama_local_smoke_v1.py"], timeout=180)
        steps.append(smoke)
        ollama_ok = smoke.get("ok", False)

    if ollama_ok and not args.skip_ollama:
        os.environ["MKM_LOGOS_LLM_DISTILL_ENABLE"] = "1"
        deep = _run(
            "themed_deep_push",
            [PY, "scripts/run_logos_track_b_themed_deep_push_v1.py"],
            timeout=3600,
        )
        steps.append(deep)
        deep_push_ok = deep.get("ok", False)
    else:
        steps.append(
            {
                "name": "themed_deep_push_skipped",
                "ok": True,
                "reason": "ollama_unavailable" if not args.skip_ollama else "skip_flag",
            }
        )

    phase_k_cmd = [PY, "scripts/run_logos_track_b_phase_k_v1.py"]
    if args.skip_phase_j:
        phase_k_cmd.append("--skip-phase-j")
    phase_k = _run("phase_k_closure", phase_k_cmd, timeout=1200)
    steps.append(phase_k)

    phase_k_ok = False
    phase_k_path = REPORTS / "logos_track_b_phase_k_v1_latest.json"
    if phase_k_path.is_file():
        try:
            phase_k_doc = json.loads(phase_k_path.read_text(encoding="utf-8-sig"))
            phase_k_ok = phase_k_doc.get("ok") is True
        except json.JSONDecodeError:
            pass

    overall_ok = all(s.get("ok") for s in steps) and phase_k_ok
    if deep_push_ok is False:
        overall_ok = False

    doc = {
        "schema": "logos_track_b_phase_l_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "ollama_ok": ollama_ok,
        "deep_push_ok": deep_push_ok,
        "phase_k_ok": phase_k_ok,
        "steps": steps,
        "ok": overall_ok,
        "reproduce": "py scripts/run_logos_track_b_phase_l_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": overall_ok, "out": str(args.out)}, ensure_ascii=False))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
