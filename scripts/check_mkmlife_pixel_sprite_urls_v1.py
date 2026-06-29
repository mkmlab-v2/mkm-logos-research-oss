#!/usr/bin/env python3
"""mkmlife pixel sprite URL hard gate v1 — HTTP verify sprite_url entries in MKM_PIXEL_LANGUAGE.

Blocks deploy/report when any referenced sprite CDN URL is not reachable (2xx).
Writes reports/mkmlife_pixel_sprite_urls_gate_v1_latest.json (exit 0 = all OK).

B-track UI quality gate; not Track A compression or live trading GO.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PIXEL_JSON = ROOT / "projects/mkm/mkm-life/public/data/MKM_PIXEL_LANGUAGE_V1.json"
DEFAULT_PUBLIC_ROOT = ROOT / "projects/mkm/mkm-life/public"
DEFAULT_OUT = ROOT / "reports/mkmlife_pixel_sprite_urls_gate_v1_latest.json"
DEFAULT_ORIGIN_PIXEL_PATH = "/data/MKM_PIXEL_LANGUAGE_V1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def collect_sprite_urls(doc: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(url: str | None, *, registry: str, key: str) -> None:
        if not url or not isinstance(url, str):
            return
        u = url.strip()
        if not u or u in seen:
            return
        seen.add(u)
        rows.append({"url": u, "registry": registry, "key": key})

    for key, entry in (doc.get("category_sprite_registry") or {}).items():
        if isinstance(entry, dict):
            add(entry.get("sprite_url"), registry="category_sprite_registry", key=str(key))
    for key, entry in (doc.get("morning_beans_lane_registry") or {}).items():
        if isinstance(entry, dict):
            add(entry.get("sprite_url"), registry="morning_beans_lane_registry", key=str(key))
    return rows


def _resolve_sprite_url(url: str, *, origin: str | None) -> tuple[str, str]:
    """Return (mode, target) where mode is http|local."""
    u = url.strip()
    if u.startswith("/"):
        if origin:
            return "http", f"{origin.rstrip('/')}{u}"
        local = (DEFAULT_PUBLIC_ROOT / u.lstrip("/")).resolve()
        return "local", str(local)
    return "http", u


def _local_file_ok(path: Path) -> tuple[bool, int | None, str | None]:
    try:
        if not path.is_file():
            return False, None, "missing local file"
        size = path.stat().st_size
        if size < 32:
            return False, None, f"file too small ({size} bytes)"
        return True, 200, None
    except OSError as exc:
        return False, None, str(exc)


def _fetch_status(url: str, timeout: float) -> tuple[bool, int | None, str | None]:
    req = request.Request(url, method="GET", headers={"User-Agent": "MKM12-mkmlife-pixel-sprite-gate/1.0"})
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            code = int(getattr(resp, "status", None) or resp.getcode())
            ok = 200 <= code < 400
            return ok, code, None
    except error.HTTPError as e:
        return False, e.code, str(e.reason)
    except Exception as e:
        return False, None, str(e)


def verify_urls(
    urls: list[dict[str, str]],
    *,
    origin: str | None,
    timeout: float,
    retries: int,
    retry_delay: float,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for row in urls:
        url = row["url"]
        mode, target = _resolve_sprite_url(url, origin=origin)
        ok = False
        code: int | None = None
        err: str | None = None
        check_mode = mode
        if mode == "local":
            ok, code, err = _local_file_ok(Path(target))
        else:
            for attempt in range(max(1, retries)):
                ok, code, err = _fetch_status(target, timeout)
                if ok:
                    break
                if attempt + 1 < retries:
                    time.sleep(retry_delay)
        results.append(
            {
                **row,
                "ok": ok,
                "http_status": code,
                "error": err,
                "check_mode": check_mode,
                "resolved_target": target,
            }
        )
    return results


def load_pixel_doc(*, pixel_json: Path | None, origin: str | None, origin_path: str) -> tuple[dict[str, Any], str]:
    if origin:
        base = origin.rstrip("/")
        fetch_url = f"{base}{origin_path}"
        req = request.Request(fetch_url, headers={"User-Agent": "MKM12-mkmlife-pixel-sprite-gate/1.0"})
        with request.urlopen(req, timeout=30.0) as resp:
            doc = json.loads(resp.read().decode("utf-8"))
        return doc, fetch_url
    if not pixel_json or not pixel_json.is_file():
        raise FileNotFoundError(f"pixel language JSON missing: {pixel_json}")
    doc = json.loads(pixel_json.read_text(encoding="utf-8"))
    return doc, _rel(pixel_json)


def run_gate(
    *,
    pixel_json: Path | None,
    origin: str | None,
    origin_path: str,
    out_path: Path,
    timeout: float,
    retries: int,
    retry_delay: float,
) -> dict[str, Any]:
    doc, source = load_pixel_doc(pixel_json=pixel_json, origin=origin, origin_path=origin_path)
    if doc.get("schema") != "mkm_pixel_language_v1":
        raise ValueError(f"unexpected schema: {doc.get('schema')!r}")
    url_rows = collect_sprite_urls(doc)
    if not url_rows:
        raise ValueError("no sprite_url entries found in MKM_PIXEL_LANGUAGE")
    results = verify_urls(
        url_rows,
        origin=origin,
        timeout=timeout,
        retries=retries,
        retry_delay=retry_delay,
    )
    fail_count = sum(1 for r in results if not r["ok"])
    report = {
        "schema": "mkmlife_pixel_sprite_urls_gate_v1",
        "generated_at_utc": _utc_now(),
        "lane": "research_only",
        "hypothesis_tag": "[HYPO]",
        "track_wall": "B-track UI asset gate — not Track A compression KPI",
        "source": source,
        "origin": origin,
        "total": len(results),
        "ok_count": len(results) - fail_count,
        "fail_count": fail_count,
        "overall_ok": fail_count == 0,
        "failed_urls": [r["url"] for r in results if not r["ok"]],
        "results": results,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="mkmlife pixel sprite URL hard gate")
    ap.add_argument("--pixel-json", type=Path, default=DEFAULT_PIXEL_JSON)
    ap.add_argument(
        "--fetch-from-origin",
        dest="origin",
        default="",
        help="Live origin base URL (e.g. https://mkmlife.com); fetches public pixel JSON from origin.",
    )
    ap.add_argument("--origin-pixel-path", default=DEFAULT_ORIGIN_PIXEL_PATH)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--timeout", type=float, default=25.0)
    ap.add_argument("--url-retries", type=int, default=2)
    ap.add_argument("--url-retry-delay", type=float, default=3.0, dest="url_retry_delay")
    ap.add_argument(
        "--soft-fail",
        action="store_true",
        help="Exit 0 even when URLs fail (writes report with overall_ok=false).",
    )
    args = ap.parse_args()

    origin = args.origin.strip() or None
    pixel_json = None if origin else args.pixel_json.resolve()

    try:
        report = run_gate(
            pixel_json=pixel_json,
            origin=origin,
            origin_path=args.origin_pixel_path,
            out_path=args.out_json.resolve(),
            timeout=args.timeout,
            retries=args.url_retries,
            retry_delay=args.url_retry_delay,
        )
    except Exception as exc:
        print(f"[check_mkmlife_pixel_sprite_urls_v1] error: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "overall_ok": report["overall_ok"],
                "ok_count": report["ok_count"],
                "fail_count": report["fail_count"],
                "out": _rel(args.out_json),
            },
            ensure_ascii=False,
        )
    )
    if report["overall_ok"]:
        return 0
    if args.soft_fail:
        print("[check_mkmlife_pixel_sprite_urls_v1] soft-fail: sprite URLs failed; exit 0", flush=True)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
