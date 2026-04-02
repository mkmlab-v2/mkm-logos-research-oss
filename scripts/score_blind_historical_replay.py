# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.8, K:0.7, M:0.6}
# Balance: 89
# Purpose: Score blind replay predictions against private answer key.
# Keywords: blind-replay, scoring, hit-rate, exploratory_only, leakage-safe
#!/usr/bin/env python3
"""Score blind historical replay predictions.

Input contracts:
- answer key jsonl rows: sample_id, answer_label
- prediction jsonl rows: sample_id, direction_sign (or predicted_label), optional confidence_0_1

This tool is B-track exploratory-only and must not connect to A-track live triggers.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "reports" / "constitution" / "btrack_pilot" / "blind_replay"
DEFAULT_REPORT = DEFAULT_DIR / "blind_replay_score_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip().lstrip("\ufeff")
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _norm_label(v: Any) -> str:
    s = str(v or "").strip().upper()
    if s in {"DOWN", "BEAR", "DOWN_STRONG", "NEGATIVE"}:
        return "DOWN_STRONG"
    if s in {"UP", "BULL", "UP_STRONG", "POSITIVE"}:
        return "UP_STRONG"
    if s in {"NEUTRAL", "HOLD", "FLAT"}:
        return "NEUTRAL"
    return "UNKNOWN"


def _heuristic_from_public(public_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    preds: list[dict[str, Any]] = []
    for r in public_rows:
        sample_id = str(r.get("sample_id") or "")
        feat = r.get("features") if isinstance(r.get("features"), dict) else {}
        momentum = float(feat.get("momentum_index") or 0.0)
        vol = float(feat.get("volatility_index") or 0.0)
        if momentum <= -0.02:
            sign = "DOWN_STRONG"
        elif momentum >= 0.02:
            sign = "UP_STRONG"
        else:
            sign = "NEUTRAL"
        # low confidence when volatility is high and momentum near 0
        conf = max(0.1, min(0.95, abs(momentum) * 3.0 + max(0.0, 0.15 - vol)))
        preds.append({"sample_id": sample_id, "direction_sign": sign, "confidence_0_1": round(conf, 4)})
    return preds


def main() -> int:
    ap = argparse.ArgumentParser(description="Score blind replay predictions with private answer key.")
    ap.add_argument("--answer-key", type=Path, required=True)
    ap.add_argument("--predictions", type=Path, default=None)
    ap.add_argument("--public-dataset", type=Path, default=None)
    ap.add_argument("--use-heuristic-baseline", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    key_rows = _read_jsonl(args.answer_key)
    if not key_rows:
        raise SystemExit(f"answer key missing/empty: {args.answer_key}")

    if args.use_heuristic_baseline:
        if not args.public_dataset:
            raise SystemExit("--public-dataset is required with --use-heuristic-baseline")
        public_rows = _read_jsonl(args.public_dataset)
        pred_rows = _heuristic_from_public(public_rows)
        prediction_source = "heuristic_baseline_from_public_features"
    else:
        if not args.predictions:
            raise SystemExit("--predictions is required unless --use-heuristic-baseline is enabled")
        pred_rows = _read_jsonl(args.predictions)
        prediction_source = str(args.predictions.resolve())

    key_map = {str(r.get("sample_id")): _norm_label(r.get("answer_label")) for r in key_rows}
    pred_map: dict[str, dict[str, Any]] = {}
    for r in pred_rows:
        sid = str(r.get("sample_id") or "")
        if not sid:
            continue
        sign = _norm_label(r.get("direction_sign") or r.get("predicted_label"))
        conf = r.get("confidence_0_1")
        pred_map[sid] = {"pred": sign, "confidence_0_1": conf}

    matched = 0
    hit = 0
    miss = 0
    unresolved = 0
    per_label_total = {"DOWN_STRONG": 0, "UP_STRONG": 0, "NEUTRAL": 0}
    per_label_hit = {"DOWN_STRONG": 0, "UP_STRONG": 0, "NEUTRAL": 0}
    samples_preview: list[dict[str, Any]] = []

    for sid, truth in key_map.items():
        if truth in per_label_total:
            per_label_total[truth] += 1
        pred_obj = pred_map.get(sid)
        if not pred_obj:
            unresolved += 1
            continue
        pred = pred_obj["pred"]
        matched += 1
        ok = pred == truth
        if ok:
            hit += 1
            if truth in per_label_hit:
                per_label_hit[truth] += 1
        else:
            miss += 1
        if len(samples_preview) < 10:
            samples_preview.append(
                {
                    "sample_id": sid,
                    "truth": truth,
                    "pred": pred,
                    "is_hit": ok,
                    "confidence_0_1": pred_obj.get("confidence_0_1"),
                }
            )

    hit_rate = (hit / matched) if matched else 0.0
    coverage = (matched / len(key_map)) if key_map else 0.0
    balanced_parts = []
    for lbl in ("DOWN_STRONG", "UP_STRONG", "NEUTRAL"):
        t = per_label_total[lbl]
        h = per_label_hit[lbl]
        if t > 0:
            balanced_parts.append(h / t)
    balanced_acc = (sum(balanced_parts) / len(balanced_parts)) if balanced_parts else 0.0

    report = {
        "schema": "blind_historical_replay_score_v1",
        "generated_at_utc": _utc_now(),
        "exploratory_only": True,
        "a_track_binding_forbidden": True,
        "input": {
            "answer_key": str(args.answer_key.resolve()),
            "prediction_source": prediction_source,
            "public_dataset": str(args.public_dataset.resolve()) if args.public_dataset else None,
        },
        "counts": {
            "answer_key_total": len(key_map),
            "predictions_total": len(pred_map),
            "matched": matched,
            "hit": hit,
            "miss": miss,
            "unresolved": unresolved,
        },
        "metrics": {
            "hit_rate": round(hit_rate, 6),
            "coverage_rate": round(coverage, 6),
            "balanced_accuracy": round(balanced_acc, 6),
        },
        "per_label": {
            "total": per_label_total,
            "hit": per_label_hit,
        },
        "samples_preview": samples_preview,
        "note": "Exploratory benchmark only. Do not promote to live trigger path.",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out.resolve()}")
    print(
        f"hit_rate={report['metrics']['hit_rate']} coverage={report['metrics']['coverage_rate']} "
        f"matched={matched}/{len(key_map)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
