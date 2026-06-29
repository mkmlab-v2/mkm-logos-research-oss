#!/usr/bin/env python3
"""HD auto chain: RWC-lite + CPTC-lite + FinStressTS diagnostic + stack compare [tier_0]."""
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


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _hold_band(doc: dict[str, Any], key: str) -> float | None:
    hold = (doc.get("summary") or {}).get("holdout_pooled") or {}
    return hold.get(key)


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
    steps.append(_run("conformal_param_sweep", [PY, "scripts/run_kospi_field_band_conformal_param_sweep_v1.py"]))
    steps.append(_run("tuned_apply", [PY, "scripts/run_kospi_field_band_tuned_apply_v1.py"]))
    steps.append(_run("finstress_diagnostic", [PY, "scripts/run_kospi_finstress_ts_diagnostic_v1.py"]))
    steps.append(_run("rwc_shadow_replay", [PY, "scripts/run_kospi_field_band_rwc_shadow_replay_v1.py"]))
    steps.append(_run("nested_revalidate", [PY, "scripts/run_kospi_field_band_nested_tune_revalidate_v1.py"]))
    steps.append(_run("commander_ack_packet", [PY, "scripts/build_kospi_field_band_commander_ack_packet_v1.py"]))
    steps.append(
        _run(
            "premium_multilens_attach",
            [PY, "scripts/build_premium_btrack_multilens_report_v1.py", "--mode", "best-effort", "--no-validate"],
            timeout=180,
        )
    )

    ok = all(s["exit_code"] == 0 for s in steps)
    rwc = _read_json(ROOT / "reports/kospi_field_band_rwc_lite_v1_latest.json")
    cptc = _read_json(ROOT / "reports/kospi_field_band_cptc_lite_v1_latest.json")
    fin = _read_json(ROOT / "reports/kospi_finstress_ts_diagnostic_v1_latest.json")
    stack_ens = _read_json(ROOT / "reports/kospi_field_band_stack_ensemble_v1_latest.json")
    ack = _read_json(ROOT / "docs/final/artifacts/kospi_field_band_commander_ack_packet_v1_latest.json")

    base = _hold_band(rwc, "band_hit_rate_base") or _hold_band(cptc, "band_hit_rate_base")
    rwc_rate = _hold_band(rwc, "band_hit_rate_rwc")
    cptc_rate = _hold_band(cptc, "band_hit_rate_cptc")

    stack = {
        "holdout_band_base": base,
        "holdout_band_rwc": rwc_rate,
        "holdout_band_cptc": cptc_rate,
        "holdout_band_stack_union": (
            ((stack_ens.get("summary") or {}).get("holdout_pooled") or {}).get("stack") or {}
        ).get("band_hit_rate"),
        "delta_rwc_minus_base": (rwc.get("summary") or {}).get("delta_rwc_minus_base_holdout"),
        "delta_cptc_minus_base": (cptc.get("summary") or {}).get("delta_cptc_minus_base_holdout"),
        "delta_stack_minus_base": (stack_ens.get("summary") or {}).get("delta_stack_minus_base_holdout"),
        "best_band_layer": (
            "stack_union"
            if (
                ((stack_ens.get("summary") or {}).get("holdout_pooled") or {}).get("stack") or {}
            ).get("band_hit_rate", 0)
            >= max(rwc_rate or 0, cptc_rate or 0)
            else (
                "rwc_lite"
                if (rwc_rate or 0) >= (cptc_rate or 0)
                else "cptc_lite"
            )
        ),
        "finstress_recommendation": fin.get("recommendation"),
        "finstress_root_causes": fin.get("root_cause_tags"),
        "l3_ack_ready": ack.get("ack_ready"),
    }
    stack_path = ROOT / "reports/kospi_field_band_stack_compare_v1_latest.json"
    stack_doc = {
        "schema": "kospi_field_band_stack_compare_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "stack": stack,
        "promotion_candidates": {
            "rwc_lite": rwc.get("promotion_candidate"),
            "cptc_lite": cptc.get("promotion_candidate"),
        },
        "reproduce": "py scripts/run_kospi_field_band_hd_auto_chain_v1.py",
    }
    stack_path.write_text(json.dumps(stack_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art_stack = ROOT / "docs/final/artifacts/kospi_field_band_stack_compare_v1_latest.json"
    art_stack.parent.mkdir(parents=True, exist_ok=True)
    art_stack.write_text(json.dumps(stack_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    completion = {
        "schema": "hd_autonomous_evolution_completion_v1",
        "generated_at_utc": _utc(),
        "mission": "KOSPI Field band sweep+tuned+stack+premium thin attach",
        "hypothesis_tier": "B",
        "research_only": True,
        "tier": "tier_0",
        "quality_ok": ok and bool(rwc) and bool(cptc) and bool(fin) and bool(stack_ens) and bool(ack),
        "ok": ok,
        "steps": steps,
        "stack": stack,
        "artifacts": {
            "rwc_lite": "reports/kospi_field_band_rwc_lite_v1_latest.json",
            "cptc_lite": "reports/kospi_field_band_cptc_lite_v1_latest.json",
            "finstress": "reports/kospi_finstress_ts_diagnostic_v1_latest.json",
            "stack_ensemble": "reports/kospi_field_band_stack_ensemble_v1_latest.json",
            "rwc_shadow_replay": "reports/kospi_field_band_rwc_shadow_replay_v1_latest.json",
            "nested_revalidate": "reports/kospi_field_band_nested_tune_revalidate_v1_latest.json",
            "tuned_policy": "docs/final/artifacts/kospi_field_band_conformal_tuned_policy_v1_latest.json",
            "premium_report": "reports/premium_btrack_multilens_report_v1.md",
            "commander_ack_packet": "docs/final/artifacts/kospi_field_band_commander_ack_packet_v1_latest.json",
        },
        "reproduce": "py scripts/run_kospi_field_band_hd_auto_chain_v1.py --skip-extended-oos",
        "send_gate": "HOLD",
    }
    out = ROOT / "reports/hd_autonomous_evolution_completion_v1_latest.json"
    out.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "stack": stack}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
