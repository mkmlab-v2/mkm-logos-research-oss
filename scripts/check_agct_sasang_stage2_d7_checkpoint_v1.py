#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _fmt_utc(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_ts(v: Any) -> datetime | None:
    if not isinstance(v, str) or not v.strip():
        return None
    s = v.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


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
    ap = argparse.ArgumentParser(description="D+7 checkpoint for AGCT stage2 final promotion readiness.")
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
        "--promotion-gate-json",
        type=Path,
        default=root / "reports" / "agct_sasang_stage2_promotion_gate_v1_latest.json",
    )
    ap.add_argument(
        "--out-json",
        type=Path,
        default=root / "reports" / "agct_sasang_stage2_d7_checkpoint_v1_latest.json",
    )
    ns = ap.parse_args()

    th = _read_json(ns.thresholds_json).get("thresholds", {})
    min_days = float(th.get("d7_min_elapsed_days", 7.0))
    required_decision = str(th.get("d7_required_decision", "GO_STAGE2_FINAL"))

    rows = _read_jsonl(ns.history_jsonl)
    gate = _read_json(ns.promotion_gate_json)
    now = _utc_now()

    first_ts = None
    if rows:
        for k in ("appended_at_utc", "source_generated_at_utc"):
            first_ts = _parse_ts(rows[0].get(k))
            if first_ts is not None:
                break

    elapsed_days = None
    elapsed_ok = False
    if first_ts is not None:
        elapsed_days = (now - first_ts).total_seconds() / 86400.0
        elapsed_ok = elapsed_days >= min_days

    gate_decision = str(gate.get("decision") or "unknown")
    decision_ok = gate_decision == required_decision

    checkpoint_status = "TRACKING"
    if elapsed_ok:
        checkpoint_status = "PASS" if decision_ok else "ALERT"

    payload = {
        "schema": "agct_sasang_stage2_d7_checkpoint_v1",
        "generated_at_utc": _fmt_utc(now),
        "track": "B_TRACK",
        "status": checkpoint_status,
        "inputs": {
            "thresholds_json": str(ns.thresholds_json.resolve()),
            "history_jsonl": str(ns.history_jsonl.resolve()),
            "promotion_gate_json": str(ns.promotion_gate_json.resolve()),
        },
        "metrics": {
            "history_rows": len(rows),
            "first_observed_at_utc": _fmt_utc(first_ts) if first_ts else None,
            "elapsed_days": round(elapsed_days, 6) if elapsed_days is not None else None,
            "min_elapsed_days_required": min_days,
            "elapsed_days_ok": elapsed_ok,
            "required_decision": required_decision,
            "current_gate_decision": gate_decision,
            "decision_ok": decision_ok,
        },
        "notes": [
            "TRACKING until D+7 elapsed threshold is reached.",
            "After elapsed threshold, status must be PASS or ALERT only.",
        ],
    }
    ns.out_json.parent.mkdir(parents=True, exist_ok=True)
    ns.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.out_json.resolve()} status={checkpoint_status}")
    if checkpoint_status == "ALERT":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
