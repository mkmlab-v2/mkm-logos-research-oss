#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-lens marginal utility harness V1: ablation on evaluate_dual_regime_and_market_shock.

Contract: docs/final/artifacts/MULTILENS_MARGINAL_UTILITY_HARNESS_CONTRACT_V1.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
BT_ROOT = WORKSPACE_ROOT / "projects" / "bitcoin-trading"
CONTRACT_PATH = (
    WORKSPACE_ROOT
    / "docs"
    / "final"
    / "artifacts"
    / "MULTILENS_MARGINAL_UTILITY_HARNESS_CONTRACT_V1.json"
)

if str(BT_ROOT) not in sys.path:
    sys.path.insert(0, str(BT_ROOT))

from src.integration.dual_regime_api import (  # noqa: E402
    DualRegimeContext,
    evaluate_dual_regime_and_market_shock,
)


def _ctx_to_dict(ctx: DualRegimeContext) -> Dict[str, Any]:
    return {
        "risk_multiplier_cap": ctx.risk_multiplier_cap,
        "resonance_count": ctx.resonance_count,
        "veto_triggered": ctx.veto_triggered,
        "market_shock_confirmed": ctx.market_shock_confirmed,
        "interpretation": ctx.interpretation,
    }


def _parse_as_of(raw: Any) -> datetime:
    if isinstance(raw, str):
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    raise TypeError(f"as_of must be ISO string, got {type(raw)}")


