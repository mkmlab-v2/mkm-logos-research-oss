# -*- coding: utf-8 -*-
"""Generate deterministic synthetic LOG_METABOLISM JSONL (B-track, no PII).

Rows satisfy ``ingest_notebooklm_metabolism_jsonl`` minimal contract:
``window_start_utc``, ``egress_pressure``, ``throttle_events``.
Optional ``trace_scope`` for downstream diversity.

Rows are spaced by ``--step-hours`` (default 1) so 만세력 시주가 코호트 전반에 걸쳐 변동한다.

Use ``--run-pipeline`` to: write cohort → convert to myeongri correlation input →
``spike_log_myeongri_correlation_v1.py`` (default min windows 30).
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]


def _rows(*, n: int, seed: int, base_utc: str, step_hours: int) -> List[Dict[str, Any]]:
    if n < 1:
        raise ValueError("n must be >= 1")
    if step_hours < 1:
        raise ValueError("step_hours must be >= 1")
    t0 = datetime.fromisoformat(base_utc.replace("Z", "+00:00"))
    if t0.tzinfo is None:
        t0 = t0.replace(tzinfo=timezone.utc)
    rows: List[Dict[str, Any]] = []
    for i in range(n):
        # Hour steps so ``MyeongriCompleteFusion`` pillars (esp. 시주) drift across cohort.
        dt = t0 + timedelta(hours=i * step_hours)
        w = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        # LCG for reproducible jitter (Park–Miller minimal std)
        s = (seed * 9301 + 49297 + i * 17) % 233280
        u = s / 233280.0
        phase = (i + seed) / 25.0
        egress = 80.0 + 60.0 * (0.5 + 0.5 * math.sin(phase)) + 25.0 * u
        throttle = max(0.0, min(egress, 8.0 + 12.0 * abs(math.cos(phase * 1.1)) + 15.0 * u))
        rows.append(
            {
                "window_start_utc": w,
                "trace_scope": f"synthetic-{(i + seed) % 8}",
                "egress_pressure": round(float(egress), 4),
                "throttle_events": round(float(throttle), 4),
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rows", type=int, default=120, help="Number of cohort rows (>=30 for default spike)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--base-utc",
        default="2026-04-01T00:00:00Z",
        help="First window_start_utc (UTC)",
    )
    ap.add_argument(
        "--step-hours",
        type=int,
        default=1,
        help="Hours between consecutive rows (default 1 for pillar diversity)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "docs/final/artifacts/derived/log_metabolism_synthetic_cohort_v1.jsonl",
    )
    ap.add_argument(
        "--correlation-input-out",
        type=Path,
        default=ROOT / "docs/final/artifacts/derived/log_metabolism_synthetic_as_myeongri_correlation_input_v1.jsonl",
    )
    ap.add_argument(
        "--correlation-json-out",
        type=Path,
        default=ROOT / "docs/final/artifacts/log_myeongri_correlation_synthetic_latest.json",
    )
    ap.add_argument("--run-id", default="synthetic_cohort_v1_auto")
    ap.add_argument("--min-valid-windows", type=int, default=30)
    ap.add_argument(
        "--run-pipeline",
        action="store_true",
        help="After write: convert_log_metabolism_to_myeongri_correlation_input_v1 + spike_log_myeongri_correlation_v1",
    )
    args = ap.parse_args()

    rows = _rows(
        n=int(args.rows),
        seed=int(args.seed),
        base_utc=str(args.base_utc),
        step_hours=int(args.step_hours),
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n"
    out.write_text(body, encoding="utf-8")
    print(f"OK: wrote {out} rows={len(rows)}", file=sys.stderr)

    if not args.run_pipeline:
        return 0

    conv = ROOT / "scripts" / "convert_log_metabolism_to_myeongri_correlation_input_v1.py"
    corr_in = Path(args.correlation_input_out)
    spike = ROOT / "scripts" / "spike_log_myeongri_correlation_v1.py"
    corr_json = Path(args.correlation_json_out)

    r1 = subprocess.run(
        [
            sys.executable,
            str(conv),
            "--in",
            str(out),
            "--out",
            str(corr_in),
            "--run-id",
            str(args.run_id),
        ],
        cwd=str(ROOT),
    )
    if r1.returncode != 0:
        return r1.returncode

    r2 = subprocess.run(
        [
            sys.executable,
            str(spike),
            "--input",
            str(corr_in),
            "--min-valid-windows",
            str(int(args.min_valid_windows)),
            "--output",
            str(corr_json),
        ],
        cwd=str(ROOT),
    )
    if r2.returncode != 0:
        return r2.returncode
    print(f"OK: pipeline wrote {corr_json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
