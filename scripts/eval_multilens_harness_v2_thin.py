#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multilens evaluation harness V2 (thin): emit same-date template for Logos/dual-regime, Myeongni B-track, Sasang B-track slots.

Contract: docs/final/artifacts/MULTILENS_EVAL_HARNESS_V2_THIN_CONTRACT.json
Curated dates: data/multilens_eval/curated_dates_v1.json

Does not compute fusion weights; fills null slots for manual or adapter population.

Ops (manual, not auto-run here):
- NotebookLM / Vault sync: scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1 (run without -WhatIf when G: is mounted; optional paths may log skip).
- Sasang B-track ledger append: scripts/sasang_dynamics_regime_mapping_ledger.py append -- ...
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = (
    WORKSPACE_ROOT
    / "docs"
    / "final"
    / "artifacts"
    / "MULTILENS_EVAL_HARNESS_V2_THIN_CONTRACT.json"
)
CURATED_DEFAULT = WORKSPACE_ROOT / "data" / "multilens_eval" / "curated_dates_v1.json"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _date_key_from_ts(ts: str) -> str:
    if not isinstance(ts, str) or len(ts) < 10:
        return ""
    return ts[:10]


def load_jsonl_by_calendar_date(path: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Index JSONL lines by YYYY-MM-DD from ts_utc."""
    idx: Dict[str, List[Dict[str, Any]]] = {}
    if not path.is_file():
        return idx
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        obj = json.loads(raw)
        ts = obj.get("ts_utc")
        if not ts:
            continue
        dk = _date_key_from_ts(str(ts))
        if not dk:
            continue
        idx.setdefault(dk, []).append(obj)
    return idx


def populate_report_from_jsonl(
    report: Dict[str, Any],
    *,
    sasang_jsonl: Optional[Path] = None,
    myeongni_jsonl: Optional[Path] = None,
) -> Dict[str, Any]:
    """Fill sasang_b_track / myeongni_b_track when calendar_date matches ts_utc day (last line wins)."""
    sas_idx = load_jsonl_by_calendar_date(sasang_jsonl) if sasang_jsonl else {}
    mye_idx = load_jsonl_by_calendar_date(myeongni_jsonl) if myeongni_jsonl else {}
    meta = report.setdefault("populate_meta", {})
    for row in report.get("rows") or []:
        d = row.get("calendar_date")
        if not isinstance(d, str):
            continue
        lo = row.setdefault("lens_outputs", {})
        if d in sas_idx and sas_idx[d]:
            lo["sasang_b_track"] = sas_idx[d][-1]
        if d in mye_idx and mye_idx[d]:
            lo["myeongni_b_track"] = mye_idx[d][-1]
    meta["sasang_jsonl"] = str(sasang_jsonl.resolve()) if sasang_jsonl and sasang_jsonl.is_file() else None
    meta["myeongni_jsonl"] = str(myeongni_jsonl.resolve()) if myeongni_jsonl and myeongni_jsonl.is_file() else None
    return report


def populate_dual_regime_from_inputs(
    report: Dict[str, Any],
    workspace_root: Path,
    inputs_path: Path,
) -> Dict[str, Any]:
    """Fill logos_dual_regime via evaluate_dual_regime_and_market_shock for each matching calendar_date."""
    if not inputs_path.is_file():
        return report

    bt = workspace_root / "projects" / "bitcoin-trading"
    bts = str(bt.resolve())
    if bts not in sys.path:
        sys.path.insert(0, bts)

    from src.integration.dual_regime_api import evaluate_dual_regime_and_market_shock  # noqa: WPS433

    root_s = str(workspace_root.resolve())
    if root_s not in sys.path:
        sys.path.insert(0, root_s)
    from scripts.core.logos_dual_regime_interpretation_snippet_v1 import (  # noqa: WPS433
        build_interpretation_snippet,
    )

    payload = load_json(inputs_path)
    entries_list = payload.get("entries") or []
    by_date = {e["calendar_date"]: e for e in entries_list if isinstance(e, dict) and e.get("calendar_date")}

    meta = report.setdefault("populate_meta", {})
    meta["dual_regime_inputs_json"] = str(inputs_path.resolve())

    for row in report.get("rows") or []:
        d = row.get("calendar_date")
        if not isinstance(d, str) or d not in by_date:
            continue
        ent = by_date[d]
        lo = row.setdefault("lens_outputs", {})
        as_of = datetime.fromisoformat(f"{d}T12:00:00")
        kwargs: Dict[str, Any] = {
            "as_of": as_of,
            "vector_4d": dict(ent["vector_4d"]),
            "psi_score": float(ent["psi_score"]),
            "bible_risk_score": float(ent["bible_risk_score"]),
            "workspace_root": workspace_root,
            "context_metrics": dict(ent.get("context_metrics") or {}),
            "logos_adjustment_strength": float(ent.get("logos_adjustment_strength", 0.12)),
        }
        lm = ent.get("logos_manuscript_text")
        kwargs["logos_manuscript_text"] = str(lm).strip() if lm else None
        sid = ent.get("state_id")
        kwargs["state_id"] = int(sid) if sid is not None else None

        ctx = evaluate_dual_regime_and_market_shock(**kwargs)
        snippet, snippet_meta = build_interpretation_snippet(
            ctx.interpretation,
            workspace_root=workspace_root,
        )
        lo["logos_dual_regime"] = {
            "risk_multiplier_cap": ctx.risk_multiplier_cap,
            "resonance_count": ctx.resonance_count,
            "veto_triggered": ctx.veto_triggered,
            "market_shock_confirmed": ctx.market_shock_confirmed,
            "interpretation_snippet": snippet,
            "interpretation_snippet_meta": {
                "validation_ok": snippet_meta.get("validation_ok"),
                "snippet_max_chars": snippet_meta.get("snippet_max_chars"),
                "snippet_source": snippet_meta.get("snippet_source"),
                "rules_ref": snippet_meta.get("rules_ref"),
            },
            "interpretation": ctx.interpretation,
            "inputs_ref": inputs_path.stem,
        }
    return report


def compute_populated_summary(report: Dict[str, Any]) -> Dict[str, Any]:
    """Aggregate stats when rows are filled (typically after --populate-default-samples)."""
    caps: List[float] = []
    shocks = 0
    vetos = 0
    match_mt = 0
    both_mt = 0
    full = 0
    rows = report.get("rows") or []
    for row in rows:
        lo = row.get("lens_outputs") or {}
        lg = lo.get("logos_dual_regime")
        if isinstance(lg, dict) and lg.get("risk_multiplier_cap") is not None:
            caps.append(float(lg["risk_multiplier_cap"]))
            if lg.get("market_shock_confirmed"):
                shocks += 1
            if lg.get("veto_triggered"):
                vetos += 1
        ss = lo.get("sasang_b_track")
        my = lo.get("myeongni_b_track")
        if isinstance(ss, dict) and isinstance(my, dict):
            s_mt = ss.get("mapping_target")
            m_mt = my.get("mapping_target")
            if s_mt is not None and m_mt is not None:
                both_mt += 1
                if s_mt == m_mt:
                    match_mt += 1
        if lo.get("logos_dual_regime") and lo.get("myeongni_b_track") and lo.get("sasang_b_track"):
            full += 1
    cap_stats: Dict[str, Any] = {}
    if caps:
        cap_stats = {
            "min": min(caps),
            "max": max(caps),
            "mean": sum(caps) / len(caps),
            "n": len(caps),
        }
    return {
        "risk_multiplier_cap_stats": cap_stats,
        "mapping_target_sasang_myeongni": {
            "agreement_count": match_mt,
            "rows_with_both": both_mt,
            "agreement_rate": (match_mt / both_mt) if both_mt else None,
        },
        "dual_regime_flags": {
            "market_shock_confirmed_count": shocks,
            "veto_triggered_count": vetos,
        },
        "fully_populated_rows": full,
        "total_rows": len(rows),
    }


def build_report_template(
    *,
    workspace_root: Path,
    curated: Dict[str, Any],
    contract: Dict[str, Any],
    curated_ref: str,
) -> Dict[str, Any]:
    dates: List[str] = curated.get("dates") or []
    if not isinstance(dates, list):
        raise ValueError("curated_dates: 'dates' must be a list")

    rows: List[Dict[str, Any]] = []
    for d in dates:
        rows.append(
            {
                "calendar_date": d,
                "lens_outputs": {
                    "logos_dual_regime": None,
                    "myeongni_b_track": None,
                    "sasang_b_track": None,
                },
                "fill_protocol": "manual_or_adapter; same date key across lenses",
            }
        )

    return {
        "schema": "multilens_eval_v2_thin_report_v1",
        "workspace_root": str(workspace_root.resolve()),
        "dataset_intent": curated.get("intent"),
        "dataset_intent_note": curated.get("intent_note"),
        "window_label": curated.get("window_label"),
        "asset_focus": curated.get("asset_focus"),
        "notes": curated.get("notes"),
        "contract": contract,
        "contract_ref": str(
            (workspace_root / "docs/final/artifacts/MULTILENS_EVAL_HARNESS_V2_THIN_CONTRACT.json").resolve()
        ),
        "curated_ref": curated_ref,
        "row_count": len(rows),
        "rows": rows,
    }


def run_thin_harness(
    workspace_root: Path,
    *,
    curated_path: Path | None = None,
    populate_default_samples: bool = False,
    sasang_jsonl: Path | None = None,
    myeongni_jsonl: Path | None = None,
    dual_regime_json: Path | None = None,
) -> Dict[str, Any]:
    cp = curated_path or (workspace_root / "data" / "multilens_eval" / "curated_dates_v1.json")
    curated = load_json(cp)
    cpath = workspace_root / "docs" / "final" / "artifacts" / "MULTILENS_EVAL_HARNESS_V2_THIN_CONTRACT.json"
    contract = load_json(cpath)
    report = build_report_template(
        workspace_root=workspace_root,
        curated=curated,
        contract=contract,
        curated_ref=str(cp.resolve()),
    )
    if populate_default_samples:
        sp = sasang_jsonl or (workspace_root / "data" / "multilens_eval" / "sasang_curated_overlap_v1.jsonl")
        mp = myeongni_jsonl or (workspace_root / "data" / "multilens_eval" / "myeongni_curated_overlap_v1.jsonl")
        populate_report_from_jsonl(report, sasang_jsonl=sp, myeongni_jsonl=mp)
        dr = dual_regime_json or (workspace_root / "data" / "multilens_eval" / "dual_regime_curated_overlap_v1.json")
        populate_dual_regime_from_inputs(report, workspace_root, dr)
        report["summary"] = compute_populated_summary(report)
    return report


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace-root", type=Path, default=WORKSPACE_ROOT)
    p.add_argument(
        "--curated",
        type=Path,
        default=None,
        help="curated_dates JSON (default: data/multilens_eval/curated_dates_v1.json)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write report JSON (default: stdout only)",
    )
    p.add_argument(
        "--populate-default-samples",
        action="store_true",
        help="Fill sasang/myeongni from data/multilens_eval/*_curated_overlap_v1.jsonl by calendar date",
    )
    p.add_argument("--sasang-jsonl", type=Path, default=None, help="Override sasang JSONL for --populate-default-samples")
    p.add_argument("--myeongni-jsonl", type=Path, default=None, help="Override myeongni JSONL for --populate-default-samples")
    p.add_argument(
        "--dual-regime-json",
        type=Path,
        default=None,
        help="Override dual_regime inputs JSON (default: data/multilens_eval/dual_regime_curated_overlap_v1.json)",
    )
    return p


def main() -> None:
    args = _parser().parse_args()
    root = args.workspace_root.resolve()
    report = run_thin_harness(
        root,
        curated_path=args.curated,
        populate_default_samples=args.populate_default_samples,
        sasang_jsonl=args.sasang_jsonl,
        myeongni_jsonl=args.myeongni_jsonl,
        dual_regime_json=args.dual_regime_json,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"WROTE: {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
