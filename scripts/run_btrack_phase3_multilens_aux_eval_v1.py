#!/usr/bin/env python3
"""Evaluate multilens agreement vs price headline + Phase3 size aux (research_only).

Does not mutate predicted_direction or prod score.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JOINED = ROOT / "reports/btrack_phase3_leading_sensors_joined_v1_latest.jsonl"
DEFAULT_PANEL = ROOT / "reports/btrack_phase3_per_date_lens_panel_v1_latest.jsonl"
DEFAULT_OUT = ROOT / "reports/btrack_phase3_multilens_aux_eval_v1_latest.json"
SCHEMA = "btrack_phase3_multilens_aux_eval_v1"


def _load_lib():
    spec = importlib.util.spec_from_file_location(
        "btrack_phase3_leading_sensors_lib_v1",
        ROOT / "scripts" / "btrack_phase3_leading_sensors_lib_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        if isinstance(o, dict):
            rows.append(o)
    return rows


def _index(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for r in rows:
        ed = str(r.get("eval_date") or "")[:10]
        ins = str(r.get("instrument") or "").strip().lower()
        if ed and ins:
            out[(ed, ins)] = r
    return out


def _enrich_joined(joined: list[dict[str, Any]], panel_idx: dict[tuple[str, str], dict[str, Any]], lib: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in joined:
        ed = str(r.get("eval_date") or "")[:10]
        ins = str(r.get("instrument") or "").strip().lower()
        row = dict(r)
        comp = r.get("leading_composite_signed_flow_z")
        comp_f = float(comp) if isinstance(comp, (int, float)) else None
        oh = lib.overheat_score(comp_f)
        row["aux_overheat_score"] = oh
        row["aux_size_multiplier"] = lib.size_multiplier_from_overheat(oh)
        pr = panel_idx.get((ed, ins))
        if pr:
            row["lens_panel"] = {
                "lens_majority_sign": (pr.get("lens") or {}).get("lens_majority_sign"),
                "lens_disagrees_with_price_pred": pr.get("lens_disagrees_with_price_pred"),
                "non_neutral_lens_count": (pr.get("lens") or {}).get("non_neutral_lens_count"),
            }
        out.append(row)
    return out


def _hit_subset(rows: list[dict[str, Any]], lib: Any, pred) -> dict[str, Any]:
    subset = [r for r in rows if pred(r)]
    if not subset:
        return {"n": 0, "metrics": None}
    base = lib.rows_baseline(subset)
    return {"n": len(subset), "metrics": lib.hit_metrics(base)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--joined-jsonl", type=Path, default=DEFAULT_JOINED)
    ap.add_argument("--lens-panel-jsonl", type=Path, default=DEFAULT_PANEL)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--window-label", default="30d")
    args = ap.parse_args(argv)

    if not args.joined_jsonl.is_file():
        print(f"MISSING joined: {args.joined_jsonl}", file=__import__("sys").stderr)
        return 2
    if not args.lens_panel_jsonl.is_file():
        print(f"MISSING panel: {args.lens_panel_jsonl}", file=__import__("sys").stderr)
        return 2

    lib = _load_lib()
    joined = _read_jsonl(args.joined_jsonl)
    panel_idx = _index(_read_jsonl(args.lens_panel_jsonl))
    enriched = _enrich_joined(joined, panel_idx, lib)
    baseline_m = lib.hit_metrics(lib.rows_baseline(joined))

    agree = _hit_subset(
        enriched,
        lib,
        lambda r: not r.get("lens_panel") or not r["lens_panel"].get("lens_disagrees_with_price_pred"),
    )
    disagree = _hit_subset(
        enriched,
        lib,
        lambda r: isinstance(r.get("lens_panel"), dict) and r["lens_panel"].get("lens_disagrees_with_price_pred"),
    )
    high_oh = _hit_subset(enriched, lib, lambda r: (r.get("aux_overheat_score") or 0) >= 0.5)
    low_oh = _hit_subset(enriched, lib, lambda r: (r.get("aux_overheat_score") or 0) < 0.5)

    payload = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "window": args.window_label,
        "inputs": {
            "joined_jsonl": _rel(args.joined_jsonl),
            "lens_panel_jsonl": _rel(args.lens_panel_jsonl),
        },
        "headline_unchanged": {
            "note_ko": "predicted_direction·prod score 미변경.",
            "metrics": baseline_m,
        },
        "slices": {
            "lens_agrees_or_no_panel": agree,
            "lens_disagrees_with_price_pred": disagree,
            "aux_high_overheat": high_oh,
            "aux_low_overheat": low_oh,
        },
        "verdict": {
            "direction_promotion_from_multilens": False,
            "track_a_promotion": "NO",
            "apply_prod": False,
            "recommended_use": "size_confidence_and_abstain_overlay_research_only",
            "shield_as_direction_gate": "RETIRED",
        },
        "operator_lines": [
            f"- [MKM-ML-AUX] headline_hit={baseline_m.get('price_directional_hit_rate')}",
            f"- [MKM-ML-AUX] lens_disagree_n={(disagree.get('n') or 0)}",
            f"- [MKM-ML-AUX] high_overheat_n={(high_oh.get('n') or 0)}",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
