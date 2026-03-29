# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.2, L:0.6, K:0.45, M:0.35}
# Balance: 80
# Purpose: Sweep --top-k for BTC-ext regime-primary Logos probe; emit intersection JSON per k.
# Keywords: logos, regime, btc-ext, sweep, intersection
"""Sweep top-k for four BTC-ext regimes; optional early stop; checkpoint + resume per k."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_probe(
    *,
    probe_py: Path,
    regime_map: Path,
    regime_id: str,
    top_k: int,
    output: Path,
    limit: int | None,
) -> None:
    cmd: List[str] = [
        "py",
        "-u",
        str(probe_py),
        "--ancient-resonance",
        "--rank-by-regime",
        "--regime-map",
        str(regime_map),
        "--regime",
        regime_id,
        "--top-k",
        str(top_k),
        "--output",
        str(output),
    ]
    if limit is not None:
        cmd.extend(["--limit", str(limit)])
    subprocess.run(cmd, cwd=str(_root()), check=True)


def _run_compute(
    *,
    compute_py: Path,
    paths: Dict[str, Path],
    output: Path,
    no_distinctive: bool,
) -> Dict[str, Any]:
    cmd: List[str] = [
        "py",
        "-u",
        str(compute_py),
        "--bull-pump",
        str(paths["bull_pump"]),
        "--sideways",
        str(paths["sideways_accumulation"]),
        "--bear",
        str(paths["bear_trend"]),
        "--capitulation",
        str(paths["capitulation"]),
        "--output",
        str(output),
    ]
    if no_distinctive:
        cmd.append("--no-distinctive")
    subprocess.run(cmd, cwd=str(_root()), check=True)
    return json.loads(output.read_text(encoding="utf-8"))


def _checkpoint_path(out_dir: Path, prefix: str) -> Path:
    return out_dir / f"{prefix}_SWEEP_CHECKPOINT.json"


def _load_checkpoint(path: Path) -> Tuple[Set[int], List[Dict[str, Any]]]:
    if not path.is_file():
        return set(), []
    data = json.loads(path.read_text(encoding="utf-8"))
    done = {int(x) for x in data.get("completed_ks", [])}
    rows = data.get("sweep_rows", [])
    if not isinstance(rows, list):
        rows = []
    return done, rows


def _save_checkpoint(
    path: Path,
    *,
    completed_ks: Set[int],
    sweep_rows: List[Dict[str, Any]],
    meta: Dict[str, Any],
) -> None:
    payload = {
        "completed_ks": sorted(completed_ks),
        "sweep_rows": sweep_rows,
        "meta": meta,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _write_summary(path: Path, sweep_rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(sweep_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def main() -> int:
    root = _root()
    probe = root / "scripts" / "logos_vector_resonance_probe.py"
    compute = root / "scripts" / "compute_logos_regime_intersections.py"

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--ks",
        type=int,
        nargs="+",
        default=[500, 1000, 2000, 5000, 10000],
        help="top-k values to try in order",
    )
    p.add_argument(
        "--regime-map",
        type=Path,
        default=root / "data" / "regimes" / "regime_map_btc_ext.json",
    )
    p.add_argument(
        "--prefix",
        type=str,
        default="LOGOS_RESONANCE_BTC_EXT",
        help="Filename prefix for per-regime probe JSON",
    )
    p.add_argument(
        "--stop-on-all-four",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="If true, stop after first k where summary.all_four_non_empty (default: false = full ks list)",
    )
    p.add_argument(
        "--fresh",
        action="store_true",
        help="Delete checkpoint before run (start from scratch)",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Forward --limit to probe (dev only; full corpus if unset)",
    )
    p.add_argument(
        "--no-distinctive",
        action="store_true",
        help="Pass --no-distinctive to intersection script",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for probe JSON, intersection JSON, sweep summary (default: backtest_results under repo root)",
    )
    args = p.parse_args()

    out_dir = (root / args.output_dir) if args.output_dir is not None else root / "backtest_results"

    regime_ids = (
        "bull_pump",
        "sideways_accumulation",
        "bear_trend",
        "capitulation",
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    ck_path = _checkpoint_path(out_dir, args.prefix)
    if args.fresh and ck_path.is_file():
        ck_path.unlink()

    completed: Set[int] = set()
    sweep_rows: List[Dict[str, Any]] = []
    if ck_path.is_file():
        completed, sweep_rows = _load_checkpoint(ck_path)
        if completed:
            print(
                json.dumps(
                    {"resume": True, "checkpoint": str(ck_path), "completed_ks": sorted(completed)},
                    ensure_ascii=False,
                    indent=2,
                ),
                flush=True,
            )

    meta = {
        "ks": list(args.ks),
        "regime_map": str(args.regime_map),
        "prefix": args.prefix,
        "limit": args.limit,
    }
    for k in args.ks:
        if k in completed:
            print(
                json.dumps({"skip_k": k, "reason": "already_checkpointed"}, ensure_ascii=False, indent=2),
                flush=True,
            )
            continue
        paths: Dict[str, Path] = {}
        for rid in regime_ids:
            outp = out_dir / f"{args.prefix}_{rid}_TOP{k}.json"
            paths[rid] = outp
            _run_probe(
                probe_py=probe,
                regime_map=args.regime_map,
                regime_id=rid,
                top_k=k,
                output=outp,
                limit=args.limit,
            )
        inter_path = out_dir / f"{args.prefix}_INTERSECTION_TOP{k}.json"
        doc = _run_compute(
            compute_py=compute,
            paths=paths,
            output=inter_path,
            no_distinctive=args.no_distinctive,
        )
        row = {
            "k": k,
            "intersection_report": str(inter_path),
            "summary": doc.get("summary"),
            "count_all_four": doc.get("count_all_four"),
        }
        sweep_rows.append(row)
        completed.add(k)
        _save_checkpoint(ck_path, completed_ks=completed, sweep_rows=sweep_rows, meta=meta)
        summary_path = out_dir / f"{args.prefix}_SWEEP_SUMMARY.json"
        _write_summary(summary_path, sweep_rows)
        print(json.dumps(row, ensure_ascii=False, indent=2), flush=True)
        if args.stop_on_all_four and doc.get("summary", {}).get("all_four_non_empty"):
            print(f"sweep: stop at k={k} (all_four non-empty)", flush=True)
            break

    summary_path = out_dir / f"{args.prefix}_SWEEP_SUMMARY.json"
    _write_summary(summary_path, sweep_rows)
    if set(args.ks) <= completed and ck_path.is_file():
        ck_path.unlink()
        print(json.dumps({"checkpoint": "cleared", "reason": "all_k_completed"}, ensure_ascii=False), flush=True)
    print(f"wrote {summary_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
