#!/usr/bin/env python3
"""One-click media handoff chain: STT JSON -> ranked MD -> closure dry-run [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "tests/fixtures/media_stt_transcription_v1.example.json"
CHAIN_OUT = ROOT / "reports/media_handoff_chain_v1_latest.json"
STT_BUILDER = ROOT / "scripts/build_media_stt_transcription_from_wav_v1.py"
CLOSURE = ROOT / "scripts/verify_handoff_closure_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = (proc.stdout or proc.stderr).strip().splitlines()
    last = tail[-1] if tail else ""
    return proc.returncode, last


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--task-id", default="20260621-REALITY")
    ap.add_argument("--wav", type=Path, default=None)
    ap.add_argument("--from-json", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--engine", choices=("auto", "whisper", "sherpa", "fixture"), default="fixture")
    ap.add_argument("--strict-schema", action="store_true", default=True)
    args = ap.parse_args()

    stt_cmd = [sys.executable, str(STT_BUILDER), "--task-id", args.task_id, "--chain-handoff"]
    if args.strict_schema:
        stt_cmd.append("--strict-schema")

    if args.engine == "fixture" or (args.wav is None and args.from_json):
        src = args.from_json if args.from_json.is_absolute() else ROOT / args.from_json
        stt_cmd += ["--from-json", str(src)]
        mode = "fixture_replay"
    else:
        wav = args.wav if args.wav.is_absolute() else ROOT / args.wav
        stt_cmd += ["--wav", str(wav), "--engine", args.engine if args.engine != "fixture" else "auto"]
        mode = f"wav:{args.engine}"

    steps: dict[str, Any] = {}
    code, line = _run(stt_cmd)
    steps["stt_and_handoff"] = {"exit_code": code, "tail": line}
    if code != 0:
        _write_chain_report(args.task_id, mode, steps, ok=False)
        return code

    close_cmd = [
        sys.executable,
        str(CLOSURE),
        "--task-id",
        args.task_id,
        "--dry-run",
    ]
    code2, line2 = _run(close_cmd)
    steps["closure_dry_run"] = {"exit_code": code2, "tail": line2}
    ok = code2 == 0
    _write_chain_report(args.task_id, mode, steps, ok=ok)
    print(json.dumps({"ok": ok, "task_id": args.task_id, "mode": mode, "report": _rel(CHAIN_OUT)}, ensure_ascii=False))
    return 0 if ok else 2


def _write_chain_report(task_id: str, mode: str, steps: dict[str, Any], *, ok: bool) -> None:
    doc = {
        "schema": "media_handoff_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "task_id": task_id,
        "mode": mode,
        "steps": steps,
        "markdown_path": f"reports/handoff_workers/HW-{task_id}-LOGOS_CLIP.md",
        "ok": ok,
        "reproduce": f"py scripts/run_media_handoff_chain_v1.py --task-id {task_id}",
    }
    CHAIN_OUT.parent.mkdir(parents=True, exist_ok=True)
    CHAIN_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
