#!/usr/bin/env python3
"""Aggregate multiple Logos symbolic backtest JSON outputs into one reliability summary."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "logos_symbolic_event_backtest_bundle_summary_v1.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build backtest bundle summary.")
    ap.add_argument(
        "--inputs",
        type=str,
        nargs="*",
        default=[],
        help="Paths to backtest JSON files (or use --auto-artifacts)",
    )
    ap.add_argument(
        "--auto-artifacts",
        action="store_true",
        help="Load standard artifact names from docs/final/artifacts/",
    )
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    tags = [
        "latest",
        "contrastive_challenge",
        "contrastive_expanded",
        "split1",
        "split2",
        "split3",
        "blind_split",
        "blind_split_hardset",
    ]
    if args.auto_artifacts:
        paths = [
            ROOT / "docs" / "final" / "artifacts" / f"logos_symbolic_event_backtest_{t}_latest.json"
            for t in tags
        ]
    elif args.inputs:
        paths = [ROOT / p if not Path(p).is_absolute() else Path(p) for p in args.inputs]
    else:
        paths = [
            ROOT / "docs" / "final" / "artifacts" / f"logos_symbolic_event_backtest_{t}_latest.json"
            for t in tags
        ]

    rows: list[dict[str, Any]] = []
    unique_rows_by_key: dict[str, dict[str, Any]] = {}
    unique_non_syn_by_key: dict[str, dict[str, Any]] = {}
    total_n = 0
    weighted_hits = 0.0
    total_non_syn = 0
    weighted_non_syn_hits = 0.0

    for p in paths:
        if not p.exists():
            continue
        doc = _load(p)
        summ = doc.get("summary") or {}
        n = int(summ.get("n_evaluated") or 0)
        hr = summ.get("hit_rate")
        hr_f = float(hr) if hr is not None else 0.0
        ns_n = int(summ.get("non_synthetic_n_evaluated") or 0)
        ns_hr = summ.get("non_synthetic_hit_rate")
        ns_hr_f = float(ns_hr) if ns_hr is not None and ns_n > 0 else None

        raw = p.stem.removeprefix("logos_symbolic_event_backtest_")
        tag = raw.removesuffix("_latest") if raw.endswith("_latest") else raw
        rows.append(
            {
                "tag": tag,
                "path": str(p).replace("\\", "/"),
                "n_evaluated": n,
                "hit_rate": hr_f,
                "non_synthetic_n": ns_n,
                "non_synthetic_hit_rate": ns_hr_f,
            }
        )
        for r in doc.get("rows") or []:
            obs_id = str(r.get("observation_id") or "")
            label_date = str(r.get("label_date") or "")
            key = f"{obs_id}|{label_date}"
            if not obs_id or not label_date:
                continue
            if key not in unique_rows_by_key:
                unique_rows_by_key[key] = r
            if not bool(r.get("is_synthetic_source", False)) and key not in unique_non_syn_by_key:
                unique_non_syn_by_key[key] = r
        total_n += n
        weighted_hits += hr_f * n
        if ns_n > 0 and ns_hr_f is not None:
            total_non_syn += ns_n
            weighted_non_syn_hits += ns_hr_f * ns_n

    overall_hit = round(weighted_hits / total_n, 6) if total_n else None
    overall_non_syn = round(weighted_non_syn_hits / total_non_syn, 6) if total_non_syn else None
    unique_n = len(unique_rows_by_key)
    unique_hits = sum(int(bool(r.get("hit"))) for r in unique_rows_by_key.values())
    unique_hit_rate = round(unique_hits / unique_n, 6) if unique_n else None
    unique_non_syn_n = len(unique_non_syn_by_key)
    unique_non_syn_hits = sum(int(bool(r.get("hit"))) for r in unique_non_syn_by_key.values())
    unique_non_syn_hit_rate = round(unique_non_syn_hits / unique_non_syn_n, 6) if unique_non_syn_n else None

    out = {
        "schema": "logos_symbolic_event_backtest_bundle_summary_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "notes": [
            "Weighted hit_rate weights each run by n_evaluated.",
            "Prefer non_synthetic_hit_rate per run when available; bundle_non_synthetic_hit_rate weights non_synthetic rows only.",
            "Runs that share the same labels_jsonl (e.g. latest vs blind_split) are correlated; do not treat aggregate as independent draws.",
        ],
        "runs": rows,
        "aggregate": {
            "run_count": len(rows),
            "total_n_evaluated": total_n,
            "weighted_hit_rate": overall_hit,
            "total_non_synthetic_n": total_non_syn,
            "weighted_non_synthetic_hit_rate": overall_non_syn,
            "unique_by_observation_label": {
                "n_evaluated": unique_n,
                "hit_rate": unique_hit_rate,
                "non_synthetic_n": unique_non_syn_n,
                "non_synthetic_hit_rate": unique_non_syn_hit_rate,
            },
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output_json), "aggregate": out["aggregate"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
