#!/usr/bin/env python3
"""Monthly prophecy-only band stack revalidate chain [HYPO][B-track]."""
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
DEFAULT_L4 = ROOT / "docs/final/artifacts/kospi_field_band_commander_l4_sign_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_field_band_monthly_prophecy_revalidate_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/kospi_field_band_monthly_prophecy_revalidate_v1_latest.json"
DEFAULT_LOG = ROOT / "reports/kospi_field_band_monthly_prophecy_revalidate_log_v1.jsonl"


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
    ap.add_argument("--skip-panel-build", action="store_true")
    ap.add_argument("--skip-premium", action="store_true")
    ap.add_argument("--l4-sign-json", type=Path, default=DEFAULT_L4)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    args = ap.parse_args()

    l4 = _read(args.l4_sign_json)
    if not l4.get("signed"):
        print(json.dumps({"ok": False, "error": "l4_sign_required"}, ensure_ascii=False), file=sys.stderr)
        return 2

    steps: list[dict[str, Any]] = []
    if not args.skip_panel_build:
        steps.append(_run("multi_month_panel", [PY, "scripts/build_kospi_multi_month_prophecy_panel_v1.py"]))
    steps.append(_run("conformal_sweep", [PY, "scripts/run_kospi_field_band_conformal_param_sweep_v1.py"]))
    steps.append(_run("tuned_apply", [PY, "scripts/run_kospi_field_band_tuned_apply_v1.py"]))
    steps.append(_run("nested_revalidate", [PY, "scripts/run_kospi_field_band_nested_tune_revalidate_v1.py"]))
    steps.append(_run("prophecy_only_oos", [PY, "scripts/run_kospi_field_band_prophecy_only_chain_v1.py"]))
    steps.append(_run("l4_prep", [PY, "scripts/build_kospi_field_band_l4_prep_packet_v1.py"]))
    if not args.skip_premium:
        steps.append(
            _run(
                "premium_attach",
                [PY, "scripts/build_premium_btrack_multilens_report_v1.py", "--mode", "best-effort", "--no-validate"],
                timeout=180,
            )
        )

    ok = all(s["exit_code"] == 0 for s in steps)
    nested = _read(ROOT / "reports/kospi_field_band_nested_tune_revalidate_v1_latest.json")
    stack = _read(ROOT / "reports/kospi_field_band_stack_ensemble_v1_latest.json")
    prophecy_oos = _read(ROOT / "reports/kospi_field_band_prophecy_only_oos_v1_latest.json")
    june = ((nested.get("june_holdout_metrics") or {}).get("nested_tune") or {})
    hold_stack = (
        ((stack.get("summary") or {}).get("holdout_pooled") or {}).get("stack") or {}
    )

    doc = {
        "schema": "kospi_field_band_monthly_prophecy_revalidate_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "track_a_go": False,
        "l4_sign_reference": l4.get("sign_reference"),
        "ok": ok,
        "steps": steps,
        "metrics": {
            "pooled_holdout_stack_union": hold_stack.get("band_hit_rate"),
            "june_prophecy_nested_delta": june.get("delta_stack_minus_base"),
            "nested_revalidation_pass": nested.get("revalidation_pass"),
            "prophecy_only_holdout_stack_union": (
                (prophecy_oos.get("holdout_pooled") or {}).get("stack_union") or {}
            ).get("band_hit_rate"),
            "prophecy_only_oos_ready": prophecy_oos.get("prophecy_only_oos_ready"),
        },
        "monthly_ok": ok
        and nested.get("revalidation_pass") is True
        and prophecy_oos.get("prophecy_only_oos_ready") is True,
        "reproduce": "py scripts/run_kospi_field_band_monthly_prophecy_revalidate_v1.py",
    }
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(payload, encoding="utf-8")
    ART_OUT.parent.mkdir(parents=True, exist_ok=True)
    ART_OUT.write_text(payload, encoding="utf-8")
    args.log_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.log_jsonl.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({k: doc[k] for k in ("generated_at_utc", "ok", "monthly_ok", "metrics", "l4_sign_reference")}, ensure_ascii=False) + "\n")

    print(json.dumps({"ok": ok, "monthly_ok": doc["monthly_ok"], "metrics": doc["metrics"]}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
