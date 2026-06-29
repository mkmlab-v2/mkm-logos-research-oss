#!/usr/bin/env python3
"""P1 music dual-plane micro-bench — harmonic draft vs symbolic grid (B-track · local only).

Neural plane: draft root pitch-class (may violate diatonic set).
Trajectory buffer: cap step size on pitch-class circle (neural plane only).
Hard project: snap to nearest allowed root (symbolic plane).

Reports raw vs post-project illegal rates separately — collapsed_combined_score stays null.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_FIXTURE = ROOT / "tests/fixtures/dual_plane_music_p1_harmonic_crosswalk_v1.json"
DEFAULT_OUT = ROOT / "reports/dual_plane_music_p1_micro_bench_v1_latest.json"
SCHEMA = "dual_plane_music_p1_micro_bench_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _shortest_pc_delta(from_pc: int, to_pc: int) -> int:
    d = (int(to_pc) - int(from_pc)) % 12
    return d - 12 if d > 6 else d


def apply_trajectory_buffer(
    last_pc: int,
    draft_pc: int,
    *,
    max_delta_pc: int,
) -> tuple[int, bool]:
    delta = _shortest_pc_delta(last_pc, draft_pc)
    if abs(delta) <= max_delta_pc:
        return draft_pc % 12, False
    clamped = max_delta_pc if delta > 0 else -max_delta_pc
    return (last_pc + clamped) % 12, True


def hard_project_to_allowed(draft_pc: int, allowed: set[int]) -> int:
    if not allowed:
        raise ValueError("allowed_root_pcs empty")
    pc = int(draft_pc) % 12
    if pc in allowed:
        return pc
    best = min(allowed, key=lambda a: min((a - pc) % 12, (pc - a) % 12))
    return best


def is_illegal_root(pc: int, allowed: set[int]) -> bool:
    return int(pc) % 12 not in allowed


def run_bench(
    fixture: dict[str, Any],
    *,
    max_delta_pc: int | None = None,
) -> dict[str, Any]:
    if fixture.get("schema") != "dual_plane_music_p1_harmonic_crosswalk_v1":
        raise ValueError("fixture schema mismatch")

    allowed_list = fixture.get("allowed_root_pcs") or []
    allowed = {int(x) % 12 for x in allowed_list}
    defaults = fixture.get("buffer_defaults") or {}
    max_delta = int(max_delta_pc if max_delta_pc is not None else defaults.get("max_delta_pc", 2))

    samples = fixture.get("samples") or []
    if not isinstance(samples, list) or not samples:
        raise ValueError("fixture samples required")

    rows: list[dict[str, Any]] = []
    raw_illegal = 0
    post_illegal = 0
    buffer_applied = 0

    for s in samples:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("id") or "")
        last_pc = int(s["last_root_pc"]) % 12
        neural_pc = int(s["neural_draft_root_pc"]) % 12

        raw_bad = is_illegal_root(neural_pc, allowed)
        if raw_bad:
            raw_illegal += 1

        buffered_pc, did_buffer = apply_trajectory_buffer(last_pc, neural_pc, max_delta_pc=max_delta)
        if did_buffer:
            buffer_applied += 1

        projected_pc = hard_project_to_allowed(buffered_pc, allowed)
        post_bad = is_illegal_root(projected_pc, allowed)
        if post_bad:
            post_illegal += 1

        rows.append(
            {
                "id": sid,
                "last_root_pc": last_pc,
                "neural_draft_root_pc": neural_pc,
                "buffered_root_pc": buffered_pc,
                "projected_root_pc": projected_pc,
                "raw_illegal": raw_bad,
                "post_project_illegal": post_bad,
                "buffer_applied": did_buffer,
            }
        )

    n = len(rows)
    raw_rate = raw_illegal / n if n else 0.0
    post_rate = post_illegal / n if n else 0.0

    return {
        "schema": SCHEMA,
        "version": "1.1.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "fixture_schema": fixture.get("schema"),
        "key_label": fixture.get("key_label"),
        "row_count": n,
        "buffer_max_delta_pc": max_delta,
        "metrics": {
            "raw_neural_illegal_rate": round(raw_rate, 4),
            "post_project_illegal_rate": round(post_rate, 4),
            "delta_post_minus_raw_illegal_rate": round(post_rate - raw_rate, 4),
            "buffer_applied_count": buffer_applied,
            "collapsed_combined_score": None,
        },
        "rows": rows,
        "lane_note": "Separate from Universal Root OSS hero — FAIL-COMP-004",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--max-delta-pc", type=int, default=None)
    ap.add_argument("--timing-iterations", type=int, default=100, help="Repeat bench for p95 wall ms (CPU path only)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    fixture_path = args.fixture.resolve()
    if not fixture_path.is_file():
        raise SystemExit(f"fixture missing: {fixture_path}")

    fixture = json.loads(fixture_path.read_text(encoding="utf-8-sig"))

    t0 = time.perf_counter()
    report = run_bench(fixture, max_delta_pc=args.max_delta_pc)
    single_ms = (time.perf_counter() - t0) * 1000.0

    timing_samples: list[float] = []
    for _ in range(max(1, args.timing_iterations)):
        t1 = time.perf_counter()
        run_bench(fixture, max_delta_pc=args.max_delta_pc)
        timing_samples.append((time.perf_counter() - t1) * 1000.0)
    timing_samples.sort()
    p95_idx = min(len(timing_samples) - 1, int(len(timing_samples) * 0.95))
    p95_ms = timing_samples[p95_idx]

    report.setdefault("metrics", {})
    report["metrics"]["bench_wall_ms_single"] = round(single_ms, 4)
    report["metrics"]["bench_wall_ms_p95"] = round(p95_ms, 4)
    report["metrics"]["bench_timing_iterations"] = len(timing_samples)
    report["metrics"]["bench_wall_ms_per_row_single"] = round(single_ms / max(report.get("row_count", 1), 1), 6)

    report["fixture"] = _rel(fixture_path)
    report["reproduce"] = (
        f"py scripts/run_dual_plane_music_p1_micro_bench_v1.py --fixture {_rel(fixture_path)}"
    )
    report["ok"] = report["metrics"]["post_project_illegal_rate"] == 0.0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": report["ok"],
                "raw_neural_illegal_rate": report["metrics"]["raw_neural_illegal_rate"],
                "post_project_illegal_rate": report["metrics"]["post_project_illegal_rate"],
                "row_count": report.get("row_count"),
                "bench_wall_ms_p95": report["metrics"].get("bench_wall_ms_p95"),
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
