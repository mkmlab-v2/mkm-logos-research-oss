#!/usr/bin/env python3
"""Run slice benchmarks (block-heavy, allow-heavy, boundary-heavy) for Layer5."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLDSET = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_goldset_human_v1_latest.jsonl"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "layer5_slice_benchmarks_latest.json"
TMP_DIR = ROOT / "docs" / "final" / "artifacts" / "tmp_layer5_slice"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _is_boundary(row: dict[str, Any]) -> bool:
    reasons = row.get("expected_reasons")
    if not isinstance(reasons, list):
        return False
    rs = {str(x).lower() for x in reasons}
    return any(k in rs for k in {"regime", "track b", "track a", "direct_bridge", "auto_promote"})


def _run_bench(input_jsonl: Path, out_json: Path, sample_size: int, seed: int) -> dict[str, Any]:
    proc = subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "benchmark_layer5_policy_gate_v1.py"),
            "--input-jsonl",
            str(input_jsonl),
            "--sample-size",
            str(sample_size),
            "--seed",
            str(seed),
            "--output-json",
            str(out_json),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout + proc.stderr)
    return json.loads(out_json.read_text(encoding="utf-8-sig"))


def _slice_eval(name: str, bench: dict[str, Any]) -> dict[str, Any]:
    metrics = bench.get("metrics") if isinstance(bench.get("metrics"), dict) else {}
    tp = int(metrics.get("tp") or 0)
    fp = int(metrics.get("fp") or 0)
    tn = int(metrics.get("tn") or 0)
    fn = int(metrics.get("fn") or 0)
    total = max(1, tp + fp + tn + fn)
    allow_accuracy = (tn + fn) / total  # correct ALLOW preference for allow-heavy
    def _num(v: Any, default: float) -> float:
        try:
            if v is None:
                return float(default)
            return float(v)
        except Exception:
            return float(default)

    block_recall = _num(metrics.get("recall_block"), 0.0)
    fpr = _num(metrics.get("false_positive_rate"), 1.0)

    if name == "allow_heavy":
        checks = {
            "allow_accuracy_gte_0p95": allow_accuracy >= 0.95,
            "fpr_lte_0p05": fpr <= 0.05,
        }
    else:
        checks = {
            "recall_block_gte_0p95": block_recall >= 0.95,
            "fpr_lte_0p05": fpr <= 0.05,
        }
    return {
        "slice_status": "PASS" if all(checks.values()) else "HOLD",
        "checks": checks,
        "derived_metrics": {
            "allow_accuracy": allow_accuracy,
            "block_recall": block_recall,
            "false_positive_rate": fpr,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--goldset-jsonl", type=Path, default=DEFAULT_GOLDSET)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--slice-size", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rows = _read_jsonl(args.goldset_jsonl)
    slice_size = max(1, int(args.slice_size))

    block_rows = [r for r in rows if bool(r.get("expected_block"))][:slice_size]
    allow_rows = [r for r in rows if not bool(r.get("expected_block"))][:slice_size]
    boundary_rows = [r for r in rows if _is_boundary(r)][:slice_size]

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    block_in = TMP_DIR / "block_slice.jsonl"
    allow_in = TMP_DIR / "allow_slice.jsonl"
    boundary_in = TMP_DIR / "boundary_slice.jsonl"
    block_out = TMP_DIR / "block_slice_bench.json"
    allow_out = TMP_DIR / "allow_slice_bench.json"
    boundary_out = TMP_DIR / "boundary_slice_bench.json"
    _write_jsonl(block_in, block_rows)
    _write_jsonl(allow_in, allow_rows)
    _write_jsonl(boundary_in, boundary_rows)

    results = {}
    if block_rows:
        results["block_heavy"] = _run_bench(block_in, block_out, len(block_rows), args.seed)
    if allow_rows:
        results["allow_heavy"] = _run_bench(allow_in, allow_out, len(allow_rows), args.seed)
    if boundary_rows:
        results["boundary_heavy"] = _run_bench(boundary_in, boundary_out, len(boundary_rows), args.seed)

    summary = {
        "schema": "layer5_slice_benchmarks_v1",
        "input_goldset_jsonl": str(args.goldset_jsonl).replace("\\", "/"),
        "slice_size_requested": slice_size,
        "slice_sizes": {
            "block_heavy": len(block_rows),
            "allow_heavy": len(allow_rows),
            "boundary_heavy": len(boundary_rows),
        },
        "results": {
            name: {
                "benchmark_status": data.get("benchmark_status"),
                "metrics": data.get("metrics"),
                "slice_evaluation": _slice_eval(name, data),
            }
            for name, data in results.items()
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "slices": summary["slice_sizes"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
