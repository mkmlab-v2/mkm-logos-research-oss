#!/usr/bin/env python3
"""Size/confidence auxiliary ablation — headline direction UNCHANGED (research_only).

Leading sensors do NOT alter predicted_direction. Reports:
  - baseline headline (unchanged)
  - overheat / size_multiplier distribution
  - directional hit rate by |composite| tercile (observation only)
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JOINED = ROOT / "reports/btrack_phase3_leading_sensors_joined_v1_latest.jsonl"
DEFAULT_OUT = ROOT / "reports/btrack_phase3_size_confidence_aux_ablation_v1_latest.json"
SCHEMA = "btrack_phase3_size_confidence_aux_ablation_v1"

def _load_lib():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "btrack_phase3_leading_sensors_lib_v1",
        ROOT / "scripts" / "btrack_phase3_leading_sensors_lib_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_lib = _load_lib()
ALERT1 = _lib.ALERT1
hit_metrics = _lib.hit_metrics
overheat_score = _lib.overheat_score
read_jsonl = _lib.read_jsonl
rows_baseline = _lib.rows_baseline
size_multiplier_from_overheat = _lib.size_multiplier_from_overheat
tercile_buckets = _lib.tercile_buckets


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def _aux_enrichment(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        comp = r.get("leading_composite_signed_flow_z")
        comp_f = float(comp) if isinstance(comp, (int, float)) else None
        oh = overheat_score(comp_f)
        sm = size_multiplier_from_overheat(oh)
        row = dict(r)
        row["aux_overheat_score"] = oh
        row["aux_size_multiplier"] = sm
        row["aux_confidence_dampen"] = round(1.0 - sm, 6) if sm is not None else None
        out.append(row)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--joined-jsonl", type=Path, default=DEFAULT_JOINED)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--window-label", default="30d")
    args = ap.parse_args(argv)

    if not args.joined_jsonl.is_file():
        print(f"MISSING: {args.joined_jsonl}", file=__import__("sys").stderr)
        return 2

    raw = read_jsonl(args.joined_jsonl)
    enriched = _aux_enrichment(raw)
    baseline_m = hit_metrics(rows_baseline(raw))

    multipliers = [r["aux_size_multiplier"] for r in enriched if r.get("aux_size_multiplier") is not None]
    mean_sm = round(sum(multipliers) / len(multipliers), 6) if multipliers else None
    n_high_overheat = sum(1 for r in enriched if (r.get("aux_overheat_score") or 0) >= 0.5)

    payload = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "window": args.window_label,
        "alert_1_threshold": ALERT1,
        "inputs": {"joined_jsonl": _rel(args.joined_jsonl)},
        "headline_unchanged": {
            "note_ko": "predicted_direction 미변경 — ALERT_1 헤드라인은 baseline과 동일 선상.",
            "metrics": baseline_m,
        },
        "aux_size_confidence": {
            "mean_size_multiplier": mean_sm,
            "n_high_overheat_days": n_high_overheat,
            "n_rows": len(enriched),
            "tercile_directional_hit": tercile_buckets(raw),
            "role_ko": "펀딩·롱숏 = 온도계; 베팅 사이즈·confidence 감쇠 보조만.",
        },
        "verdict": {
            "direction_promotion_from_sensors": False,
            "track_a_promotion": "NO",
            "auto_promote": False,
            "apply_prod": False,
            "recommended_integration": "insight_sidecar_aux_fields_only",
        },
        "operator_lines": [
            f"- [MKM-SIZE-AUX] headline_hit={baseline_m.get('price_directional_hit_rate')} unchanged",
            f"- [MKM-SIZE-AUX] mean_size_mult={mean_sm} high_overheat_days={n_high_overheat}",
        ],
        "rerun": "py scripts/run_btrack_phase3_size_confidence_aux_ablation_v1.py",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"  headline_hit={baseline_m.get('price_directional_hit_rate')} mean_size_mult={mean_sm}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
