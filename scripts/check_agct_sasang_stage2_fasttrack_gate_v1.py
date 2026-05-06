#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        t = line.strip()
        if not t:
            continue
        try:
            obj = json.loads(t)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Fast-track gate for AGCT stage2 final candidate.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument(
        "--thresholds-json",
        type=Path,
        default=root / "docs" / "final" / "artifacts" / "agct_sasang_stage2_promotion_thresholds_v1.json",
    )
    ap.add_argument(
        "--history-jsonl",
        type=Path,
        default=root / "reports" / "agct_sasang_stage2_compare_history_v1.jsonl",
    )
    ap.add_argument(
        "--latest-compare-json",
        type=Path,
        default=root / "reports" / "agct_sasang_stage2_candidate_compare_v1_latest.json",
    )
    ap.add_argument(
        "--out-json",
        type=Path,
        default=root / "reports" / "agct_sasang_stage2_fasttrack_gate_v1_latest.json",
    )
    ns = ap.parse_args()

    th = _read_json(ns.thresholds_json).get("thresholds", {})
    min_samples = int(th.get("fasttrack_min_samples", 7))
    min_go_ratio = float(th.get("fasttrack_min_go_ratio", 0.7))
    max_hold_ratio = float(th.get("fasttrack_max_hold_ratio", 0.0))
    require_latest_not_hold = bool(th.get("fasttrack_require_latest_not_hold", True))

    rows = _read_jsonl(ns.history_jsonl)
    latest_compare = _read_json(ns.latest_compare_json)
    window = rows[-min_samples:] if len(rows) >= min_samples else rows

    n = len(window)
    go_count = sum(1 for r in window if str(r.get("decision_label")) == "GO_STAGE2_CANDIDATE")
    hold_count = sum(1 for r in window if str(r.get("decision_label")) == "HOLD_STAGE2")
    go_ratio = (go_count / n) if n > 0 else 0.0
    hold_ratio = (hold_count / n) if n > 0 else 1.0
    latest_label = str(latest_compare.get("decision", {}).get("label") or "unknown")

    checks = {
        "sample_count_ok": n >= min_samples,
        "go_ratio_ok": go_ratio >= min_go_ratio,
        "hold_ratio_ok": hold_ratio <= max_hold_ratio,
        "latest_not_hold_ok": (latest_label != "HOLD_STAGE2") if require_latest_not_hold else True,
    }
    all_ok = all(checks.values())
    decision = "GO_STAGE2_FINAL_CANDIDATE_FASTTRACK" if all_ok else "HOLD_STAGE2_FASTTRACK"

    payload = {
        "schema": "agct_sasang_stage2_fasttrack_gate_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "decision": decision,
        "inputs": {
            "thresholds_json": str(ns.thresholds_json.resolve()),
            "history_jsonl": str(ns.history_jsonl.resolve()),
            "latest_compare_json": str(ns.latest_compare_json.resolve()),
        },
        "window_metrics": {
            "sample_count": n,
            "go_candidate_count": go_count,
            "hold_count": hold_count,
            "go_candidate_ratio": round(go_ratio, 6),
            "hold_ratio": round(hold_ratio, 6),
            "latest_label": latest_label,
        },
        "checks": checks,
    }
    ns.out_json.parent.mkdir(parents=True, exist_ok=True)
    ns.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.out_json.resolve()} decision={decision}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
