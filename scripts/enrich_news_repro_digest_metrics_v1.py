#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    for enc in ("utf-8", "utf-8-sig"):
        try:
            return json.loads(path.read_text(encoding=enc))
        except Exception:
            continue
    raise ValueError(f"Failed to parse JSON: {path}")


def _read_lines(path: Path) -> list[str]:
    for enc in ("utf-8", "utf-8-sig"):
        try:
            return path.read_text(encoding=enc).splitlines()
        except Exception:
            continue
    raise ValueError(f"Failed to read text log: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich news repro digest with failure/latency metrics from raw log.")
    parser.add_argument(
        "--dropzone",
        default="reports/news_repro/latest",
        help="Dropzone directory containing independent_result_digest.json and raw_benchmark.log",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    dropzone = (root / args.dropzone).resolve()
    digest_path = dropzone / "independent_result_digest.json"
    raw_log_path = dropzone / "raw_benchmark.log"

    digest = _read_json(digest_path)
    lines = _read_lines(raw_log_path)

    status_pattern = re.compile(r"status=(\w+)")
    duration_pattern = re.compile(r"duration_sec=(\d+)")

    step_count = 0
    failed_steps = 0
    benchmark_duration_sec = None

    for line in lines:
        if "step=" in line and "status=" in line:
            step_count += 1
            m = status_pattern.search(line)
            if m and m.group(1).lower() != "ok":
                failed_steps += 1
        if "benchmark_end" in line:
            m_dur = duration_pattern.search(line)
            if m_dur:
                benchmark_duration_sec = int(m_dur.group(1))

    failure_rate = (failed_steps / step_count) if step_count > 0 else 0.0

    digest["failed_cases"] = int(failed_steps)
    digest["failure_rate"] = float(failure_rate)
    digest["latency_summary"] = {
        "benchmark_duration_sec": benchmark_duration_sec,
        "steps_observed": step_count,
        "note": "Derived from raw_benchmark.log; p95 unavailable in this log format.",
    }

    digest_path.write_text(json.dumps(digest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(digest_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
