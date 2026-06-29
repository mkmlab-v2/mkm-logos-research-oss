#!/usr/bin/env python3
"""[HYPO] RQ-025 layer-5 ensemble — causal + TimeAPN + Chronos + CMDMamba stub stack WF."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_rq025_gbdt_shadow_hypo_v1 import _feature_vector  # noqa: E402
from scripts.build_rq025_timeapn_layer2_poc_v1 import _eval_wf  # noqa: E402
from scripts.rq025_chronos_stub_v1 import expand_chronos_series_features  # noqa: E402
from scripts.rq025_cmdmamba_stub_v1 import expand_cmdmamba_series_features  # noqa: E402
from scripts.rq025_timeapn_dwt_stub_v1 import expand_macro_series_features  # noqa: E402

DEFAULT_WIDE = ROOT / "reports/rq025_vault_macro_direct_wide_hypo_v1_latest.json"
DEFAULT_CAUSAL = ROOT / "reports/rq025_vault_macro_direct_causal_hypo_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/rq025_layer5_ensemble_poc_v1_latest.json"
SCHEMA = "rq025_layer5_ensemble_poc_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wide-join-json", type=Path, default=DEFAULT_WIDE)
    ap.add_argument("--causal-json", type=Path, default=DEFAULT_CAUSAL)
    ap.add_argument("--dwt-window", type=int, default=8)
    ap.add_argument("--chronos-window", type=int, default=16)
    ap.add_argument("--mamba-window", type=int, default=12)
    ap.add_argument("--n-folds", type=int, default=3)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    wide_path = args.wide_join_json if args.wide_join_json.is_absolute() else ROOT / args.wide_join_json
    causal_path = args.causal_json if args.causal_json.is_absolute() else ROOT / args.causal_json
    wide = _load(wide_path)
    causal = _load(causal_path)
    base_features = list(causal.get("selected_features") or [])
    if not base_features:
        raise SystemExit("no selected_features in causal json")

    rows = [
        r
        for r in wide.get("rows_hybrid_kospi_252d") or []
        if isinstance(r, dict) and r.get("macro_present") and r.get("daily_flow_present")
    ]
    rows.sort(key=lambda r: str(r.get("eval_date")))
    if len(rows) < 12:
        raise SystemExit(f"insufficient intersection rows: {len(rows)}")

    dates = [str(r.get("eval_date"))[:10] for r in rows]
    macro_keys = sorted(
        {f.replace("macro_", "") for f in base_features if str(f).startswith("macro_")}
    )
    values_by_key: dict[str, dict[str, float]] = {}
    for mk in macro_keys:
        vbd: dict[str, float] = {}
        for r in rows:
            dk = str(r.get("eval_date"))[:10]
            macro = r.get("macro") if isinstance(r.get("macro"), dict) else {}
            try:
                vbd[dk] = float(macro.get(mk))
            except (TypeError, ValueError):
                continue
        values_by_key[mk] = vbd

    extra_by_date: dict[str, dict[str, float]] = {dk: {} for dk in dates}
    for mk, vbd in values_by_key.items():
        for expander, prefix, win in (
            (expand_macro_series_features, f"ta_{mk}", int(args.dwt_window)),
            (expand_chronos_series_features, f"ch_{mk}", int(args.chronos_window)),
            (expand_cmdmamba_series_features, f"mb_{mk}", int(args.mamba_window)),
        ):
            expanded = expander(dates, vbd, window=win, prefix=prefix)
            for dk, feats in expanded.items():
                extra_by_date.setdefault(dk, {}).update(feats)

    baseline_labeled: list[tuple[str, np.ndarray, float]] = []
    ensemble_labeled: list[tuple[str, np.ndarray, float]] = []
    feat_count = 0
    for r in rows:
        hit = r.get("panel_hit")
        if hit is None:
            continue
        dk = str(r.get("eval_date"))[:10]
        base = np.array(_feature_vector(r, base_features), dtype=float)
        extras = sorted(extra_by_date.get(dk, {}))
        if not feat_count and extras:
            feat_count = len(extras)
        ext = np.array([float(extra_by_date[dk][k]) for k in extras], dtype=float)
        full = np.concatenate([base, ext])
        if not (np.all(np.isfinite(base)) and np.all(np.isfinite(full))):
            continue
        yv = 1.0 if bool(hit) else 0.0
        baseline_labeled.append((dk, base, yv))
        ensemble_labeled.append((dk, full, yv))

    if len(baseline_labeled) < 12:
        raise SystemExit(f"insufficient labeled rows: {len(baseline_labeled)}")

    base_wf = _eval_wf(baseline_labeled, n_folds=int(args.n_folds))
    ens_wf = _eval_wf(ensemble_labeled, n_folds=int(args.n_folds))
    delta = round(float(ens_wf["mean_test_accuracy"]) - float(base_wf["mean_test_accuracy"]), 6)

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "rq_id": "RQ-025",
        "layer": 5,
        "implementation": "timeapn_chronos_cmdmamba_logistic_ensemble_stub_v1",
        "macro_source": "vault_csv",
        "inputs": {
            "wide_join_json": str(wide_path.relative_to(ROOT)).replace("\\", "/"),
            "causal_json": str(causal_path.relative_to(ROOT)).replace("\\", "/"),
            "n_labeled_rows": len(baseline_labeled),
            "n_ensemble_features_added": feat_count,
        },
        "causal_baseline_only": base_wf,
        "full_ensemble_stack": ens_wf,
        "delta_ensemble_minus_baseline": delta,
        "verdict": {
            "ensemble_improves_over_baseline": delta > 0,
            "beats_majority_baseline": float(ens_wf["mean_test_accuracy"])
            > float(ens_wf["mean_majority_baseline"]),
            "gate_0_55_pass": float(ens_wf["mean_test_accuracy"]) >= 0.55,
            "track_a_promotion": False,
        },
        "track_wall": {
            "track_a_auto_merge": False,
            "oracle_promotion": False,
            "live_trading": False,
        },
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {out_path} baseline={base_wf['mean_test_accuracy']} "
        f"ensemble={ens_wf['mean_test_accuracy']} delta={delta}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
