#!/usr/bin/env python3
"""Fetch latest agmet rows from RDA-style OpenAPI endpoint.

This script is intentionally provider-agnostic and uses explicit CLI/env wiring.
It can run in dry-run mode without credentials for pipeline smoke checks.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import requests


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch agmet rows from OpenAPI and write JSON snapshot.")
    parser.add_argument("--base-url", default=os.getenv("RDA_AGMET_API_BASE_URL", "").strip())
    parser.add_argument("--endpoint", default=os.getenv("RDA_AGMET_API_ENDPOINT", "").strip())
    parser.add_argument(
        "--function",
        default=os.getenv("RDA_AGMET_API_FUNCTION", "").strip(),
        help="Optional API function path suffix (e.g. getWeatherPlpdCropList).",
    )
    parser.add_argument("--service-key", default=os.getenv("RDA_AGMET_API_KEY", "").strip())
    parser.add_argument("--start-utc", default=None, help="Optional ISO UTC start")
    parser.add_argument("--end-utc", default=None, help="Optional ISO UTC end")
    parser.add_argument("--station-code", default=os.getenv("RDA_AGMET_STATION_CODE", "").strip())
    parser.add_argument(
        "--extra-query-json",
        default="",
        help='Optional JSON object string for additional query params (e.g. {"pageNo":"1","numOfRows":"10"}).',
    )
    parser.add_argument("--timeout-sec", type=int, default=30)
    parser.add_argument(
        "--fallback-on-fail",
        action="store_true",
        help="When primary fetch fails, retry once with fallback endpoint/env.",
    )
    parser.add_argument("--fallback-base-url", default=os.getenv("NONGSARO_API_BASE_URL", "").strip())
    parser.add_argument("--fallback-endpoint", default=os.getenv("NONGSARO_API_ENDPOINT", "").strip())
    parser.add_argument(
        "--fallback-function",
        default=os.getenv("NONGSARO_API_FUNCTION", "").strip(),
        help="Optional fallback API function path suffix.",
    )
    parser.add_argument("--fallback-service-key", default=os.getenv("NONGSARO_API_KEY", "").strip())
    parser.add_argument(
        "--output-json",
        default="data/smartfarm_rda_extract_v1/out/rda_agmet_openapi_latest.json",
    )
    parser.add_argument(
        "--output-alert-json",
        default="data/smartfarm_rda_extract_v1/out/rda_agmet_openapi_alert_latest.json",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def _iso_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _parse_iso_or_default(raw: str | None, default_dt: datetime) -> str:
    if not raw:
        return default_dt.replace(microsecond=0).isoformat()
    return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(UTC).replace(microsecond=0).isoformat()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_url(base_url: str, endpoint: str, function: str) -> str:
    base = base_url.rstrip("/")
    endpoint_norm = endpoint.lstrip("/")
    function_norm = function.strip().lstrip("/")
    url = f"{base}/{endpoint_norm}" if base and endpoint_norm else ""
    if url and function_norm:
        url = f"{url}/{function_norm}"
    return url


def main() -> int:
    args = _parse_args()
    now = datetime.now(UTC)
    start_utc = _parse_iso_or_default(args.start_utc, now - timedelta(hours=24)) if args.start_utc else None
    end_utc = _parse_iso_or_default(args.end_utc, now) if args.end_utc else None

    out_path = Path(args.output_json)
    alert_path = Path(args.output_alert_json)

    url = _build_url(args.base_url, args.endpoint, args.function)

    params: dict[str, Any] = {
        "serviceKey": args.service_key,
    }
    if start_utc:
        params["startUtc"] = start_utc
    if end_utc:
        params["endUtc"] = end_utc
    if args.station_code:
        params["stationCode"] = args.station_code
    if args.extra_query_json.strip():
        try:
            extra = json.loads(args.extra_query_json)
            if isinstance(extra, dict):
                params.update(extra)
        except Exception:
            pass

    if args.dry_run:
        payload = {
            "schema": "rda_agmet_openapi_fetch_v1",
            "mode": "dry_run",
            "generated_at_utc": _iso_now(),
            "request": {"url": url, "params": params, "timeout_sec": args.timeout_sec},
        }
        _write_json(out_path, payload)
        _write_json(
            alert_path,
            {
                "schema": "rda_agmet_openapi_alert_v1",
                "generated_at_utc": _iso_now(),
                "severity": "info",
                "title": "RDA agmet OpenAPI dry-run",
                "message": "No network call executed.",
                "ref": str(out_path),
            },
        )
        print(f"[ok] dry-run snapshot -> {out_path}")
        return 0

    if not (url and args.service_key):
        _write_json(
            alert_path,
            {
                "schema": "rda_agmet_openapi_alert_v1",
                "generated_at_utc": _iso_now(),
                "severity": "warning",
                "title": "RDA agmet OpenAPI config missing",
                "message": "Set RDA_AGMET_API_BASE_URL, RDA_AGMET_API_ENDPOINT, RDA_AGMET_API_KEY.",
            },
        )
        print("[warn] missing API config; wrote alert JSON")
        return 2

    attempts: list[dict[str, Any]] = [
        {
            "source": "primary",
            "url": url,
            "params": params,
        }
    ]
    fallback_url = _build_url(args.fallback_base_url, args.fallback_endpoint, args.fallback_function)
    if args.fallback_on_fail and fallback_url and args.fallback_service_key:
        fallback_params = {**params, "serviceKey": args.fallback_service_key}
        attempts.append(
            {
                "source": "fallback",
                "url": fallback_url,
                "params": fallback_params,
            }
        )

    last_exc: Exception | None = None
    for attempt in attempts:
        try:
            resp = requests.get(attempt["url"], params=attempt["params"], timeout=args.timeout_sec)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            body: Any
            if "json" in content_type.lower():
                body = resp.json()
            else:
                body = {"raw_text": resp.text[:10000]}

            payload = {
                "schema": "rda_agmet_openapi_fetch_v1",
                "mode": "live",
                "source": attempt["source"],
                "generated_at_utc": _iso_now(),
                "request": {"url": attempt["url"], "params": {**attempt["params"], "serviceKey": "***masked***"}},
                "response_status": resp.status_code,
                "response_content_type": content_type,
                "response_body": body,
            }
            _write_json(out_path, payload)
            _write_json(
                alert_path,
                {
                    "schema": "rda_agmet_openapi_alert_v1",
                    "generated_at_utc": _iso_now(),
                    "severity": "info",
                    "title": "RDA agmet OpenAPI fetch success",
                    "message": f"HTTP {resp.status_code} via {attempt['source']}",
                    "ref": str(out_path),
                },
            )
            print(f"[ok] live snapshot ({attempt['source']}) -> {out_path}")
            return 0
        except Exception as exc:  # noqa: BLE001
            last_exc = exc

    _write_json(
        alert_path,
        {
            "schema": "rda_agmet_openapi_alert_v1",
            "generated_at_utc": _iso_now(),
            "severity": "critical",
            "title": "RDA agmet OpenAPI fetch failed",
            "message": str(last_exc) if last_exc is not None else "unknown error",
            "request_url": url,
            "fallback_enabled": bool(args.fallback_on_fail),
            "fallback_configured": bool(fallback_url and args.fallback_service_key),
        },
    )
    print(f"[err] fetch failed: {last_exc}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

