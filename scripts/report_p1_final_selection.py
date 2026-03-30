#!/usr/bin/env python3
"""Build a single final-selection report from three P1 A/B profiles."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"

EFF = ART / "MULTILENS_P1_AB_EFFICIENCY_V1.json"
INTN = ART / "MULTILENS_P1_AB_INTENSITY_V1.json"
BAL = ART / "MULTILENS_P1_AB_BALANCED_V1.json"
OUT = ART / "MULTILENS_P1_AB_FINAL_SELECTION_V1.json"


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Create final winner report from P1 A/B profile artifacts.")
    p.add_argument("--efficiency", default=str(EFF), help="Efficiency profile JSON path")
    p.add_argument("--intensity", default=str(INTN), help="Intensity profile JSON path")
    p.add_argument("--balanced", default=str(BAL), help="Balanced profile JSON path")
    p.add_argument("--output", default=str(OUT), help="Output final selection JSON path")
    return p


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _snapshot(doc: dict[str, Any], name: str) -> dict[str, Any]:
    best = doc.get("best_candidate") or {}
    gate = doc.get("gate_contract") or {}
    summary = doc.get("summary") or {}
    row = {
        "profile_name": name,
        "schema": doc.get("schema"),
        "profile": doc.get("profile"),
        "candidate_count": summary.get("candidate_count"),
        "passing_count": summary.get("passing_count"),
        "saving_rate_min": gate.get("saving_rate_min"),
        "jaccard_drop_pp_max": gate.get("jaccard_drop_pp_max"),
        "sensitive_integrity_min": gate.get("sensitive_integrity_min"),
        "best_candidate": {
            "strategy": best.get("strategy"),
            "intensity": best.get("intensity"),
            "use_hangul_principle": best.get("use_hangul_principle"),
            "global_token_saving_rate": best.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": best.get("avg_reconstruction_fidelity_jaccard"),
            "jaccard_drop_pp": best.get("jaccard_drop_pp"),
            "avg_sensitive_integrity": best.get("avg_sensitive_integrity"),
            "gate_ok": best.get("gate_ok"),
            "balanced_composite": best.get("balanced_composite"),
        },
    }
    if name == "balanced":
        row["balanced_weights"] = doc.get("balanced_weights")
    return row


def _pick_winner(rows: list[dict[str, Any]]) -> dict[str, Any]:
    # 1) Prefer balanced winner when gate_ok=True.
    # 2) Otherwise choose gate_ok=True with highest saving, then lower drop.
    # 3) Last resort: highest saving regardless of gate.
    by_name = {r["profile_name"]: r for r in rows}
    bal = by_name.get("balanced")
    if bal and bool((bal.get("best_candidate") or {}).get("gate_ok")):
        return {"winner_profile": "balanced", "reason": "balanced gate_ok and composite-driven anchor", "winner": bal}

    gate_ok_rows = [r for r in rows if bool((r.get("best_candidate") or {}).get("gate_ok"))]
    if gate_ok_rows:
        gate_ok_rows.sort(
            key=lambda r: (
                float((r.get("best_candidate") or {}).get("global_token_saving_rate") or 0.0),
                -float((r.get("best_candidate") or {}).get("jaccard_drop_pp") or 0.0),
            ),
            reverse=True,
        )
        winner = gate_ok_rows[0]
        return {"winner_profile": winner["profile_name"], "reason": "fallback: highest saving among gate_ok winners", "winner": winner}

    rows.sort(
        key=lambda r: float((r.get("best_candidate") or {}).get("global_token_saving_rate") or 0.0),
        reverse=True,
    )
    winner = rows[0]
    return {"winner_profile": winner["profile_name"], "reason": "no gate_ok winner; highest saving fallback", "winner": winner}


def main() -> int:
    args = _parser().parse_args()
    eff_doc = _load(Path(args.efficiency).resolve())
    int_doc = _load(Path(args.intensity).resolve())
    bal_doc = _load(Path(args.balanced).resolve())

    rows = [
        _snapshot(eff_doc, "efficiency_first"),
        _snapshot(int_doc, "intensity_first"),
        _snapshot(bal_doc, "balanced"),
    ]
    picked = _pick_winner(rows)

    out_doc = {
        "schema": "multilens_p1_ab_final_selection_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "source_refs": {
            "efficiency": "docs/final/artifacts/MULTILENS_P1_AB_EFFICIENCY_V1.json",
            "intensity": "docs/final/artifacts/MULTILENS_P1_AB_INTENSITY_V1.json",
            "balanced": "docs/final/artifacts/MULTILENS_P1_AB_BALANCED_V1.json",
        },
        "profiles": rows,
        "selection": picked,
    }

    out_path = Path(args.output).resolve()
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    print(f"WINNER: {picked['winner_profile']} ({picked['reason']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
