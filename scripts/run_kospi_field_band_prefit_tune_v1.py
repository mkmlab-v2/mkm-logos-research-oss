#!/usr/bin/env python3
"""Tune RWC/CPTC on prefit panel only → frozen prefit policy [HYPO]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_kospi_field_band_conformal_param_sweep_v1 import run_sweep  # noqa: E402
from scripts.run_kospi_four_lens_conditional_fusion_ablation_v1 import _read  # noqa: E402

DEFAULT_EVAL = ROOT / "reports/kospi_field_band_prefit_panel_eval_v1_latest.json"
DEFAULT_CAL = ROOT / "reports/kospi_field_band_prefit_panel_calendar_v1_latest.json"
DEFAULT_FUSION = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
DEFAULT_FIELD_TIER2 = ROOT / "reports/field_lens_vol_band_tier2_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_field_band_prefit_tune_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/kospi_field_band_prefit_tune_v1_latest.json"
POLICY_OUT = ROOT / "docs/final/artifacts/kospi_field_band_conformal_prefit_frozen_policy_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--calendar-json", type=Path, default=DEFAULT_CAL)
    ap.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--field-tier2-json", type=Path, default=DEFAULT_FIELD_TIER2)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    ev = _read(args.eval_json)
    cal = _read(args.calendar_json)
    fusion = _read(args.fusion_json)
    if not all((ev, cal, fusion)):
        print("Missing prefit eval, calendar, or fusion", file=sys.stderr)
        return 2

    doc = run_sweep(
        ev,
        cal,
        fusion,
        field_tier2=_read(args.field_tier2_json),
        rwc_decay_grid=[0.03, 0.05, 0.08],
        rwc_gamma_grid=[0.12, 0.15, 0.18],
        cptc_vol_jump_grid=[1.5, 1.75, 2.0],
        cptc_gamma_grid=[0.15, 0.18, 0.21],
    )
    doc["schema"] = "kospi_field_band_prefit_tune_v1"
    doc["protocol"] = "tune_on_prefit_science_core_pre_may_only"
    doc["train_panel_pointer"] = "reports/kospi_field_band_prefit_panel_eval_v1_latest.json"
    doc["prophecy_oos_panel_forbidden_during_tune"] = True
    doc["reproduce"] = "py scripts/run_kospi_field_band_prefit_tune_v1.py"

    policy = {
        "schema": "kospi_field_band_conformal_prefit_frozen_policy_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "frozen": True,
        "use_tuned": True,
        "train_panel": "prefit_science_core_kospi_pre_may",
        "train_panel_pointer": doc["train_panel_pointer"],
        "oos_panel": "prophecy_only_may_june",
        "rwc": doc["best_rwc_params"],
        "cptc": doc["best_cptc_params"],
        "prefit_tune_pointer": "reports/kospi_field_band_prefit_tune_v1_latest.json",
        "legacy_mixed_policy_pointer": "docs/final/artifacts/kospi_field_band_conformal_tuned_policy_v1_latest.json",
    }

    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(payload, encoding="utf-8")
    ART_OUT.parent.mkdir(parents=True, exist_ok=True)
    ART_OUT.write_text(payload, encoding="utf-8")
    POLICY_OUT.write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "prefit_n": ev.get("n_scored"),
                "tuned_stack_holdout": doc["tuned_stack_holdout_band_hit_rate"],
                "delta": doc["delta_tuned_minus_default_stack"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
