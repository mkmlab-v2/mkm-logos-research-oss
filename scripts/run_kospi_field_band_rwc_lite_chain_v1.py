#!/usr/bin/env python3
"""HD chain: multi-month panel → RWC-lite band conformal PoC [HYPO][tier_0]."""
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-extended-oos", action="store_true")
    ap.add_argument("--skip-panel-build", action="store_true")
    args = ap.parse_args()

    steps: list[dict] = []
    if not args.skip_extended_oos:
        steps.append(
            _run(
                "extended_oos",
                [PY, "scripts/run_kospi_field_band_extended_oos_v1.py", "--skip-may-eval"],
            )
        )
    if not args.skip_panel_build:
        steps.append(_run("multi_month_panel", [PY, "scripts/build_kospi_multi_month_prophecy_panel_v1.py"]))
    steps.append(_run("rwc_lite", [PY, "scripts/run_kospi_field_band_rwc_lite_v1.py"]))

    ok = all(s["exit_code"] == 0 for s in steps)
    rwc_path = ROOT / "reports/kospi_field_band_rwc_lite_v1_latest.json"
    rwc_doc: dict[str, Any] = {}
    if rwc_path.is_file():
        try:
            rwc_doc = json.loads(rwc_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            rwc_doc = {}

    hold = (rwc_doc.get("summary") or {}).get("holdout_pooled") or {}
    completion = {
        "schema": "hd_autonomous_evolution_completion_v1",
        "generated_at_utc": _utc(),
        "mission": "KOSPI Field band RWC-lite PoC on multi-month panel",
        "hypothesis_tier": "B",
        "research_only": True,
        "tier": "tier_0",
        "quality_ok": ok and bool(rwc_doc),
        "ok": ok,
        "steps": steps,
        "metrics": {
            "holdout_band_base": hold.get("band_hit_rate_base"),
            "holdout_band_rwc": hold.get("band_hit_rate_rwc"),
            "delta_holdout": (rwc_doc.get("summary") or {}).get("delta_rwc_minus_base_holdout"),
            "promotion_candidate": rwc_doc.get("promotion_candidate"),
        },
        "artifacts": {
            "rwc_lite": "reports/kospi_field_band_rwc_lite_v1_latest.json",
            "extended_oos": "reports/kospi_field_band_extended_oos_v1_latest.json",
            "multi_month_eval": "reports/kospi_multi_month_prophecy_eval_v1_latest.json",
        },
        "reproduce": "py scripts/run_kospi_field_band_rwc_lite_chain_v1.py",
        "send_gate": "HOLD",
    }
    out = ROOT / "reports/hd_autonomous_evolution_completion_v1_latest.json"
    out.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "metrics": completion["metrics"]}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
