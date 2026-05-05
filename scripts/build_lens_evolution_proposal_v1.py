#!/usr/bin/env python3
"""Emit lens_evolution_proposal_latest.json (HITL-only, research_only).

Reads per-lens scoreboard + optional dual-leg Track C brief. Produces proposal text
and structured items only; never auto-applies weights or live config.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "lens_evolution_proposal_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _rel(root: Path, p: Path) -> str:
    try:
        return str(p.resolve().relative_to(root))
    except ValueError:
        return str(p)


def _sorted_lens_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(r: dict[str, Any]) -> tuple[float, str]:
        hr = r.get("price_directional_hit_rate")
        if isinstance(hr, (int, float)):
            return (-float(hr), str(r.get("lens_id") or ""))
        return (1.0, str(r.get("lens_id") or ""))

    return sorted(rows, key=key)


def _eligible_for_fusion_spread(r: dict[str, Any]) -> bool:
    """Fusion-stub legs only (not ensemble, not runtime_meta price/macro/news snapshots)."""
    src = str(r.get("prediction_source") or "")
    return "independent_lens_fusion_stub" in src


def _build_proposals_for_leg(
    *,
    instrument: str,
    lenses: list[dict[str, Any]],
    hit_gap_threshold: float,
    min_n: int,
    ensemble_weak_threshold: float,
) -> list[dict[str, Any]]:
    proposals: list[dict[str, Any]] = []
    ranked = _sorted_lens_rows([r for r in lenses if _eligible_for_fusion_spread(r)])
    strong = [r for r in ranked if isinstance(r.get("n_evaluated"), int) and r["n_evaluated"] >= min_n]
    if len(strong) >= 2:
        best, worst = strong[0], strong[-1]
        bhr = best.get("price_directional_hit_rate")
        whr = worst.get("price_directional_hit_rate")
        if isinstance(bhr, (int, float)) and isinstance(whr, (int, float)):
            gap = float(bhr) - float(whr)
            if gap >= hit_gap_threshold:
                proposals.append(
                    {
                        "id": f"weight_review_{instrument}_{best.get('lens_id')}_vs_{worst.get('lens_id')}",
                        "kind": "fusion_weight_review",
                        "instrument": instrument,
                        "requires_human_approval": True,
                        "rationale": (
                            f"Snapshot counterfactual hit-rate spread on {instrument}: "
                            f"{best.get('lens_id')}={bhr:.4f} vs {worst.get('lens_id')}={whr:.4f} "
                            f"(gap {gap:.4f}, n>={min_n}). Consider manual fusion weight tilt — not auto-applied."
                        ),
                        "evidence": {
                            "best_lens_id": best.get("lens_id"),
                            "worst_lens_id": worst.get("lens_id"),
                            "hit_rate_gap": round(gap, 6),
                            "confidence_band_best": best.get("confidence_band"),
                            "confidence_band_worst": worst.get("confidence_band"),
                        },
                    }
                )

    for r in lenses:
        if str(r.get("lens_id") or "") != "ensemble_hypothesis":
            continue
        hr = r.get("price_directional_hit_rate")
        n = r.get("n_evaluated")
        if not isinstance(hr, (int, float)) or not isinstance(n, int):
            continue
        if float(hr) < ensemble_weak_threshold and n >= min_n:
            proposals.append(
                {
                    "id": f"conservative_defense_{instrument}_ensemble_weak",
                    "kind": "conservative_defense",
                    "instrument": instrument,
                    "requires_human_approval": True,
                    "rationale": (
                        f"Ensemble hypothesis directional hit on {instrument} is {float(hr):.4f} "
                        f"(n={n}) below weak threshold {ensemble_weak_threshold}. "
                        "Proposal: tighten B-track gates or defer fusion promotion — HITL only."
                    ),
                    "evidence": {
                        "ensemble_hit_rate": float(hr),
                        "n_evaluated": n,
                        "threshold": ensemble_weak_threshold,
                    },
                }
            )
        break

    return proposals


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument(
        "--per-lens-json",
        type=Path,
        default=None,
        help="Default: docs/final/artifacts/prophecy_hit_rate_per_lens_latest.json",
    )
    ap.add_argument(
        "--dual-leg-brief-json",
        type=Path,
        default=None,
        help="Default: docs/final/artifacts/trackc_prophecy_dual_leg_brief_latest.json",
    )
    ap.add_argument("--hit-gap-threshold", type=float, default=0.10)
    ap.add_argument("--min-n-for-proposal", type=int, default=20)
    ap.add_argument("--ensemble-weak-threshold", type=float, default=0.50)
    ap.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Default: docs/final/artifacts/lens_evolution_proposal_latest.json",
    )
    ns = ap.parse_args()
    root = Path(ns.workspace_root).expanduser().resolve()
    per_path = ns.per_lens_json or (root / "docs/final/artifacts/prophecy_hit_rate_per_lens_latest.json")
    brief_path = ns.dual_leg_brief_json or (root / "docs/final/artifacts/trackc_prophecy_dual_leg_brief_latest.json")
    out_path = ns.output or (root / "docs/final/artifacts/lens_evolution_proposal_latest.json")

    per_doc = _load_json(per_path)
    if not per_doc or not isinstance(per_doc.get("legs"), dict):
        print(f"ERROR: missing or invalid per-lens json: {per_path}", file=__import__("sys").stderr)
        return 2

    brief = _load_json(brief_path)
    all_proposals: list[dict[str, Any]] = []
    for inst, leg in per_doc["legs"].items():
        if not isinstance(leg, dict):
            continue
        lenses = leg.get("lenses")
        if not isinstance(lenses, list):
            continue
        lens_rows = [x for x in lenses if isinstance(x, dict)]
        all_proposals.extend(
            _build_proposals_for_leg(
                instrument=str(inst),
                lenses=lens_rows,
                hit_gap_threshold=float(ns.hit_gap_threshold),
                min_n=int(ns.min_n_for_proposal),
                ensemble_weak_threshold=float(ns.ensemble_weak_threshold),
            )
        )

    dual_context: dict[str, Any] | None = None
    if brief:
        dual_context = {
            "schema": brief.get("schema"),
            "delta_btc_minus_kospi_hit_rate": (brief.get("delta") or {}).get("btc_minus_kospi_hit_rate"),
            "legs": brief.get("legs"),
            "overall_hit_rate": (brief.get("overall") or {}).get("price_directional_hit_rate"),
        }

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "requires_human_approval": True,
        "zeroing_note": "Proposals are advisory; no automatic weight or routing changes.",
        "inputs": {
            "per_lens_json": _rel(root, per_path),
            "dual_leg_brief_json": _rel(root, brief_path) if brief_path.is_file() else None,
            "hit_gap_threshold": float(ns.hit_gap_threshold),
            "min_n_for_proposal": int(ns.min_n_for_proposal),
            "ensemble_weak_threshold": float(ns.ensemble_weak_threshold),
        },
        "dual_leg_context": dual_context,
        "proposals": all_proposals,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()} ({len(all_proposals)} proposals)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
