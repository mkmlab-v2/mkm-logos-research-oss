#!/usr/bin/env python3
"""Build Field KOSPI event graph snapshot from disk SSOT [HYPO][B-track]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_REGIME = ROOT / "data/regimes/regime_map.json"
DEFAULT_OVERNIGHT = ROOT / "docs/final/artifacts/global_market_overnight_signals_v1_latest.json"
DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_SCIENCE = ROOT / "reports/btrack_science_core_per_date_kospi_v1.jsonl"
DEFAULT_MACRO = ROOT / "reports/kospi_june2026_macro_daily_refresh_poc_latest.json"
DEFAULT_OUT = ROOT / "reports/field_kospi_event_graph_v1_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/field_kospi_event_graph_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _last_jsonl(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    last = None
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            last = obj
    return last


def _eval_tail_row(eval_doc: dict[str, Any] | None) -> dict[str, Any] | None:
    rows = (eval_doc or {}).get("rows")
    if not isinstance(rows, list) or not rows:
        return None
    tail = rows[-1]
    return tail if isinstance(tail, dict) else None


def build_graph(
    *,
    regime_map: Path,
    overnight: Path,
    eval_json: Path,
    science_jsonl: Path,
    macro_poc: Path,
) -> dict[str, Any]:
    regime = _read_json(regime_map)
    ov = _read_json(overnight)
    ev = _read_json(eval_json)
    sci = _last_jsonl(science_jsonl)
    macro = _read_json(macro_poc)
    tail = _eval_tail_row(ev)

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    if tail:
        nodes.append(
            {
                "node_id": "evt_ohlcv_tail",
                "kind": "ohlcv_shock",
                "session_date": tail.get("session_date"),
                "close": tail.get("actual_close"),
                "return_pct": tail.get("daily_return_pct"),
                "direction": tail.get("actual_direction"),
            }
        )
        nodes.append(
            {
                "node_id": "evt_prophecy_miss",
                "kind": "forecast_band_miss",
                "predicted": tail.get("predicted_direction"),
                "band_hit": tail.get("band_hit"),
            }
        )
        edges.append(
            {
                "edge_id": "e_miss_on_shock",
                "src": "evt_ohlcv_tail",
                "dst": "evt_prophecy_miss",
                "relation": "triggered_by",
            }
        )

    if ov:
        nodes.append(
            {
                "node_id": "evt_overnight",
                "kind": "overnight_composite",
                "composite_tilt": ov.get("composite_tilt"),
                "ts_utc": ov.get("generated_at_utc") or ov.get("ts_utc"),
            }
        )
        if tail:
            edges.append(
                {
                    "edge_id": "e_overnight_field",
                    "src": "evt_overnight",
                    "dst": "evt_ohlcv_tail",
                    "relation": "context_for",
                }
            )

    if sci:
        nodes.append(
            {
                "node_id": "evt_science_core",
                "kind": "science_core_row",
                "session_date": sci.get("session_date"),
                "price_score": ((sci.get("components") or {}).get("price") or {}).get("direction_score"),
            }
        )

    if regime and isinstance(regime.get("regimes"), dict):
        for rid in list(regime["regimes"].keys())[:6]:
            nodes.append({"node_id": f"regime_{rid}", "kind": "regime_map_ref", "regime_id": rid})

    macro_samples = (macro or {}).get("macro_per_date_samples")
    if isinstance(macro_samples, list) and macro_samples:
        last_m = macro_samples[-1]
        if isinstance(last_m, dict):
            nodes.append(
                {
                    "node_id": "evt_macro_carry",
                    "kind": "macro_per_date",
                    "session_date": last_m.get("session_date"),
                    "direction": last_m.get("per_date_macro_direction"),
                    "decision_state": last_m.get("decision_state"),
                }
            )

    return {
        "schema": "field_kospi_event_graph_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "gating_layer": "field",
        "nodes": nodes,
        "edges": edges,
        "summary_ko": "OHLCV tail + overnight + science_core + regime_map refs — Field 이벤트 평면 PoC",
        "pointers": {
            "regime_map": str(regime_map.as_posix()),
            "overnight": str(overnight.as_posix()),
            "eval": str(eval_json.as_posix()),
            "science_jsonl": str(science_jsonl.as_posix()),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--regime-map", type=Path, default=DEFAULT_REGIME)
    ap.add_argument("--overnight", type=Path, default=DEFAULT_OVERNIGHT)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--science-jsonl", type=Path, default=DEFAULT_SCIENCE)
    ap.add_argument("--macro-poc", type=Path, default=DEFAULT_MACRO)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build_graph(
        regime_map=args.regime_map,
        overnight=args.overnight,
        eval_json=args.eval_json,
        science_jsonl=args.science_jsonl,
        macro_poc=args.macro_poc,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DEFAULT_ART.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_ART.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "nodes": len(doc["nodes"]), "edges": len(doc["edges"]), "out": str(args.out_json)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
