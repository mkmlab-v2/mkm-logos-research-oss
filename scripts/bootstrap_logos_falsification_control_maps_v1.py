#!/usr/bin/env python3
"""Emit missing Logos falsification control symbol maps (B-track, research only)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PRIMARY = ROOT / "docs/final/artifacts/logos_symbolic_event_map_v1.json"
OUT_COUNTER = ROOT / "docs/final/artifacts/logos_symbolic_event_map_counterfactual_v1.json"
OUT_DUMMY = ROOT / "docs/final/artifacts/logos_symbolic_event_map_dummy_v1.json"
OUT_ICHING = ROOT / "docs/final/artifacts/logos_symbolic_event_map_iching_v1.json"
HOLDOUT_NEWS = ROOT / "tests/fixtures/logos_symbolic_event_backtest_news_holdout_v1.jsonl"
HOLDOUT_LABELS = ROOT / "tests/fixtures/logos_symbolic_event_backtest_labels_holdout_v1.jsonl"
SMOKE_NEWS = ROOT / "tests/fixtures/logos_symbolic_event_backtest_news_smoke_v1.jsonl"
SMOKE_LABELS = ROOT / "tests/fixtures/logos_symbolic_event_backtest_labels_smoke_v1.jsonl"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _flip_bias(bias: str) -> str:
    if bias == "up":
        return "down"
    if bias == "down":
        return "up"
    return bias


def _build_counterfactual(primary: dict[str, Any]) -> dict[str, Any]:
    doc = json.loads(json.dumps(primary))
    doc["version"] = "1.0.0-counterfactual"
    symbols = doc.get("symbols")
    if isinstance(symbols, list):
        for sym in symbols:
            if isinstance(sym, dict) and sym.get("symbol_id") in {
                "joseph_famine_storage",
                "jubilee_relief",
            }:
                sym["direction_bias"] = _flip_bias(str(sym.get("direction_bias") or "neutral"))
    notes = doc.get("notes")
    if not isinstance(notes, list):
        notes = []
    notes.append("[B-TRACK] Counterfactual arm: flipped Joseph/Jubilee biases for falsification only.")
    doc["notes"] = notes
    return doc


def _build_dummy() -> dict[str, Any]:
    return {
        "schema": "logos_symbolic_event_map_v1",
        "version": "1.0.0-dummy-control",
        "symbolic_inference": {"conflict_dampen": 0.0},
        "symbols": [
            {
                "symbol_id": "dummy_never_match",
                "corpus_lane": "canon",
                "direction_bias": "up",
                "weight": 0.01,
                "keywords": ["__dummy_never_match_xyz__"],
            }
        ],
        "notes": ["[B-TRACK] Negative control — keywords should not match real news fixtures."],
    }


def _build_iching() -> dict[str, Any]:
    return {
        "schema": "logos_symbolic_event_map_v1",
        "version": "1.0.0-iching-adapter",
        "symbolic_inference": {"conflict_dampen": 0.5},
        "symbols": [
            {
                "symbol_id": "hexagram_change",
                "corpus_lane": "canon",
                "direction_bias": "neutral",
                "weight": 0.15,
                "keywords": ["inventory build", "prices dip", "orders improve"],
            },
            {
                "symbol_id": "hexagram_stillness",
                "corpus_lane": "canon",
                "direction_bias": "neutral",
                "weight": 0.12,
                "keywords": ["slower tightening", "housing starts cool"],
            },
        ],
        "notes": ["[B-TRACK] I-Ching adapter stub — low-weight neutral band for contrastive bench."],
    }


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _bootstrap_holdout() -> None:
    if HOLDOUT_NEWS.is_file() and HOLDOUT_LABELS.is_file():
        return
    HOLDOUT_NEWS.parent.mkdir(parents=True, exist_ok=True)
    news_rows: list[str] = []
    label_rows: list[str] = []
    if SMOKE_NEWS.is_file():
        for i, line in enumerate(SMOKE_NEWS.read_text(encoding="utf-8").splitlines()):
            raw = line.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            obj["observation_id"] = f"holdout-{i:04d}"
            obj["dataset_partition"] = "locked_eval_holdout"
            news_rows.append(json.dumps(obj, ensure_ascii=False))
    if SMOKE_LABELS.is_file():
        for i, line in enumerate(SMOKE_LABELS.read_text(encoding="utf-8").splitlines()):
            raw = line.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            obj["label_sha256"] = f"holdout_label_{i:04d}"
            label_rows.append(json.dumps(obj, ensure_ascii=False))
    # Expand holdout to 8 label rows if smoke labels shorter
    while len(label_rows) < 8 and label_rows:
        label_rows.append(label_rows[-1])
    while len(news_rows) < 8 and news_rows:
        news_rows.append(news_rows[-1])
    HOLDOUT_NEWS.write_text("\n".join(news_rows[:8]) + "\n", encoding="utf-8")
    HOLDOUT_LABELS.write_text("\n".join(label_rows[:8]) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not PRIMARY.is_file():
        print(f"missing primary map: {PRIMARY}")
        return 2
    primary = _load(PRIMARY)
    outputs = [
        (OUT_COUNTER, _build_counterfactual(primary)),
        (OUT_DUMMY, _build_dummy()),
        (OUT_ICHING, _build_iching()),
    ]
    if args.dry_run:
        for path, _ in outputs:
            print(path)
        print(HOLDOUT_NEWS)
        print(HOLDOUT_LABELS)
        return 0
    for path, doc in outputs:
        _write_json(path, doc)
        print(f"WROTE: {path}")
    _bootstrap_holdout()
    print(f"WROTE: {HOLDOUT_NEWS}")
    print(f"WROTE: {HOLDOUT_LABELS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
