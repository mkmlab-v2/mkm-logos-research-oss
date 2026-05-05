#!/usr/bin/env python3
"""Build Logos symbolic data-hygiene audit artifact.

Produces an at-a-glance audit for:
- source_id distribution in news_observation_v1
- synthetic vs non-synthetic ratio
- backtest skip diagnostics
- promotion gate non-synthetic checks
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEWS = ROOT / "docs" / "final" / "artifacts" / "news_observation_v1_blind_split_latest.jsonl"
DEFAULT_BACKTEST = ROOT / "docs" / "final" / "artifacts" / "logos_symbolic_event_backtest_latest.json"
DEFAULT_GATE = ROOT / "docs" / "final" / "artifacts" / "logos_symbolic_event_promotion_gate_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "logos_symbolic_data_hygiene_audit_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _load_news_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        obj = json.loads(s)
        if isinstance(obj, dict) and obj.get("schema_version") == "news_observation_v1":
            rows.append(obj)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--news-jsonl", type=Path, default=DEFAULT_NEWS)
    ap.add_argument("--backtest-json", type=Path, default=DEFAULT_BACKTEST)
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--synthetic-source-ids", type=str, default="label_guided_seed,manual_seed")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--previous-audit-json",
        type=Path,
        default=DEFAULT_OUT,
        help="Prior audit artifact to compare drift against.",
    )
    ap.add_argument("--max-hit-rate-drop", type=float, default=0.05)
    ap.add_argument("--max-non-synthetic-drop", type=int, default=2)
    args = ap.parse_args()

    synthetic_ids = {x.strip() for x in str(args.synthetic_source_ids).split(",") if x.strip()}
    news_rows = _load_news_jsonl(Path(args.news_jsonl).resolve())
    backtest = _load_json(Path(args.backtest_json).resolve())
    gate = _load_json(Path(args.gate_json).resolve())

    src_counter = Counter(str(r.get("source_id") or "") for r in news_rows)
    non_synth = 0
    synth = 0
    for r in news_rows:
        sid = str(r.get("source_id") or "")
        if sid in synthetic_ids:
            synth += 1
        else:
            non_synth += 1

    summary = (backtest.get("summary") or {}) if isinstance(backtest.get("summary"), dict) else {}
    checks = (gate.get("checks") or {}) if isinstance(gate.get("checks"), dict) else {}
    metrics = (gate.get("metrics_snapshot") or {}) if isinstance(gate.get("metrics_snapshot"), dict) else {}
    decision = str(gate.get("decision") or "")
    leakage_risk = non_synth == 0
    previous_audit = _load_json(Path(args.previous_audit_json).resolve())
    prev_gate_snapshot = previous_audit.get("gate_snapshot") if isinstance(previous_audit.get("gate_snapshot"), dict) else {}
    prev_metrics = prev_gate_snapshot.get("metrics_snapshot") if isinstance(prev_gate_snapshot.get("metrics_snapshot"), dict) else {}
    prev_hit_rate = prev_metrics.get("hit_rate") if isinstance(prev_metrics.get("hit_rate"), (int, float)) else None
    curr_hit_rate = metrics.get("hit_rate") if isinstance(metrics.get("hit_rate"), (int, float)) else None
    hit_rate_drop = (float(prev_hit_rate) - float(curr_hit_rate)) if prev_hit_rate is not None and curr_hit_rate is not None else None

    prev_non_synth_eval = prev_metrics.get("non_synthetic_n_evaluated") if isinstance(prev_metrics.get("non_synthetic_n_evaluated"), int) else None
    curr_non_synth_eval = metrics.get("non_synthetic_n_evaluated") if isinstance(metrics.get("non_synthetic_n_evaluated"), int) else None
    non_synth_eval_drop = (prev_non_synth_eval - curr_non_synth_eval) if prev_non_synth_eval is not None and curr_non_synth_eval is not None else None

    drift_flags = {
        "hit_rate_drop_exceeds_threshold": bool(
            hit_rate_drop is not None and hit_rate_drop > float(args.max_hit_rate_drop)
        ),
        "non_synthetic_evaluated_drop_exceeds_threshold": bool(
            non_synth_eval_drop is not None and non_synth_eval_drop > int(args.max_non_synthetic_drop)
        ),
    }
    status = "warning" if (leakage_risk or any(drift_flags.values())) else "ok"

    out = {
        "schema": "logos_symbolic_data_hygiene_audit_v1",
        "generated_at_utc": _now(),
        "inputs": {
            "news_jsonl": str(Path(args.news_jsonl).resolve()).replace("\\", "/"),
            "backtest_json": str(Path(args.backtest_json).resolve()).replace("\\", "/"),
            "gate_json": str(Path(args.gate_json).resolve()).replace("\\", "/"),
            "synthetic_source_ids": sorted(list(synthetic_ids)),
        },
        "news_source_distribution": dict(src_counter),
        "news_counts": {
            "total_news_rows": len(news_rows),
            "synthetic_rows": synth,
            "non_synthetic_rows": non_synth,
        },
        "backtest_skip_diagnostics": {
            "skipped_counts": summary.get("skipped_counts"),
            "skipped_non_synthetic_counts": summary.get("skipped_non_synthetic_counts"),
            "non_synthetic_n_evaluated": summary.get("non_synthetic_n_evaluated"),
        },
        "gate_snapshot": {
            "decision": decision,
            "all_pass": gate.get("all_pass"),
            "metrics_snapshot": metrics,
            "checks": checks,
        },
        "drift_comparison": {
            "previous_audit_json": str(Path(args.previous_audit_json).resolve()).replace("\\", "/"),
            "previous_hit_rate": prev_hit_rate,
            "current_hit_rate": curr_hit_rate,
            "hit_rate_drop": hit_rate_drop,
            "previous_non_synthetic_n_evaluated": prev_non_synth_eval,
            "current_non_synthetic_n_evaluated": curr_non_synth_eval,
            "non_synthetic_n_evaluated_drop": non_synth_eval_drop,
            "thresholds": {
                "max_hit_rate_drop": float(args.max_hit_rate_drop),
                "max_non_synthetic_drop": int(args.max_non_synthetic_drop),
            },
            "flags": drift_flags,
        },
        "risk_flags": {
            "non_synthetic_absent_in_news": leakage_risk,
            "non_synthetic_gate_check_pass": bool(checks.get("min_non_synthetic_samples_pass") is True),
        },
        "status": status,
    }

    out_path = Path(args.output_json).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

