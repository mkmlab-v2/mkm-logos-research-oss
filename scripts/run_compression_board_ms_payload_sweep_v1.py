#!/usr/bin/env python3
"""RQ-017 step 3: L1 load sweep across approx token sizes (research_only, same host)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BENCH_SCRIPT = ROOT / "scripts" / "bench_l1_api_load.py"
OUT_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "compression_board_ms_payload_sweep_v1_latest.json"


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _run_bench(
    *,
    base_url: str,
    approx_words: int,
    max_concurrent: int,
    total_requests: int,
    bench_environment: str,
    user_context: Path | None,
) -> dict[str, Any]:
    out = ROOT / "docs" / "final" / "artifacts" / f"_tmp_bench_payload_{approx_words}.json"
    cmd = [
        sys.executable,
        str(BENCH_SCRIPT),
        "--base-url",
        base_url,
        "--max-concurrent",
        str(max_concurrent),
        "--total-requests",
        str(total_requests),
        "--approx-words",
        str(approx_words),
        "--bench-environment",
        bench_environment,
        "--out",
        str(out),
    ]
    if user_context and user_context.is_file():
        cmd.extend(["--mkm-user-context-json", str(user_context)])
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    row: dict[str, Any] = {
        "approx_words": approx_words,
        "exit_code": proc.returncode,
        "bench_out": str(out.relative_to(ROOT)).replace("\\", "/"),
    }
    if proc.returncode != 0:
        row["stderr"] = (proc.stderr or "")[-500:]
        return row
    if out.is_file():
        try:
            doc = json.loads(out.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            doc = {}
        lat = doc.get("latency_ms") if isinstance(doc.get("latency_ms"), dict) else {}
        row.update(
            {
                "error_rate": doc.get("error_rate"),
                "p50_ms": lat.get("p50"),
                "p95_ms": lat.get("p95"),
                "p99_ms": lat.get("p99"),
                "generated_at_utc": doc.get("generated_at_utc"),
            }
        )
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default="http://127.0.0.1:8010")
    ap.add_argument("--approx-words", default="500,1000,2000", help="Comma-separated sizes")
    ap.add_argument("--max-concurrent", type=int, default=25)
    ap.add_argument("--total-requests", type=int, default=90)
    ap.add_argument(
        "--bench-environment",
        default="local_loopback_payload_sweep",
    )
    ap.add_argument(
        "--mkm-user-context-json",
        type=Path,
        default=ROOT / "data" / "personalization" / "mkm_user_context_v1.sample.json",
    )
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    sizes = [int(x.strip()) for x in str(args.approx_words).split(",") if x.strip()]
    runs = [
        _run_bench(
            base_url=args.base_url,
            approx_words=n,
            max_concurrent=args.max_concurrent,
            total_requests=args.total_requests,
            bench_environment=args.bench_environment,
            user_context=args.mkm_user_context_json,
        )
        for n in sizes
    ]
    ok = all(r.get("exit_code") == 0 and r.get("error_rate") == 0 for r in runs)
    doc: dict[str, Any] = {
        "schema": "compression_board_ms_payload_sweep_v1",
        "generated_at_utc": _utc_now_z(),
        "status": "[HYPO]",
        "hypothesis_tier": "B",
        "track_wall": "b_track_research_only",
        "rq": "RQ-017",
        "base_url": args.base_url,
        "runs": runs,
        "sweep_ok": ok,
        "note": "Payload size vs RTT on same host; not joined to bench token-saving without controlled A/B.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    payload = {"out": str(args.out), "sweep_ok": ok, "runs": len(runs)}
    if args.stdout_only:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"WROTE: {args.out}")
        print(json.dumps(payload, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
