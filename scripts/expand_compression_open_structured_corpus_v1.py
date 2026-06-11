#!/usr/bin/env python3
"""Expand open structured PoC JSONL corpora (deterministic, no external fetch)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STD_OUT = ROOT / "data/compression/stateless_poc_open_structured_v1.jsonl"
LONG_OUT = ROOT / "data/compression/stateless_poc_open_structured_long_v1.jsonl"


def _std_row(i: int) -> dict[str, Any]:
    domains = (
        "open-api-weather",
        "open-api-orders",
        "open-api-auth",
        "open-api-telemetry",
        "open-api-payments",
        "open-api-inventory",
        "open-api-notifications",
        "open-api-audit",
    )
    domain = domains[i % len(domains)]
    svc = domain.replace("open-api-", "")
    if domain == "open-api-weather":
        payload = {
            "service": "weather-gateway",
            "version": "1.2",
            "request": {"lat": 37.56 + (i % 5) * 0.01, "lon": 126.97},
            "response": {
                "temp_c": 18.2 + (i % 7),
                "humidity": 62,
                "wind_ms": 3.1,
                "condition": "partly_cloudy",
            },
            "cache": "miss" if i % 3 else "hit",
            "latency_ms": 41 + (i % 9),
        }
    elif domain == "open-api-orders":
        payload = {
            "service": "order-ingest",
            "version": "3.0",
            "event": "order.created",
            "order_id": f"ord_{i:04x}",
            "sku": f"SKU-{9000 + (i % 200)}",
            "qty": 1 + (i % 4),
            "currency": "KRW",
            "amount": 42800 + i * 17,
            "channel": "mobile",
            "status": "pending_fulfillment",
        }
    elif domain == "open-api-auth":
        payload = {
            "service": "auth-edge",
            "version": "2.4",
            "method": "POST",
            "path": "/v1/token/refresh",
            "status": 200,
            "client": "dashboard",
            "scopes": ["read:metrics", "write:config"],
            "rate_limit_remaining": 118 - (i % 20),
            "trace_id": f"tr_{i:04x}",
        }
    else:
        payload = {
            "service": f"{svc}-collector",
            "host": f"api-worker-{i % 12:02d}",
            "level": "INFO",
            "span": "compress_route",
            "attributes": {
                "domain": svc,
                "shard": f"zone_{chr(ord('a') + (i % 4))}",
                "bytes_in": 1200 + i * 11,
                "bytes_out": 600 + i * 5,
                "router": "global_pivot_v1",
            },
        }
    text = json.dumps(payload, separators=(",", ":")) + (
        f' ,"seq":{i},"bench":"compression_lv1_open_structured"'
    )
    return {
        "id": f"open-struct-{i:03d}",
        "source": "open_structured_sample_v1",
        "domain_tag": domain,
        "text": text,
    }


def _long_row(i: int) -> dict[str, Any]:
    domains = (
        "open-api-weather",
        "open-api-orders",
        "open-api-auth",
        "open-api-telemetry",
        "open-api-payments",
        "open-api-inventory",
    )
    domain = domains[i % len(domains)]
    svc = domain.replace("open-api-", "")
    events = []
    for j in range(12):
        events.append(
            {
                "seq": i * 100 + j,
                "service": domain,
                "method": "POST",
                "path": f"/v1/resource/{i}",
                "status": 429 if j % 5 == 0 else 200,
                "latency_ms": 20 + j * 3,
                "request_id": f"req_{i:04d}_{j:02d}",
                "tenant": "open-bench",
                "attributes": {
                    "region": "ap-northeast-2",
                    "cache": "miss" if j % 4 == 0 else "hit",
                    "bytes_in": 400 + j * 17,
                    "bytes_out": 180 + j * 9,
                },
            }
        )
    payload = {
        "schema": "open_structured_long_v1",
        "batch": i,
        "domain_tag": domain,
        "events": events,
        "footer": "repeated_keys_for_compression_routing_must_keep_proxy_benchmark_only",
    }
    return {
        "id": f"open-long-{i:03d}",
        "source": "open_structured_long_v1",
        "domain_tag": domain,
        "text": json.dumps(payload, separators=(",", ":")),
    }


def expand(*, std_count: int = 128, long_count: int = 48) -> dict[str, Any]:
    std_lines = [_std_row(i) for i in range(std_count)]
    long_lines = [_long_row(i) for i in range(long_count)]
    STD_OUT.parent.mkdir(parents=True, exist_ok=True)
    STD_OUT.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in std_lines) + "\n",
        encoding="utf-8",
    )
    LONG_OUT.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in long_lines) + "\n",
        encoding="utf-8",
    )
    return {
        "std_path": STD_OUT.relative_to(ROOT).as_posix(),
        "std_count": std_count,
        "long_path": LONG_OUT.relative_to(ROOT).as_posix(),
        "long_count": long_count,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--std-count", type=int, default=128)
    ap.add_argument("--long-count", type=int, default=48)
    args = ap.parse_args()
    summary = expand(std_count=args.std_count, long_count=args.long_count)
    print(json.dumps({"ok": True, **summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
