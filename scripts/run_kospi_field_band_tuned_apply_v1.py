#!/usr/bin/env python3
"""Apply tuned conformal policy from sweep → refresh RWC/CPTC/stack artifacts [HYPO]."""
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

from scripts.run_kospi_field_band_cptc_lite_v1 import run_cptc_lite  # noqa: E402
from scripts.run_kospi_field_band_rwc_lite_v1 import run_rwc_lite  # noqa: E402
from scripts.run_kospi_field_band_stack_ensemble_v1 import run_stack_ensemble  # noqa: E402
from scripts.run_kospi_four_lens_conditional_fusion_ablation_v1 import _read  # noqa: E402

DEFAULT_POLICY = ROOT / "docs/final/artifacts/kospi_field_band_conformal_tuned_policy_v1_latest.json"
DEFAULT_EVAL = ROOT / "reports/kospi_multi_month_prophecy_eval_v1_latest.json"
DEFAULT_CAL = ROOT / "reports/kospi_multi_month_prophecy_calendar_v1_latest.json"
DEFAULT_FUSION = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
DEFAULT_FIELD_TIER2 = ROOT / "reports/field_lens_vol_band_tier2_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--force-default", action="store_true", help="Ignore use_tuned and run default params")
    args = ap.parse_args()

    policy = _read(args.policy_json)
    if not policy:
        print("Missing tuned policy", file=sys.stderr)
        return 2

    ev = _read(DEFAULT_EVAL)
    cal = _read(DEFAULT_CAL)
    fusion = _read(DEFAULT_FUSION)
    tier2 = _read(DEFAULT_FIELD_TIER2)
    if not all((ev, cal, fusion)):
        print("Missing eval inputs", file=sys.stderr)
        return 2

    use_tuned = bool(policy.get("use_tuned")) and not args.force_default
    rwc_p = policy.get("rwc") if isinstance(policy.get("rwc"), dict) else {}
    cptc_p = policy.get("cptc") if isinstance(policy.get("cptc"), dict) else {}

    rwc_doc = run_rwc_lite(
        ev,
        cal,
        fusion,
        field_tier2=tier2,
        decay_lambda=float(rwc_p.get("decay_lambda") or 0.05),
        margin_gamma=float(rwc_p.get("margin_gamma") or 0.15),
        bandwidth_h=float(rwc_p.get("bandwidth_h") or 1.0),
    )
    cptc_doc = run_cptc_lite(
        ev,
        cal,
        fusion,
        field_tier2=tier2,
        vol_jump_threshold=float(cptc_p.get("vol_jump_threshold") or 1.75),
        margin_gamma=float(cptc_p.get("margin_gamma") or 0.18),
        base_quantile_q=float(cptc_p.get("base_quantile_q") or 0.88),
    )
    stack_doc = run_stack_ensemble(ev, cal, rwc_doc, cptc_doc)

    if use_tuned:
        rwc_doc["tuned_policy_applied"] = True
        cptc_doc["tuned_policy_applied"] = True
        stack_doc["tuned_policy_applied"] = True

    paths = {
        "rwc": ROOT / "reports/kospi_field_band_rwc_lite_v1_latest.json",
        "cptc": ROOT / "reports/kospi_field_band_cptc_lite_v1_latest.json",
        "stack": ROOT / "reports/kospi_field_band_stack_ensemble_v1_latest.json",
    }
    art = ROOT / "docs/final/artifacts"
    _write_json(paths["rwc"], rwc_doc)
    _write_json(art / "kospi_field_band_rwc_lite_v1_latest.json", rwc_doc)
    _write_json(paths["cptc"], cptc_doc)
    _write_json(art / "kospi_field_band_cptc_lite_v1_latest.json", cptc_doc)
    _write_json(paths["stack"], stack_doc)
    _write_json(art / "kospi_field_band_stack_ensemble_v1_latest.json", stack_doc)

    hold_stack = (
        ((stack_doc.get("summary") or {}).get("holdout_pooled") or {}).get("stack") or {}
    ).get("band_hit_rate")

    meta = {
        "schema": "kospi_field_band_tuned_apply_v1",
        "generated_at_utc": _utc(),
        "use_tuned": use_tuned,
        "holdout_stack_band_hit_rate": hold_stack,
        "policy_pointer": str(args.policy_json).replace("\\", "/"),
    }
    _write_json(ROOT / "reports/kospi_field_band_tuned_apply_v1_latest.json", meta)

    print(json.dumps({"ok": True, **meta}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
