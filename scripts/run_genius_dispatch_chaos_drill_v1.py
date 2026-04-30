#!/usr/bin/env python3
"""Run a local chaos drill for genius dispatch chain health."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "genius_dispatch_chaos_drill_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run_py(script: Path, args: list[str]) -> tuple[int, str]:
    cmd = ["py", str(script), *args]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    out = (cp.stdout or "").strip()
    err = (cp.stderr or "").strip()
    merged = out if out else err
    return cp.returncode, merged


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    with tempfile.TemporaryDirectory(prefix="genius-dispatch-chaos-") as td:
        tdir = Path(td)
        gate_json = tdir / "dispatch_health_gate_hold.json"
        dispatch_out = tdir / "dispatch_health_gate_dispatch.json"
        hist_jsonl = tdir / "dispatch_health_history.jsonl"
        health_gate_json = tdir / "dispatch_health_gate.json"

        _write_json(
            gate_json,
            {
                "schema": "genius_reasoning_dispatch_health_gate_v1",
                "generated_at_utc": _iso_now(),
                "status": "HOLD",
                "reasons": ["chaos_drill_forced_hold"],
                "current": {"failed_total": 1},
            },
        )
        rc1, out1 = _run_py(
            ROOT / "scripts" / "dispatch_genius_reasoning_dispatch_health_gate_webhook_v1.py",
            [
                "--gate-json",
                str(gate_json),
                "--output-json",
                str(dispatch_out),
            ],
        )

        # Compose synthetic history row where dispatch should have happened but webhook is not configured.
        row = {
            "schema": "genius_reasoning_dispatch_health_history_row_v1",
            "ts_utc": _iso_now(),
            "benchmark_alert_should_dispatch": True,
            "benchmark_alert_webhook_configured": False,
            "benchmark_alert_dispatch_status": "skipped",
            "human_review_gate_should_dispatch": False,
            "human_review_gate_webhook_configured": False,
            "human_review_gate_dispatch_status": "skipped",
            "human_review_trend_should_dispatch": False,
            "human_review_trend_webhook_configured": False,
            "human_review_trend_dispatch_status": "skipped",
        }
        hist_jsonl.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
        rc2, out2 = _run_py(
            ROOT / "scripts" / "check_genius_reasoning_dispatch_health_gate_v1.py",
            [
                "--history-jsonl",
                str(hist_jsonl),
                "--output-json",
                str(health_gate_json),
                "--window",
                "1",
                "--max-failed-count",
                "0",
                "--max-unconfigured-count",
                "0",
            ],
        )

        dispatch_doc: dict[str, Any] = {}
        gate_doc: dict[str, Any] = {}
        if dispatch_out.is_file():
            dispatch_doc = json.loads(dispatch_out.read_text(encoding="utf-8-sig"))
        if health_gate_json.is_file():
            gate_doc = json.loads(health_gate_json.read_text(encoding="utf-8-sig"))

        dispatch_status = ((dispatch_doc.get("dispatch") or {}).get("status")) if isinstance(dispatch_doc, dict) else None
        health_status = gate_doc.get("status") if isinstance(gate_doc, dict) else None
        drill_pass = (rc1 == 0 and rc2 == 0 and dispatch_status in {"skipped", "failed", "sent"} and health_status == "HOLD")

        out = {
            "schema": "genius_dispatch_chaos_drill_v1",
            "generated_at_utc": _iso_now(),
            "results": {
                "dispatch_webhook_script_exit_code": rc1,
                "dispatch_webhook_output": out1,
                "dispatch_status": dispatch_status,
                "health_gate_script_exit_code": rc2,
                "health_gate_output": out2,
                "health_gate_status": health_status,
            },
            "pass": drill_pass,
            "note": "Pass means forced HOLD + missing-webhook history is detected as dispatch health HOLD.",
        }
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        _write_json(args.output_json, out)
        print(json.dumps({"ok": True, "output_json": str(args.output_json).replace("\\", "/"), "pass": drill_pass}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
