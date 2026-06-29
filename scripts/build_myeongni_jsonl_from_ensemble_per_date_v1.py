#!/usr/bin/env python3
"""Backfill myeongni/sasang calendar JSONL from ensemble per-date directions (B-track).

Uses causal ensemble `predicted_direction` per eval_date — not cyclic calendar stub.
Does not overwrite v1_latest sidecar automatically; outputs dedicated JSONL paths.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENSEMBLE = ROOT / "reports/btrack_ensemble_per_date_directions_30y_v1.json"
DEFAULT_MYEONGNI_OUT = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.ensemble_30y_v1.jsonl"
DEFAULT_SASANG_OUT = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.ensemble_30y_v1.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm_mapping_target(direction: str) -> str:
    d = str(direction or "").strip().lower()
    if d in ("bull", "up", "long"):
        return "bull"
    if d in ("bear", "down", "short"):
        return "bear"
    return "sideways"


def _sign_score(score: float) -> str:
    if score > 0.05:
        return "bull"
    if score < -0.05:
        return "bear"
    return "sideways"


def _load_ensemble(path: Path) -> list[dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = doc.get("rows") or []
    if not isinstance(rows, list):
        raise SystemExit(f"invalid rows in {path}")
    return [r for r in rows if isinstance(r, dict)]


def _dedupe_by_eval_date(rows: list[dict[str, Any]], instrument: str) -> dict[str, dict[str, Any]]:
    want = instrument.strip().lower()
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        ins = str(r.get("instrument") or "").strip().lower()
        if want and ins != want:
            continue
        ed = str(r.get("eval_date") or "")[:10]
        if not ed:
            continue
        out[ed] = r
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ensemble-json", type=Path, default=DEFAULT_ENSEMBLE)
    ap.add_argument("--instrument", type=str, default="btc")
    ap.add_argument("--myeongni-out", type=Path, default=DEFAULT_MYEONGNI_OUT)
    ap.add_argument("--sasang-out", type=Path, default=DEFAULT_SASANG_OUT)
    args = ap.parse_args()
    if not args.ensemble_json.is_file():
        raise SystemExit(f"missing ensemble: {args.ensemble_json}")

    by_day = _dedupe_by_eval_date(_load_ensemble(args.ensemble_json), args.instrument)
    if not by_day:
        raise SystemExit("no ensemble rows after dedupe")

    my_lines: list[dict[str, Any]] = []
    sa_lines: list[dict[str, Any]] = []
    for ed in sorted(by_day):
        row = by_day[ed]
        mt = _norm_mapping_target(str(row.get("predicted_direction") or ""))
        conf = float(row.get("confidence") or 0.0)
        lv = row.get("lens_values") if isinstance(row.get("lens_values"), dict) else {}
        ms = lv.get("myeongni_sasang") if isinstance(lv.get("myeongni_sasang"), dict) else {}
        sas_mt = _sign_score(float(ms.get("score") or 0.0)) if ms else mt
        ts_m = f"{ed}T13:00:00Z"
        ts_s = f"{ed}T12:00:00+00:00"
        my_lines.append(
            {
                "ts_utc": ts_m,
                "hypothesis_tier": "B",
                "boundary_ack": True,
                "stub": False,
                "source": "ensemble_per_date_v1",
                "eval_date": ed,
                "mapping_target": mt,
                "consistency_rate": round(min(0.95, 0.5 + conf * 0.4), 3),
                "self_contradiction_rate": round(max(0.02, 0.15 - conf * 0.1), 3),
                "run_id": "ensemble_30y_backfill_v1",
                "ensemble_confidence": conf,
            }
        )
        sa_lines.append(
            {
                "ts_utc": ts_s,
                "hypothesis_tier": "B",
                "boundary_ack": True,
                "stub": False,
                "source": "ensemble_per_date_v1",
                "eval_date": ed,
                "mapping_target": sas_mt,
                "regime_hypothesis": "phase_transition",
                "machine_readables": {
                    "ensemble_weighted_score": row.get("weighted_score"),
                },
            }
        )

    args.myeongni_out.parent.mkdir(parents=True, exist_ok=True)
    args.sasang_out.parent.mkdir(parents=True, exist_ok=True)
    args.myeongni_out.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in my_lines) + "\n",
        encoding="utf-8",
    )
    args.sasang_out.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in sa_lines) + "\n",
        encoding="utf-8",
    )
    bull = sum(1 for x in my_lines if x["mapping_target"] == "bull")
    bear = sum(1 for x in my_lines if x["mapping_target"] == "bear")
    side = len(my_lines) - bull - bear
    meta = {
        "schema": "myeongni_jsonl_from_ensemble_per_date_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "ensemble_json": str(args.ensemble_json.relative_to(ROOT)).replace("\\", "/"),
        "n_days": len(my_lines),
        "mapping_target_counts": {"bull": bull, "bear": bear, "sideways": side},
        "myeongni_out": str(args.myeongni_out.relative_to(ROOT)).replace("\\", "/"),
        "sasang_out": str(args.sasang_out.relative_to(ROOT)).replace("\\", "/"),
    }
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
