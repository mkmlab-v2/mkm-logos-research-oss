#!/usr/bin/env python3
"""Ko shorts HD delegation mission — Netflix pro ASS + full chain verify [HYPO]."""

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

DEFAULT_MISSION_OUT = ROOT / "reports/ko_shorts_hd_delegation_mission_v1_latest.json"
DEFAULT_COMPLETION = ROOT / "reports/ko_shorts_hd_delegation_completion_v1_latest.json"
PROFILE = "netflix_v16_pro"

PYTEST_FILES = [
    "tests/test_ko_shorts_subtitle_gate_and_burnin_v1.py",
    "tests/test_ko_shorts_full_chain_v1.py",
    "tests/test_ko_shorts_alignment_backend_spike_v1.py",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _run(name: str, cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    tail_lines = (proc.stdout or proc.stderr or "").strip().splitlines()
    tail = tail_lines[-1] if tail_lines else ""
    step: dict[str, Any] = {
        "node": name,
        "exit_code": proc.returncode,
        "cmd": cmd,
        "tail": tail,
        "ok": proc.returncode == 0,
    }
    try:
        step["summary"] = json.loads(tail)
    except Exception:
        if proc.stderr:
            step["stderr_tail"] = proc.stderr.strip()[-500:]
    return step


def run_mission_v1(*, skip_burn: bool, skip_alignment: bool) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []

    nodes.append(_run("pytest_offline", [sys.executable, "-m", "pytest", *PYTEST_FILES, "-q"]))

    nodes.append(
        _run(
            "burnin_batch_pro",
            [
                sys.executable,
                str(ROOT / "scripts/run_ko_shorts_ass_burnin_batch_v1.py"),
                "--profile",
                PROFILE,
            ]
            + (["--skip-burn"] if skip_burn else []),
        )
    )

    chain_cmd = [
        sys.executable,
        str(ROOT / "scripts/run_ko_shorts_full_chain_v1.py"),
        "--quick",
        "--profile",
        PROFILE,
    ]
    if skip_burn:
        chain_cmd.append("--skip-burn")
    if not skip_alignment:
        chain_cmd.append("--include-alignment-spike")
    nodes.append(_run("full_chain_quick_pro", chain_cmd))

    ok = all(n["ok"] for n in nodes)
    mission = {
        "schema": "ko_shorts_hd_delegation_mission_v1",
        "hypothesis_tag": "[HYPO]",
        "research_only": True,
        "send_gate": "HOLD",
        "generated_at_utc": _utc_now(),
        "mission_line": "ko shorts Netflix pro ASS + full chain tier_0 verify",
        "lane": "ms",
        "cost_tier": "tier_0",
        "profile": PROFILE,
        "preflight_note": "browser/NL optional; local script nodes only",
        "ok": ok,
        "nodes": nodes,
        "artifacts": {
            "burnin_batch": "reports/ko_shorts_burnin_batch_v1_latest.json",
            "full_chain": "reports/ko_shorts_full_chain_v1_latest.json",
            "preview_html": "reports/ko_shorts_cursor_preview_v1.html",
        },
        "reproduce": f"py scripts/run_ko_shorts_hd_delegation_mission_v1.py --profile {PROFILE}",
    }
    return mission


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_MISSION_OUT)
    ap.add_argument("--completion-out", type=Path, default=DEFAULT_COMPLETION)
    ap.add_argument("--skip-burn", action="store_true")
    ap.add_argument("--skip-alignment", action="store_true")
    args = ap.parse_args()

    report = run_mission_v1(skip_burn=args.skip_burn, skip_alignment=args.skip_alignment)
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    completion = {
        "schema": "ko_shorts_hd_delegation_completion_v1",
        "hypothesis_tag": "[HYPO]",
        "research_only": True,
        "send_gate": "HOLD",
        "generated_at_utc": report["generated_at_utc"],
        "mission_line": report["mission_line"],
        "lane": report["lane"],
        "cost_tier": report["cost_tier"],
        "quality_ok": report["ok"],
        "profile": PROFILE,
        "completion_contract": {
            "exit_code_target": 0,
            "artifact": _rel(args.completion_out if args.completion_out.is_absolute() else ROOT / args.completion_out),
            "reproducible_command": report["reproduce"],
        },
        "nodes": {n["node"]: {"ok": n["ok"], "exit_code": n["exit_code"]} for n in report["nodes"]},
        "mission_report": _rel(out),
    }
    comp_path = args.completion_out if args.completion_out.is_absolute() else ROOT / args.completion_out
    comp_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": report["ok"], "out": _rel(out), "completion": _rel(comp_path)}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
