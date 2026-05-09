#!/usr/bin/env python3
"""Build simple walk-forward fold summary from benchmark outputs."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCH = ROOT / "docs" / "final" / "artifacts" / "logos_falsification_benchmark_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "logos_falsification_walkforward_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows_from_result(path_rel: str) -> list[dict[str, Any]]:
    p = ROOT / path_rel
    if not p.is_file():
        return []
    doc = _load_json(p)
    rows = doc.get("rows")
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def _fold_hit_rate(rows: list[dict[str, Any]], folds: int = 3) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda r: str(r.get("label_date") or ""))
    n = len(ordered)
    if n == 0:
        return []
    out: list[dict[str, Any]] = []
    for i in range(folds):
        s = (n * i) // folds
        e = (n * (i + 1)) // folds
        chunk = ordered[s:e]
        if not chunk:
            continue
        hits = sum(1 for r in chunk if int(r.get("hit") or 0) == 1)
        out.append(
            {
                "fold_id": i + 1,
                "n": len(chunk),
                "hits": hits,
                "hit_rate": round(hits / len(chunk), 6),
                "start_label_date": str(chunk[0].get("label_date") or ""),
                "end_label_date": str(chunk[-1].get("label_date") or ""),
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Build walk-forward summary for logos falsification benchmark.")
    ap.add_argument("--benchmark-json", type=Path, default=DEFAULT_BENCH)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    bench = _load_json(args.benchmark_json)
    arms = bench.get("arms")
    if not isinstance(arms, list):
        raise SystemExit("invalid benchmark: arms missing")

    wf: dict[str, Any] = {}
    for arm in arms:
        if not isinstance(arm, dict):
            continue
        arm_id = str(arm.get("arm_id") or "")
        result_json = arm.get("result_json")
        if not arm_id or not isinstance(result_json, str):
            continue
        rows = _rows_from_result(result_json)
        wf[arm_id] = _fold_hit_rate(rows, folds=3)

    def _mean_rate(arm_id: str) -> float | None:
        vals = [f.get("hit_rate") for f in wf.get(arm_id, []) if isinstance(f.get("hit_rate"), (float, int))]
        if not vals:
            return None
        return round(sum(float(v) for v in vals) / len(vals), 6)

    logos_oos = _mean_rate("logos_primary_oos")
    counterfactual_oos = _mean_rate("counterfactual_variant_v1_oos")
    iching_oos = _mean_rate("iching_adapter_v1_oos")
    quantum_oos = _mean_rate("quantum_adapter_v1_oos")
    dummy_oos = _mean_rate("dummy_negative_control_oos")

    payload = {
        "schema": "logos_falsification_walkforward_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "benchmark_json": str(args.benchmark_json),
        "walkforward_folds": wf,
        "mean_oos_fold_hit_rate": {
            "logos_primary_oos": logos_oos,
            "counterfactual_variant_v1_oos": counterfactual_oos,
            "iching_adapter_v1_oos": iching_oos,
            "quantum_adapter_v1_oos": quantum_oos,
            "dummy_negative_control_oos": dummy_oos,
        },
        "comparative_gate": {
            "logos_minus_counterfactual_oos": round(logos_oos - counterfactual_oos, 6) if isinstance(logos_oos, float) and isinstance(counterfactual_oos, float) else None,
            "logos_minus_iching_oos": round(logos_oos - iching_oos, 6) if isinstance(logos_oos, float) and isinstance(iching_oos, float) else None,
            "logos_minus_quantum_oos": round(logos_oos - quantum_oos, 6) if isinstance(logos_oos, float) and isinstance(quantum_oos, float) else None,
            "logos_minus_dummy_oos": round(logos_oos - dummy_oos, 6) if isinstance(logos_oos, float) and isinstance(dummy_oos, float) else None,
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
