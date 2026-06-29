#!/usr/bin/env python3
"""P2 spatial dual-plane micro-bench — scene grid draft vs symbolic navigability (B-track).

Neural plane: draft grid cell (may hit wall / OOB).
Trajectory buffer: cap Chebyshev step on grid (neural only).
Hard project: snap to nearest legal navigable cell.

Reports raw vs post-project violation rates — collapsed_combined_score stays null.
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

DEFAULT_FIXTURE = ROOT / "tests/fixtures/dual_plane_spatial_p2_scene_crosswalk_v1.json"
DEFAULT_OUT = ROOT / "reports/dual_plane_spatial_p2_micro_bench_v1_latest.json"
SCHEMA = "dual_plane_spatial_p2_micro_bench_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def cell_to_xy(cell: int, grid_size: int) -> tuple[int, int]:
    c = int(cell)
    return c // grid_size, c % grid_size


def xy_to_cell(x: int, y: int, grid_size: int) -> int:
    return int(x) * grid_size + int(y)


def build_allowed(grid_size: int, wall_cells: set[int]) -> set[int]:
    total = grid_size * grid_size
    return {i for i in range(total) if i not in wall_cells}


def is_violation(cell: int, allowed: set[int], grid_size: int) -> bool:
    c = int(cell)
    if c < 0 or c >= grid_size * grid_size:
        return True
    return c not in allowed


def chebyshev(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def apply_trajectory_buffer(
    last_cell: int,
    draft_cell: int,
    *,
    grid_size: int,
    max_delta: int,
) -> tuple[int, bool]:
    lx, ly = cell_to_xy(last_cell, grid_size)
    dx, dy = cell_to_xy(draft_cell, grid_size)
    dist = chebyshev((lx, ly), (dx, dy))
    if dist <= max_delta:
        return int(draft_cell), False
    # step toward draft by max_delta on each axis proportionally (Chebyshev clamp)
    sx = max(-max_delta, min(max_delta, dx - lx))
    sy = max(-max_delta, min(max_delta, dy - ly))
    # if still too far diagonally, scale down
    if max(abs(sx), abs(sy)) > max_delta:
        sx = max(-max_delta, min(max_delta, sx))
        sy = max(-max_delta, min(max_delta, sy))
    nx, ny = lx + sx, ly + sy
    return xy_to_cell(nx, ny, grid_size), True


def hard_project_to_allowed(draft_cell: int, allowed: set[int], grid_size: int) -> int:
    c = int(draft_cell)
    if not is_violation(c, allowed, grid_size):
        return c
    dx, dy = cell_to_xy(c, grid_size)
    best = min(
        allowed,
        key=lambda a: (
            chebyshev((dx, dy), cell_to_xy(a, grid_size)),
            a,
        ),
    )
    return best


def run_bench(
    fixture: dict[str, Any],
    *,
    max_delta: int | None = None,
) -> dict[str, Any]:
    if fixture.get("schema") != "dual_plane_spatial_p2_scene_crosswalk_v1":
        raise ValueError("fixture schema mismatch")

    grid_size = int(fixture.get("grid_size") or 8)
    walls = {int(x) for x in fixture.get("wall_cells") or []}
    allowed = build_allowed(grid_size, walls)
    defaults = fixture.get("buffer_defaults") or {}
    max_d = int(max_delta if max_delta is not None else defaults.get("max_delta_chebyshev", 2))

    samples = fixture.get("samples") or []
    rows: list[dict[str, Any]] = []
    raw_viol = 0
    post_viol = 0
    buffer_applied = 0

    for s in samples:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("id") or "")
        last = int(s["last_cell"])
        neural = int(s["neural_draft_cell"])

        raw_bad = is_violation(neural, allowed, grid_size)
        if raw_bad:
            raw_viol += 1

        buffered, did_buffer = apply_trajectory_buffer(
            last, neural, grid_size=grid_size, max_delta=max_d
        )
        if did_buffer:
            buffer_applied += 1

        projected = hard_project_to_allowed(buffered, allowed, grid_size)
        post_bad = is_violation(projected, allowed, grid_size)
        if post_bad:
            post_viol += 1

        rows.append(
            {
                "id": sid,
                "last_cell": last,
                "neural_draft_cell": neural,
                "buffered_cell": buffered,
                "projected_cell": projected,
                "raw_violation": raw_bad,
                "post_project_violation": post_bad,
                "buffer_applied": did_buffer,
            }
        )

    n = len(rows)
    raw_rate = raw_viol / n if n else 0.0
    post_rate = post_viol / n if n else 0.0

    return {
        "schema": SCHEMA,
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "fixture_schema": fixture.get("schema"),
        "scene_label": fixture.get("scene_label"),
        "row_count": n,
        "buffer_max_delta_chebyshev": max_d,
        "metrics": {
            "raw_neural_violation_rate": round(raw_rate, 4),
            "post_project_violation_rate": round(post_rate, 4),
            "delta_post_minus_raw_violation_rate": round(post_rate - raw_rate, 4),
            "buffer_applied_count": buffer_applied,
            "collapsed_combined_score": None,
        },
        "rows": rows,
        "lane_note": "Separate from Universal Root OSS hero — FAIL-COMP-004",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--max-delta", type=int, default=None)
    ap.add_argument("--timing-iterations", type=int, default=100)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    fixture_path = args.fixture.resolve()
    fixture = json.loads(fixture_path.read_text(encoding="utf-8-sig"))

    t0 = time.perf_counter()
    report = run_bench(fixture, max_delta=args.max_delta)
    single_ms = (time.perf_counter() - t0) * 1000.0

    times: list[float] = []
    for _ in range(max(1, args.timing_iterations)):
        t1 = time.perf_counter()
        run_bench(fixture, max_delta=args.max_delta)
        times.append((time.perf_counter() - t1) * 1000.0)
    times.sort()
    p95 = times[min(len(times) - 1, int(len(times) * 0.95))]

    report["metrics"]["bench_wall_ms_single"] = round(single_ms, 4)
    report["metrics"]["bench_wall_ms_p95"] = round(p95, 4)
    report["fixture"] = _rel(fixture_path)
    report["reproduce"] = f"py scripts/run_dual_plane_spatial_p2_micro_bench_v1.py --fixture {_rel(fixture_path)}"
    report["ok"] = report["metrics"]["post_project_violation_rate"] == 0.0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": report["ok"],
                "raw_neural_violation_rate": report["metrics"]["raw_neural_violation_rate"],
                "post_project_violation_rate": report["metrics"]["post_project_violation_rate"],
                "row_count": report["row_count"],
                "bench_wall_ms_p95": report["metrics"]["bench_wall_ms_p95"],
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
