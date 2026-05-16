# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.6, L:0.5, K:0.5, M:0.7}
# Purpose: HTTP verify CDN URLs in public pixel battalion map (multi-round).
"""Verify image_url entries in public character map return HTTP 200."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP = ROOT / "docs" / "final" / "artifacts" / "pixel_battalion_character_map_public_latest.json"
OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "pixel_battalion_cdn_verify_latest.json"


def _fetch_status(url: str, timeout: float = 30.0) -> tuple[bool, int | None, str | None]:
    req = request.Request(url, method="GET", headers={"User-Agent": "MKM12-pixel-battalion-verify/1.0"})
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            code = getattr(resp, "status", None) or resp.getcode()
            ok = 200 <= int(code) < 400
            return ok, int(code), None
    except error.HTTPError as e:
        return False, e.code, str(e.reason)
    except Exception as e:
        return False, None, str(e)


def _verify_once(urls: list[str], retries: int, retry_delay: float) -> list[dict]:
    results: list[dict] = []
    for u in urls:
        ok = False
        code: int | None = None
        err: str | None = None
        for attempt in range(max(1, retries)):
            ok, code, err = _fetch_status(u)
            if ok:
                break
            if attempt + 1 < retries:
                time.sleep(retry_delay)
        results.append({"url": u, "ok": ok, "http_status": code, "error": err})
    return results


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--map-path", type=Path, default=DEFAULT_MAP)
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--round-sleep", type=float, default=20.0, dest="round_sleep_sec")
    p.add_argument("--url-retries", type=int, default=3)
    p.add_argument("--url-retry-delay", type=float, default=8.0, dest="url_retry_delay_sec")
    p.add_argument(
        "--soft-fail",
        action="store_true",
        help="Exit 0 even when some URLs fail (still writes JSON with fail_count).",
    )
    args = p.parse_args()

    if not args.map_path.exists():
        raise SystemExit(f"map missing: {args.map_path}")
    doc = json.loads(args.map_path.read_text(encoding="utf-8"))
    urls: list[str] = []
    for row in doc.get("pilot_characters") or []:
        if isinstance(row, dict) and row.get("image_url"):
            urls.append(str(row["image_url"]))

    all_results: list[dict] | None = None
    fail_count = 0
    for r in range(max(1, args.rounds)):
        all_results = _verify_once(urls, args.url_retries, args.url_retry_delay_sec)
        fail_count = sum(1 for x in all_results if not x["ok"])
        if fail_count == 0:
            break
        if r + 1 < args.rounds:
            time.sleep(args.round_sleep_sec)

    assert all_results is not None
    ok_count = sum(1 for x in all_results if x["ok"])
    payload = {
        "schema": "pixel_battalion_cdn_verify_v1",
        "checked_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "map_path": str(args.map_path.resolve()),
        "total": len(all_results),
        "ok_count": ok_count,
        "fail_count": fail_count,
        "soft_fail": bool(args.soft_fail),
        "verify_options": {
            "url_retries": args.url_retries,
            "url_retry_delay_sec": args.url_retry_delay_sec,
            "rounds": args.rounds,
            "round_sleep_sec": args.round_sleep_sec,
        },
        "results": all_results,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok_count": ok_count, "fail_count": fail_count, "out": str(OUT_JSON)}, ensure_ascii=False))
    if fail_count:
        if args.soft_fail:
            print("[verify_pixel_battalion_cdn_urls] soft-fail: CDN checks had failures; exit 0", flush=True)
            raise SystemExit(0)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
