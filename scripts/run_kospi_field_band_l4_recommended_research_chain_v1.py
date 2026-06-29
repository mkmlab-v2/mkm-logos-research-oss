#!/usr/bin/env python3
"""L4 recommended research chain [HYPO][B-track].

1. Prophecy-only panel refresh
2. Prefit frozen policy (May-train panel) + honest OOS
3. Nested June-holdout revalidate on prophecy-only panel
4. FinStressTS diagnostic on expanded panel
5. Premium multilens band section refresh
6. L4 prep packet refresh

Repro: py scripts/run_kospi_field_band_l4_recommended_research_chain_v1.py
"""
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
PROPHECY_EVAL = ROOT / "reports/kospi_prophecy_only_panel_eval_v1_latest.json"
PROPHECY_CAL = ROOT / "reports/kospi_prophecy_only_panel_calendar_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_field_band_l4_recommended_research_chain_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/kospi_field_band_l4_recommended_research_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, timeout: int = 600) -> dict[str, Any]:
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


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-premium", action="store_true")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = [
        _run("prophecy_only_panel", [PY, "scripts/build_kospi_prophecy_only_panel_v1.py"]),
        _run("prefit_panel", [PY, "scripts/build_kospi_field_band_prefit_panel_v1.py"]),
        _run("prefit_tune", [PY, "scripts/run_kospi_field_band_prefit_tune_v1.py"]),
        _run("prefit_frozen_oos", [PY, "scripts/run_kospi_field_band_prefit_frozen_oos_v1.py"]),
        _run(
            "nested_june_revalidate",
            [
                PY,
                "scripts/run_kospi_field_band_nested_tune_revalidate_v1.py",
                "--eval-json",
                str(PROPHECY_EVAL),
                "--calendar-json",
                str(PROPHECY_CAL),
            ],
        ),
        _run(
            "finstress_ts",
            [
                PY,
                "scripts/run_kospi_finstress_ts_diagnostic_v1.py",
                "--eval-json",
                str(PROPHECY_EVAL),
            ],
        ),
    ]
    if not args.skip_premium:
        steps.append(
            _run(
                "premium_attach",
                [PY, "scripts/build_premium_btrack_multilens_report_v1.py", "--mode", "best-effort", "--no-validate"],
                timeout=180,
            )
        )
    steps.append(_run("l4_prep", [PY, "scripts/build_kospi_field_band_l4_prep_packet_v1.py"]))

    ok = all(s["exit_code"] == 0 for s in steps)
    prefit = _read(ROOT / "reports/kospi_field_band_prefit_frozen_oos_v1_latest.json")
    nested = _read(ROOT / "reports/kospi_field_band_nested_tune_revalidate_v1_latest.json")
    finstress = _read(ROOT / "reports/kospi_finstress_ts_diagnostic_v1_latest.json")
    l4 = _read(ROOT / "reports/kospi_field_band_l4_prep_packet_v1_latest.json")

    doc: dict[str, Any] = {
        "schema": "kospi_field_band_l4_recommended_research_chain_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "track_a_go": False,
        "ok": ok,
        "steps": steps,
        "metrics": {
            "prophecy_only_n_scored": (_read(PROPHECY_EVAL) or {}).get("n_scored"),
            "prefit_honest_oos_ready": prefit.get("prefit_honest_oos_ready"),
            "prefit_holdout_stack": ((prefit.get("prefit_oos") or {}).get("holdout_pooled") or {})
            .get("stack_union", {})
            .get("band_hit_rate"),
            "nested_revalidation_pass": nested.get("revalidation_pass"),
            "june_nested_delta": ((nested.get("june_holdout_metrics") or {}).get("nested_tune") or {}).get(
                "delta_stack_minus_base"
            ),
            "finstress_recommendation": finstress.get("recommendation"),
            "l4_track_a_discussion_eligible": l4.get("track_a_discussion_eligible"),
        },
        "reproduce": "py scripts/run_kospi_field_band_l4_recommended_research_chain_v1.py",
    }
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(payload, encoding="utf-8")
    ART_OUT.parent.mkdir(parents=True, exist_ok=True)
    ART_OUT.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": ok, "metrics": doc["metrics"]}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
