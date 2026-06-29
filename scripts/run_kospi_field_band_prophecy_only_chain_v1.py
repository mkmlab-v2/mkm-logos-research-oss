#!/usr/bin/env python3
"""Chain: prophecy-only panel build → tuned stack OOS [HYPO][tier_0]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, timeout: int = 300) -> dict[str, Any]:
    cp = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return {"step": name, "exit_code": cp.returncode, "tail": ((cp.stdout or "") + (cp.stderr or "")).strip()[-500:]}


DEFAULT_OOS_LOG = ROOT / "reports/kospi_field_band_prophecy_only_oos_log_v1.jsonl"


def _append_oos_log(oos: dict[str, Any]) -> None:
    line = json.dumps(
        {
            "generated_at_utc": _utc(),
            "prophecy_only_oos_ready": oos.get("prophecy_only_oos_ready"),
            "n_scored_total": oos.get("n_scored_total"),
            "holdout_n": ((oos.get("holdout_pooled") or {}).get("stack_union") or {}).get("n_scored"),
            "holdout_stack": ((oos.get("holdout_pooled") or {}).get("stack_union") or {}).get("band_hit_rate"),
            "delta_stack_minus_base_holdout": oos.get("delta_stack_minus_base_holdout"),
            "included_prophecy_months": oos.get("included_prophecy_months"),
        },
        ensure_ascii=False,
    )
    DEFAULT_OOS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with DEFAULT_OOS_LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    args = ap.parse_args()

    steps = [
        _run("prophecy_only_panel", [PY, "scripts/build_kospi_prophecy_only_panel_v1.py"]),
        _run("prophecy_only_oos", [PY, "scripts/run_kospi_field_band_prophecy_only_oos_v1.py"]),
    ]
    ok = all(s["exit_code"] == 0 for s in steps)
    oos_path = ROOT / "reports/kospi_field_band_prophecy_only_oos_v1_latest.json"
    oos: dict[str, Any] = {}
    if oos_path.is_file():
        try:
            oos = json.loads(oos_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            oos = {}
    if ok and oos:
        _append_oos_log(oos)

    completion = {
        "schema": "kospi_field_band_prophecy_only_chain_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "steps": steps,
        "prophecy_only_oos_ready": oos.get("prophecy_only_oos_ready"),
        "track_a_discussion_eligible": (oos.get("small_sample_guardrails") or {}).get(
            "track_a_discussion_eligible"
        ),
        "metrics": {
            "n_scored": oos.get("n_scored_total"),
            "holdout_stack": (oos.get("holdout_pooled") or {}).get("stack_union", {}).get("band_hit_rate"),
            "delta": oos.get("delta_stack_minus_base_holdout"),
        },
        "artifact": "reports/kospi_field_band_prophecy_only_oos_v1_latest.json",
        "reproduce": "py scripts/run_kospi_field_band_prophecy_only_chain_v1.py",
    }
    out = ROOT / "reports/kospi_field_band_prophecy_only_chain_v1_latest.json"
    out.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "metrics": completion["metrics"], "ready": oos.get("prophecy_only_oos_ready")}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
