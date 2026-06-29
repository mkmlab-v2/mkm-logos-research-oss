#!/usr/bin/env python3
"""Triage B-track compression grid sweep — economy cell drill-down + cost sim cross-check."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
EXP = ROOT / "experiments" / "compression_pipeline_grid_sweep_v1"
DEFAULT_SUMMARY = EXP / "results" / "compression_pipeline_grid_sweep_v1_latest.json"
DEFAULT_DIFF = EXP / "results" / "compression_pipeline_grid_sweep_golden40_diff_v1_latest.json"
DEFAULT_COST = EXP / "results" / "track_a_conversational_cost_simulation_baseline_linked.json"
DEFAULT_OUT = EXP / "results" / "compression_pipeline_grid_sweep_triage_v1_latest.json"
ACTIVE = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _domain_map_from_active(active: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in (active.get("compression_metrics") or {}).get("cases") or []:
        cid = row.get("id")
        if not cid:
            continue
        route = row.get("route") or {}
        dom = row.get("domain") or route.get("domain") or "unknown"
        out[str(cid)] = str(dom)
    return out


def _summarize_cell(
    cell_id: str,
    rows: list[dict[str, Any]],
    domain_by_id: dict[str, str],
) -> dict[str, Any]:
    changed = [r for r in rows if abs(r.get("delta_saving", 0)) > 1e-9 or abs(r.get("delta_jaccard", 0)) > 1e-9]
    saving_up = [r for r in rows if r.get("delta_saving", 0) > 1e-9]
    jaccard_down = [r for r in rows if r.get("delta_jaccard", 0) < -1e-9]
    both_up = [r for r in rows if r.get("delta_saving", 0) > 1e-9 and r.get("delta_jaccard", 0) > 1e-9]

    def _enrich(r: dict[str, Any]) -> dict[str, Any]:
        cid = str(r["id"])
        return {**r, "domain": domain_by_id.get(cid, "unknown")}

    by_domain: dict[str, dict[str, float]] = {}
    for r in rows:
        dom = domain_by_id.get(str(r["id"]), "unknown")
        slot = by_domain.setdefault(
            dom,
            {"case_count": 0, "sum_delta_saving": 0.0, "sum_delta_jaccard": 0.0},
        )
        slot["case_count"] += 1
        slot["sum_delta_saving"] += float(r.get("delta_saving") or 0)
        slot["sum_delta_jaccard"] += float(r.get("delta_jaccard") or 0)
    for dom, slot in by_domain.items():
        n = slot["case_count"] or 1
        slot["avg_delta_saving"] = round(slot.pop("sum_delta_saving") / n, 6)
        slot["avg_delta_jaccard"] = round(slot.pop("sum_delta_jaccard") / n, 6)

    return {
        "cell_id": cell_id,
        "case_count": len(rows),
        "changed_case_count": len(changed),
        "saving_increase_ids": [r["id"] for r in saving_up],
        "jaccard_decrease_ids": [r["id"] for r in jaccard_down],
        "both_axes_up_ids": [r["id"] for r in both_up],
        "top_saving_gains": sorted(
            [_enrich(r) for r in rows if r.get("delta_saving", 0) > 1e-9],
            key=lambda x: -x["delta_saving"],
        )[:10],
        "top_jaccard_losses": sorted(
            [_enrich(r) for r in rows if r.get("delta_jaccard", 0) < -1e-9],
            key=lambda x: x["delta_jaccard"],
        )[:10],
        "by_domain_avg_delta": dict(sorted(by_domain.items())),
    }


def _cost_sim_economy_projection(
    cost_doc: dict[str, Any] | None,
    frozen_saving: float,
    economy_saving: float,
) -> dict[str, Any] | None:
    if not cost_doc:
        return None
    baseline_tokens = float(cost_doc.get("hypothesis_monthly_baseline_tokens") or 0)
    if baseline_tokens <= 0:
        return None
    frozen_after = baseline_tokens * (1.0 - frozen_saving)
    economy_after = baseline_tokens * (1.0 - economy_saving)
    return {
        "hypothesis_monthly_baseline_tokens": baseline_tokens,
        "frozen_active_after_tokens": round(frozen_after),
        "economy_cell_after_tokens": round(economy_after),
        "delta_tokens_vs_frozen_active": round(frozen_after - economy_after),
        "note": "Scenario-only; not billing or live routing. correlation_claim_allowed=false.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build compression grid sweep triage (research_only).")
    ap.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--diff", type=Path, default=DEFAULT_DIFF)
    ap.add_argument("--cost-sim", type=Path, default=DEFAULT_COST)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--mirror-pilot", action="store_true")
    args = ap.parse_args()

    for path in (args.summary, args.diff, ACTIVE):
        if not path.is_file():
            print(f"ABORT: missing {path}")
            return 2

    summary = _load(args.summary)
    diff_doc = _load(args.diff)
    active = _load(ACTIVE)
    cost_doc = _load(args.cost_sim) if args.cost_sim.is_file() else None
    domain_by_id = _domain_map_from_active(active)

    frozen = summary.get("frozen_baseline") or {}
    frozen_metrics = frozen.get("metrics") or {}
    frozen_saving = float(frozen_metrics.get("global_token_saving_rate") or 0)

    cells = {c["cell_id"]: c for c in summary.get("cells") or [] if c.get("cell_id")}
    economy_cell = cells.get("profile_economy") or {}
    economy_metrics = economy_cell.get("metrics") or {}
    economy_saving = float(economy_metrics.get("global_token_saving_rate") or 0)

    triage_cells: dict[str, Any] = {}
    for cell_id, rows in (diff_doc.get("cells") or {}).items():
        if cell_id in ("profile_economy", "profile_fidelity"):
            triage_cells[cell_id] = _summarize_cell(cell_id, rows, domain_by_id)

    out = {
        "schema": "compression_pipeline_grid_sweep_triage_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "promote_active": False,
        "correlation_claim_allowed": False,
        "summary_pointer": str(args.summary.relative_to(ROOT)).replace("\\", "/"),
        "diff_pointer": str(args.diff.relative_to(ROOT)).replace("\\", "/"),
        "frozen_baseline_pointer": str(ACTIVE.relative_to(ROOT)).replace("\\", "/"),
        "economy_cell_gate": economy_cell.get("gate"),
        "economy_cell_metrics": economy_metrics,
        "profile_triage": triage_cells,
        "cost_sim_cross_check": {
            "cost_sim_pointer": (
                str(args.cost_sim.relative_to(ROOT)).replace("\\", "/") if cost_doc else None
            ),
            "cost_sim_gate_decision": cost_doc.get("gate_decision") if cost_doc else None,
            "frozen_active_saving_rate": frozen_saving,
            "economy_cell_saving_rate": economy_saving,
            "delta_saving_pp": round((economy_saving - frozen_saving) * 100.0, 4),
            "economy_projection": _cost_sim_economy_projection(cost_doc, frozen_saving, economy_saving),
        },
        "next_actions_research_only": [
            "Review profile_economy top_saving_gains vs domain_relaxed signoff allowlist.",
            "Confirm economy run_config matches intended promotion candidate (strategy A, bridge OFF).",
            "Human sign-off before any active report write; cost sim alone is insufficient.",
        ],
        "forbidden": summary.get("guardrails") or [],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")

    if args.mirror_pilot:
        pilot = ROOT / "reports" / "constitution" / "btrack_pilot" / "compression_pipeline_grid_sweep_triage_v1_latest.json"
        pilot.parent.mkdir(parents=True, exist_ok=True)
        pilot.write_text(args.out.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"WROTE: {pilot}")

    econ = triage_cells.get("profile_economy") or {}
    print(
        f"economy changed={econ.get('changed_case_count')} "
        f"saving_up={len(econ.get('saving_increase_ids') or [])} "
        f"both_up={len(econ.get('both_axes_up_ids') or [])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
