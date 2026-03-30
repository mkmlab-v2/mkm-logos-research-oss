# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.8, K:0.6, M:0.4}
# Balance: 86
# Purpose: Execute state approval packet and append JSONL execution logs.
# Keywords: state, execution, approval, packet, jsonl
#!/usr/bin/env python3
"""Execute approval packet items and write execution logs (B-track only)."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _append_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _jsonl_has_idempotency_key(path: Path, key: str) -> bool:
    if not path.is_file():
        return False
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if str(row.get("idempotency_key", "")) == key:
                return True
    return False


def _try_acquire_lock(path: Path) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        return True
    except FileExistsError:
        return False


def _release_lock(path: Path) -> None:
    try:
        if path.is_file():
            path.unlink()
    except Exception:
        # Best-effort cleanup; lock auto-recovers by manual deletion if needed.
        pass


def _parse_args() -> argparse.Namespace:
    root = _workspace_root()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--packet",
        type=Path,
        default=(
            root
            / "backtest_results"
            / "LOGOS_RESONANCE_BTC_EXT_K6866_RELAXED_N2_C0_STATE_EXECUTION_APPROVAL_PACKET_TOP5.json"
        ),
        help="Approval packet JSON path",
    )
    p.add_argument(
        "--log-jsonl",
        type=Path,
        default=(
            root
            / "backtest_results"
            / "LOGOS_RESONANCE_BTC_EXT_K6866_STATE_EXECUTION_RUN_LOG.jsonl"
        ),
        help="Append-only JSONL run log path",
    )
    p.add_argument(
        "--simulate",
        action="store_true",
        help="If set, records simulated=true in logs (default: false).",
    )
    p.add_argument(
        "--idempotency-key",
        type=str,
        default=None,
        help="Optional dedupe key. If same key already exists in log JSONL, run is skipped.",
    )
    p.add_argument(
        "--lock-file",
        type=Path,
        default=None,
        help="Optional lock file path. Defaults to <log_jsonl>.lock for single-run exclusivity.",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    packet = _load_json(args.packet)
    items = packet.get("items") or []
    ts = _now_iso()
    run_id = str(uuid4())
    idem_key = str(args.idempotency_key or "")
    lock_file = args.lock_file or Path(str(args.log_jsonl) + ".lock")

    if not _try_acquire_lock(lock_file):
        print(
            json.dumps(
                {
                    "ok": True,
                    "skipped": True,
                    "reason": "execution_lock_exists",
                    "lock_file": str(lock_file),
                    "packet": str(args.packet),
                    "log_jsonl": str(args.log_jsonl),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    try:
        if idem_key and _jsonl_has_idempotency_key(args.log_jsonl, idem_key):
            print(
                json.dumps(
                    {
                        "ok": True,
                        "skipped": True,
                        "reason": "idempotency_key_exists",
                        "idempotency_key": idem_key,
                        "packet": str(args.packet),
                        "log_jsonl": str(args.log_jsonl),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

        rows: List[Dict[str, Any]] = []
        go_count = 0
        hold_count = 0

        for item in items:
            decision = str(item.get("decision", "hold")).lower()
            executed = decision == "go"
            if executed:
                go_count += 1
            else:
                hold_count += 1
            rows.append(
                {
                    "schema": "state_execution_run_log_v1",
                    "run_at_utc": ts,
                    "run_id": run_id,
                    "idempotency_key": idem_key if idem_key else None,
                    "simulate": bool(args.simulate),
                    "state_id": item.get("state_id"),
                    "decision": decision,
                    "executed": executed,
                    "target_verse_id": item.get("target_verse_id"),
                    "priority_score": item.get("priority_score"),
                    "support_regimes_observed": item.get("support_regimes_observed"),
                    "mean_cosine_observed": item.get("mean_cosine_observed"),
                    "bottleneck_cosine_observed": item.get("bottleneck_cosine_observed"),
                    "risk_level": item.get("risk_level"),
                    "reasons": item.get("reasons", []),
                    "boundary_note": "B-track only; no A-track auto-merge.",
                }
            )

        _append_jsonl(args.log_jsonl, rows)

        print(
            json.dumps(
                {
                    "ok": True,
                    "packet": str(args.packet),
                    "log_jsonl": str(args.log_jsonl),
                    "run_id": run_id,
                    "idempotency_key": idem_key if idem_key else None,
                    "items": len(items),
                    "go_count": go_count,
                    "hold_count": hold_count,
                    "simulate": bool(args.simulate),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    finally:
        _release_lock(lock_file)


if __name__ == "__main__":
    raise SystemExit(main())
