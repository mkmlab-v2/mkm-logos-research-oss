#!/usr/bin/env python3
"""Run Step-1/2 pipeline: proxy-table freeze + leakage audit."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT_JSON = ART / "sasang_byeongjeung_yakri_step12_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "command": " ".join(cmd),
        "exit_code": int(cp.returncode),
        "stdout_tail": (cp.stdout or "").strip()[-800:],
        "stderr_tail": (cp.stderr or "").strip()[-800:],
    }


def main() -> int:
    mapping_json = ART / "sasang_12state_proxy_mapping_v1_latest.json"
    events_jsonl = ART / "sasang_symptom_market_proxy_events_latest.jsonl"
    leakage_json = ART / "sasang_symptom_transition_leakage_audit_latest.json"

    steps = [
        _run([sys.executable, "scripts/build_sasang_12state_proxy_mapping_v1.py"]),
        _run([sys.executable, "scripts/validate_sasang_12state_proxy_mapping_v1.py", "--mapping-json", str(mapping_json)]),
        _run([sys.executable, "scripts/build_sasang_byeongjeung_yakri_proxy_table_v1.py"]),
        _run([sys.executable, "scripts/build_sasang_symptom_market_proxy_v1.py", "--output-jsonl", str(events_jsonl)]),
        _run([sys.executable, "scripts/audit_sasang_symptom_transition_leakage_v1.py", "--events-jsonl", str(events_jsonl), "--out-json", str(leakage_json)]),
    ]
    all_exit_zero = all(s["exit_code"] == 0 for s in steps)
    leakage = {}
    if leakage_json.is_file():
        leakage = json.loads(leakage_json.read_text(encoding="utf-8"))

    payload = {
        "schema": "sasang_byeongjeung_yakri_step12_v1",
        "generated_at_utc": _now_utc(),
        "all_exit_zero": all_exit_zero,
        "step_count": len(steps),
        "steps": steps,
        "leakage_status": leakage.get("status"),
        "n_leakage_suspects": leakage.get("n_leakage_suspects"),
        "leakage_ratio": leakage.get("leakage_ratio"),
        "track_wall": {"track_b_only": True, "a_track_autobind_forbidden": True},
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT_JSON}")
    return 0 if all_exit_zero else 1


if __name__ == "__main__":
    raise SystemExit(main())