def _builtin_scenarios() -> List[Dict[str, Any]]:
    """Deterministic rows aligned with dual_regime smoke tests / policy SSOT."""
    return [
        {
            "id": "builtin_myeongni_clamp_row",
            "as_of": "2026-03-29T12:00:00",
            "vector_4d": {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
            "psi_score": 0.5,
            "bible_risk_score": 0.5,
            "context_metrics": {"fear_greed_index": 0.5},
            "logos_manuscript_text": None,
            "logos_adjustment_strength": 0.12,
            "state_id": 7,
        },
        {
            "id": "builtin_bible_stress_row",
            "as_of": "2026-03-29T12:00:00",
            "vector_4d": {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
            "psi_score": 0.5,
            "bible_risk_score": 0.5,
            "context_metrics": {"fear_greed_index": 0.5},
            "logos_manuscript_text": None,
            "logos_adjustment_strength": 0.12,
            "state_id": 1,
        },
    ]


def _base_kwargs(
    row: Mapping[str, Any],
    workspace_root: Path,
) -> Dict[str, Any]:
    return {
        "as_of": _parse_as_of(row["as_of"]),
        "vector_4d": dict(row["vector_4d"]),
        "psi_score": float(row["psi_score"]),
        "bible_risk_score": float(row["bible_risk_score"]),
        "workspace_root": workspace_root,
        "context_metrics": dict(row.get("context_metrics") or {}),
        "logos_adjustment_strength": float(row.get("logos_adjustment_strength", 0.12)),
    }


def _optional_text(row: Mapping[str, Any]) -> Optional[str]:
    t = row.get("logos_manuscript_text")
    if t is None:
        return None
    s = str(t).strip()
    return s if s else None


def _optional_state(row: Mapping[str, Any]) -> Any:
    if "state_id" not in row or row["state_id"] is None:
        return None
    return row["state_id"]


def evaluate_row_ablation(
    row: Mapping[str, Any],
    workspace_root: Path,
    mode: str,
) -> DualRegimeContext:
    kw = _base_kwargs(row, workspace_root)
    logos = _optional_text(row)
    sid = _optional_state(row)
    if mode == "full":
        kw["logos_manuscript_text"] = logos
        kw["state_id"] = sid
    elif mode == "no_logos":
        kw["logos_manuscript_text"] = None
        kw["state_id"] = sid
    elif mode == "no_bible_stress":
        kw["bible_risk_score"] = 0.0
        kw["logos_manuscript_text"] = logos
        kw["state_id"] = sid
    elif mode == "no_myeongni_state":
        kw["logos_manuscript_text"] = logos
        kw["state_id"] = None
    else:
        raise ValueError(f"unknown ablation mode: {mode}")
    return evaluate_dual_regime_and_market_shock(**kw)


def _delta_cap(ablation: DualRegimeContext, full: DualRegimeContext) -> float:
    return float(ablation.risk_multiplier_cap - full.risk_multiplier_cap)


def _delta_bool(ablation: bool, full: bool) -> bool:
    return bool(ablation) != bool(full)


def run_marginal_utility_harness(
    workspace_root: Path,
    scenarios: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    rows_in = scenarios if scenarios is not None else _builtin_scenarios()
    ablation_modes = ("full", "no_logos", "no_bible_stress", "no_myeongni_state")

    out_rows: List[Dict[str, Any]] = []
    cap_deltas: Dict[str, List[float]] = {m: [] for m in ablation_modes if m != "full"}
    veto_flips: Dict[str, int] = {m: 0 for m in ablation_modes if m != "full"}
    shock_flips: Dict[str, int] = {m: 0 for m in ablation_modes if m != "full"}

    for row in rows_in:
        rid = str(row.get("id", "row"))
        full_ctx = evaluate_row_ablation(row, workspace_root, "full")
        full_d = _ctx_to_dict(full_ctx)

        ablation_block: Dict[str, Any] = {}
        for mode in ablation_modes:
            if mode == "full":
                continue
            actx = evaluate_row_ablation(row, workspace_root, mode)
            ad = _ctx_to_dict(actx)
            d_cap = _delta_cap(actx, full_ctx)
            ablation_block[mode] = {
                "context": ad,
                "deltas_vs_full": {
                    "risk_cap": d_cap,
                    "veto_flipped": _delta_bool(actx.veto_triggered, full_ctx.veto_triggered),
                    "shock_flipped": _delta_bool(
                        actx.market_shock_confirmed, full_ctx.market_shock_confirmed
                    ),
                },
            }
            cap_deltas[mode].append(abs(d_cap))
            if ablation_block[mode]["deltas_vs_full"]["veto_flipped"]:
                veto_flips[mode] += 1
            if ablation_block[mode]["deltas_vs_full"]["shock_flipped"]:
                shock_flips[mode] += 1

        out_rows.append(
            {
                "id": rid,
                "full": full_d,
                "ablations": ablation_block,
            }
        )

    summary: Dict[str, Any] = {
        "row_count": len(out_rows),
        "mean_abs_risk_cap_delta": {},
        "veto_flip_count": dict(veto_flips),
        "shock_flip_count": dict(shock_flips),
    }
    for mode, vals in cap_deltas.items():
        summary["mean_abs_risk_cap_delta"][mode] = statistics.mean(vals) if vals else 0.0

    contract_payload: Dict[str, Any] = {}
    if CONTRACT_PATH.is_file():
        try:
            contract_payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        except Exception:
            contract_payload = {"error": "contract_read_failed", "path": str(CONTRACT_PATH)}

    return {
        "schema": "multilens_marginal_utility_report_v1",
        "contract_ref": str(CONTRACT_PATH),
        "contract": contract_payload,
        "workspace_root": str(workspace_root.resolve()),
        "rows": out_rows,
        "summary": summary,
    }


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--workspace-root",
        type=Path,
        default=WORKSPACE_ROOT,
        help="Repo workspace root (parent of projects/bitcoin-trading)",
    )
    p.add_argument(
        "--grid",
        type=Path,
        default=None,
        help="Optional JSON file with key 'scenarios' (list of scenario objects)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write full JSON report to this path",
    )
    return p


def main() -> None:
    args = _parser().parse_args()
    root = args.workspace_root.resolve()
    scenarios: Optional[List[Dict[str, Any]]] = None
    if args.grid is not None:
        data = json.loads(Path(args.grid).read_text(encoding="utf-8"))
        scenarios = data.get("scenarios")
        if not isinstance(scenarios, list):
            raise SystemExit("--grid JSON must contain a 'scenarios' array")

    report = run_marginal_utility_harness(root, scenarios=scenarios)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
