#!/usr/bin/env python3
"""Build advisory summary for lens_music_gate_chain_v1 quality_guard_m7.

M8 scope: aggregate WARN/OK counts from one or more chain reports.
Non-blocking analytics only; does not alter promotion decisions.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "lens_music_quality_guard_m7_summary_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _collect_inputs(paths: list[Path], glob_pattern: str | None) -> list[Path]:
    out: list[Path] = [p for p in paths if p.is_file()]
    if glob_pattern:
        out.extend([p for p in ROOT.glob(glob_pattern) if p.is_file()])
    # Stable unique by absolute path string.
    uniq: dict[str, Path] = {}
    for p in out:
        uniq[str(p.resolve())] = p
    return list(uniq.values())


def build_summary(chain_paths: list[Path]) -> dict[str, Any]:
    total = 0
    guard_enabled = 0
    guard_status = Counter()
    check_status_by_id: dict[str, Counter] = defaultdict(Counter)

    for path in chain_paths:
        doc = _load_json(path)
        if doc.get("schema") != "lens_music_gate_chain_v1":
            continue
        total += 1
        g = doc.get("quality_guard_m7")
        if not isinstance(g, dict):
            continue
        if bool(g.get("enabled")):
            guard_enabled += 1
        status = str(g.get("status", "UNKNOWN"))
        guard_status[status] += 1
        checks = g.get("checks")
        if isinstance(checks, list):
            for row in checks:
                if not isinstance(row, dict):
                    continue
                cid = str(row.get("id", "unknown"))
                cst = str(row.get("status", "UNKNOWN"))
                check_status_by_id[cid][cst] += 1

    checks_rollup = {
        cid: {"status_counts": dict(counter), "warn_ratio": counter.get("WARN", 0) / max(sum(counter.values()), 1)}
        for cid, counter in sorted(check_status_by_id.items())
    }

    return {
        "schema": "lens_music_quality_guard_m7_summary_v1",
        "generated_at_utc": _utc_now(),
        "input_chain_reports": [str(p.resolve()) for p in chain_paths],
        "input_count": len(chain_paths),
        "parsed_chain_count": total,
        "guard_enabled_count": guard_enabled,
        "guard_status_counts": dict(guard_status),
        "checks_rollup": checks_rollup,
        "note": "Advisory aggregation only; does not gate promotion decisions.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chain-json", action="append", type=Path, default=[], help="Path to lens_music_gate_chain_v1 json.")
    ap.add_argument(
        "--glob",
        type=str,
        default=None,
        help="Optional ROOT-relative glob (example: reports/**/lens_music_gate_chain*.json)",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    chain_paths = _collect_inputs(args.chain_json, args.glob)
    if not chain_paths:
        print(json.dumps({"ok": False, "error": "no_input_chain_reports"}))
        return 2

    summary = build_summary(chain_paths)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out.resolve()), "parsed_chain_count": summary["parsed_chain_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
