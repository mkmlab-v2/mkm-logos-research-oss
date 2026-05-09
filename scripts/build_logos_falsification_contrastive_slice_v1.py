#!/usr/bin/env python3
"""Build contrastive slice where theory predictions disagree."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "logos_falsification_contrastive_slice_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    doc = _load_json(path)
    rows = doc.get("rows")
    out: dict[str, dict[str, Any]] = {}
    if isinstance(rows, list):
        for r in rows:
            if isinstance(r, dict):
                oid = str(r.get("observation_id") or "")
                if oid:
                    out[oid] = r
    return out


def _hit_rate(rows: list[dict[str, Any]], arm_key: str) -> float | None:
    if not rows:
        return None
    vals = [int(r.get(f"{arm_key}_hit") or 0) for r in rows]
    return round(sum(vals) / len(vals), 6)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build contrastive disagreement slice from real OOS arm outputs.")
    ap.add_argument(
        "--logos-json",
        default="docs/final/artifacts/logos_symbolic_event_backtest_benchmark_logos_real_oos_latest.json",
    )
    ap.add_argument(
        "--counterfactual-json",
        default="docs/final/artifacts/logos_symbolic_event_backtest_benchmark_counterfactual_real_oos_latest.json",
    )
    ap.add_argument(
        "--iching-json",
        default="docs/final/artifacts/logos_symbolic_event_backtest_benchmark_iching_real_oos_latest.json",
    )
    ap.add_argument(
        "--quantum-json",
        default="docs/final/artifacts/logos_symbolic_event_backtest_benchmark_quantum_real_oos_latest.json",
    )
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    logos = _rows(ROOT / args.logos_json)
    counterfactual = _rows(ROOT / args.counterfactual_json)
    iching = _rows(ROOT / args.iching_json)
    quantum = _rows(ROOT / args.quantum_json)

    ids = set(logos.keys()) & set(counterfactual.keys()) & set(iching.keys()) & set(quantum.keys())
    contrastive_rows: list[dict[str, Any]] = []
    for oid in sorted(ids):
        l = str(logos[oid].get("predicted_direction") or "")
        c = str(counterfactual[oid].get("predicted_direction") or "")
        i = str(iching[oid].get("predicted_direction") or "")
        q = str(quantum[oid].get("predicted_direction") or "")
        preds = {l, c, i, q}
        if len(preds) <= 1:
            continue
        row = {
            "observation_id": oid,
            "label_date": str(logos[oid].get("label_date") or ""),
            "actual_direction": str(logos[oid].get("actual_direction") or ""),
            "logos_pred": l,
            "counterfactual_pred": c,
            "iching_pred": i,
            "quantum_pred": q,
            "logos_hit": int(logos[oid].get("hit") or 0),
            "counterfactual_hit": int(counterfactual[oid].get("hit") or 0),
            "iching_hit": int(iching[oid].get("hit") or 0),
            "quantum_hit": int(quantum[oid].get("hit") or 0),
        }
        contrastive_rows.append(row)

    summary = {
        "n_common_rows": len(ids),
        "n_contrastive_rows": len(contrastive_rows),
        "logos_hit_rate_contrastive": _hit_rate(contrastive_rows, "logos"),
        "counterfactual_hit_rate_contrastive": _hit_rate(contrastive_rows, "counterfactual"),
        "iching_hit_rate_contrastive": _hit_rate(contrastive_rows, "iching"),
        "quantum_hit_rate_contrastive": _hit_rate(contrastive_rows, "quantum"),
    }

    payload = {
        "schema": "logos_falsification_contrastive_slice_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "inputs": {
            "logos_json": args.logos_json,
            "counterfactual_json": args.counterfactual_json,
            "iching_json": args.iching_json,
            "quantum_json": args.quantum_json,
        },
        "summary": summary,
        "rows": contrastive_rows,
        "notes": [
            "Contrastive rows only include observations where at least one theory predicted a different direction.",
            "If n_contrastive_rows is 0, current benchmark data lacks theory-discriminating difficulty.",
        ],
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output_json), "n_contrastive_rows": len(contrastive_rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
