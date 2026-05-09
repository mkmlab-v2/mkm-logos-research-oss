#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "reports" / "myeongni_autobot_api_audit_log.jsonl"
DEFAULT_OUT = ROOT / "reports" / "myeongni_autobot_api_audit_summary_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Build summary metrics from myeongni autobot API audit JSONL.")
    ap.add_argument("--input-jsonl", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows = _read_jsonl(args.input_jsonl if args.input_jsonl.is_absolute() else ROOT / args.input_jsonl)
    by_status = Counter()
    by_reason = Counter()
    by_ip = Counter()
    by_route = Counter()
    for r in rows:
        by_status[str(r.get("status_code", "unknown"))] += 1
        if "reason" in r:
            by_reason[str(r.get("reason"))] += 1
        if "ip" in r:
            by_ip[str(r.get("ip"))] += 1
        if "route" in r:
            by_route[str(r.get("route"))] += 1

    total = len(rows)
    ok = by_status.get("200", 0)
    denied = by_status.get("401", 0)
    limited = by_status.get("429", 0)
    out = {
        "schema": "myeongni_autobot_api_audit_summary_v1",
        "generated_at_utc": _now(),
        "input_jsonl": str((args.input_jsonl if args.input_jsonl.is_absolute() else ROOT / args.input_jsonl).resolve()),
        "counts": {
            "total": total,
            "status_200": ok,
            "status_401": denied,
            "status_429": limited,
        },
        "ratios": {
            "ok_ratio": round(ok / total, 6) if total else 0.0,
            "unauthorized_ratio": round(denied / total, 6) if total else 0.0,
            "rate_limited_ratio": round(limited / total, 6) if total else 0.0,
        },
        "top": {
            "routes": by_route.most_common(5),
            "reasons": by_reason.most_common(5),
            "ips": by_ip.most_common(5),
        },
    }
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "total": total}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

