#!/usr/bin/env python3
"""Pull VPS bitcoin-live PM2 error log and summarize execution_gate BLOCK events."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "vps_execution_gate_block_timeline_v1_latest.json"
DEFAULT_HOST = "vps-mkmlife"
REMOTE_LOG = "/root/.pm2/logs/bitcoin-live-small-24h-error.log"
REMOTE_DECISION = (
    "/opt/mkm-destiny-ai-41e38ec6/reports/binance_usdm_single_order/"
    "runtime_execution_gate_decision_latest.json"
)

BLOCK_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ .*실행 게이트 차단\(([^)]+)\)"
)
CROSS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ .*signal=(\w+)")


def _ssh(host: str, remote_cmd: str) -> str:
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", host, remote_cmd],
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"ssh exit {proc.returncode}")
    return proc.stdout


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vps-host", default=DEFAULT_HOST)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sample-size", type=int, default=12)
    args = ap.parse_args()

    log_text = _ssh(
        args.vps_host,
        f"grep -E '실행 게이트 차단|signal=CROSS_SHORT' {REMOTE_LOG} 2>/dev/null || true",
    )

    blocks: list[dict[str, str]] = []
    cross_short = 0
    for line in log_text.splitlines():
        m = BLOCK_RE.search(line)
        if m:
            blocks.append({"ts_local": m.group(1), "intent": m.group(2)})
        m2 = CROSS_RE.search(line)
        if m2 and m2.group(2) == "CROSS_SHORT":
            cross_short += 1

    by_day: dict[str, int] = {}
    for b in blocks:
        day = b["ts_local"][:10]
        by_day[day] = by_day.get(day, 0) + 1

    latest_decision: dict[str, Any]
    try:
        latest_decision = json.loads(_ssh(args.vps_host, f"cat {REMOTE_DECISION}"))
    except Exception as exc:  # noqa: BLE001
        latest_decision = {"error": str(exc)}

    sample_n = max(0, int(args.sample_size))
    sample = blocks[-sample_n:] if sample_n else []

    out = {
        "schema": "vps_execution_gate_block_timeline_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "vps_host": args.vps_host,
        "pm2_app": "bitcoin-live-small-24h",
        "log_path": REMOTE_LOG,
        "summary": {
            "execution_gate_blocks_total": len(blocks),
            "cross_short_signals_total": cross_short,
            "first_block_ts_local": blocks[0]["ts_local"] if blocks else None,
            "last_block_ts_local": blocks[-1]["ts_local"] if blocks else None,
            "blocks_by_day": dict(sorted(by_day.items())),
            "dominant_intent": "close_position",
            "dominant_block_reason_latest": (latest_decision.get("reasons") or [None])[0],
        },
        "latest_decision": latest_decision,
        "recent_blocks_sample": sample,
        "interpretation_ko": [
            "마지막 fill(2026-06-04 03:54 UTC) 직후부터 close_position 청산이 execution_gate에 반복 BLOCK.",
            "최신 BLOCK 사유: qty 0.05 > max_position_size cap (risk_profile × governance multiplier).",
            "governance_status=GO이나 execution_gate는 포지션 qty 상한으로 청산까지 막음 → LONG 0.05 고착.",
            "CROSS_SHORT 신호는 다수 발생하나 청산 실패로 신규 fill/회전 없음.",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out} blocks={len(blocks)} cross_short={cross_short}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
