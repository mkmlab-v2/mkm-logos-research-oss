#!/usr/bin/env python3
"""Capture Nebius/console page into web_ops_regime live observation JSON (CDP Playwright)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_web_ops_regime_cdp_probe_v1 import (
    DEFAULT_LIVE_OBS,
    capture_live_observation,
    capture_observation_from_playwright_page,
    write_live_observation_json,
)
from scripts.web_ops_regime_classifier_v1 import (
    is_auth_wall_observation,
    nebius_billing_open_url,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    ap.add_argument("--host-filter", default="console.nebius.com")
    ap.add_argument("--wait-ms", type=int, default=2000)
    ap.add_argument("--out", type=Path, default=DEFAULT_LIVE_OBS)
    ap.add_argument("--no-mirror-ide", action="store_true")
    ap.add_argument(
        "--open-url",
        default=None,
        help="Open/navigate billing tab (default: Nebius transactions URL).",
    )
    ap.add_argument(
        "--billing-fallback",
        action="store_true",
        help="Use /billing/payments instead of transactions deep link.",
    )
    ap.add_argument(
        "--no-open-url",
        action="store_true",
        help="Do not navigate; use best existing CDP tab only.",
    )
    args = ap.parse_args()
    if args.no_open_url:
        open_url = None
    elif args.open_url:
        open_url = args.open_url
    else:
        open_url = nebius_billing_open_url(prefer_transactions=not args.billing_fallback)

    try:
        obs = capture_live_observation(
            cdp_url=args.cdp_url,
            host_filter=args.host_filter,
            wait_ms=args.wait_ms,
            open_url=open_url,
        )
        if is_auth_wall_observation(obs):
            out = write_live_observation_json(
                obs,
                out=args.out,
                also_mirror_ide=not args.no_mirror_ide,
                skip_auth_wall_overwrite=True,
            )
            print(
                json.dumps(
                    {
                        "ok": False,
                        "auth_wall": True,
                        "tier": "human_tier3",
                        "preserved_existing": out.is_file()
                        and not is_auth_wall_observation(
                            json.loads(out.read_text(encoding="utf-8-sig"))
                        ),
                        "url": obs.get("url"),
                        "operator_hint_ko": "CDP Chrome 프로필에서 Nebius 로그인 후 재캡처 (Tier-3 Human).",
                    },
                    ensure_ascii=False,
                )
            )
            return 3
        out = write_live_observation_json(
            obs,
            out=args.out,
            also_mirror_ide=not args.no_mirror_ide,
        )
        print(
            json.dumps(
                {
                    "ok": True,
                    "out": str(out),
                    "url": obs.get("url"),
                    "title": obs.get("title"),
                    "hints": obs.get("hints"),
                },
                ensure_ascii=False,
            )
        )
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
