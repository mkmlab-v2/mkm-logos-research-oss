#!/usr/bin/env python3
"""Build diff/history artifacts for TruthfulQA Vertex A/B benchmark."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


def _now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if isinstance(obj, dict):
                out.append(obj)
    return out


def _summary(bench: dict[str, Any], gate: dict[str, Any] | None) -> dict[str, Any]:
    b = bench.get("baseline") or {}
    c = bench.get("candidate") or {}
    comp = bench.get("comparative") or {}
    strict = (gate or {}).get("strict") or {}
    strict_summary = strict.get("summary") or {}
    return {
        "generated_at_utc": bench.get("generated_at_utc") or _now_utc_iso(),
        "dataset_jsonl": bench.get("dataset_jsonl"),
        "baseline_model": bench.get("baseline_model"),
        "candidate_model": bench.get("candidate_model"),
        "baseline_accuracy": b.get("accuracy"),
        "candidate_accuracy": c.get("accuracy"),
        "accuracy_delta": comp.get("accuracy_delta"),
        "hallucination_rate_proxy_delta": comp.get("hallucination_rate_proxy_delta"),
        "gate_decision": strict_summary.get("decision"),
        "gate_pass_count": strict_summary.get("pass_count"),
        "gate_total": strict_summary.get("total"),
    }


def _delta(cur: dict[str, Any], prev: dict[str, Any] | None, key: str) -> float | None:
    if not prev:
        return None
    a = cur.get(key)
    b = prev.get(key)
    try:
        if a is None or b is None:
            return None
        return float(a) - float(b)
    except (TypeError, ValueError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Build TruthfulQA Vertex A/B diff artifact")
    ap.add_argument(
        "--bench-json",
        type=Path,
        default=Path("docs/final/artifacts/truthfulqa_vertex_ab_benchmark_latest.json"),
    )
    ap.add_argument(
        "--gate-json",
        type=Path,
        default=Path("docs/final/artifacts/truthfulqa_vertex_ab_gate_latest.json"),
    )
    ap.add_argument(
        "--history-jsonl",
        type=Path,
        default=Path("docs/final/artifacts/truthfulqa_vertex_ab_history_v1.jsonl"),
    )
    ap.add_argument(
        "--out-json",
        type=Path,
        default=Path("docs/final/artifacts/truthfulqa_vertex_ab_diff_latest.json"),
    )
    args = ap.parse_args()

    bench = _read_json(args.bench_json)
    gate = _read_json(args.gate_json) if args.gate_json.is_file() else None
    cur = _summary(bench, gate)
    hist = _read_jsonl(args.history_jsonl)
    prev = hist[-1] if hist else None

    out = {
        "schema": "truthfulqa_vertex_ab_diff_v1",
        "generated_at_utc": _now_utc_iso(),
        "current": cur,
        "previous": prev,
        "delta": {
            "baseline_accuracy": _delta(cur, prev, "baseline_accuracy"),
            "candidate_accuracy": _delta(cur, prev, "candidate_accuracy"),
            "accuracy_delta": _delta(cur, prev, "accuracy_delta"),
            "hallucination_rate_proxy_delta": _delta(cur, prev, "hallucination_rate_proxy_delta"),
        },
        "has_previous_snapshot": prev is not None,
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    args.history_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.history_jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(cur, ensure_ascii=False) + "\n")

    print(f"[OK] wrote: {args.out_json}")
    print(f"[OK] history append: {args.history_jsonl}")
    print(f"[SUMMARY] has_previous={prev is not None}, gate={cur.get('gate_decision')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
