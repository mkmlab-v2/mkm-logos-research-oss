#!/usr/bin/env python3
"""
Variant-B homepage smoke checker (mkmlab -> jema-ai redirect params).
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


USER_AGENT = "MKM-VariantB-Smoke/1.0"


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: Dict[str, object]


def fetch_text(url: str, timeout_sec: int = 20) -> tuple[int, str, str]:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout_sec) as resp:  # nosec B310
        status = int(getattr(resp, "status", 200))
        final_url = resp.geturl()
        body = resp.read().decode("utf-8", "ignore")
    return status, final_url, body


def check_homepage(url: str, required_fragments: List[str], name: str) -> CheckResult:
    status, final_url, body = fetch_text(url)
    contains = {fragment: (fragment in body) for fragment in required_fragments}
    ok = status == 200 and all(contains.values())
    return CheckResult(
        name=name,
        ok=ok,
        details={
            "url": url,
            "final_url": final_url,
            "status": status,
            "contains": contains,
        },
    )


def check_redirect() -> CheckResult:
    source_url = (
        "https://jema-ai.com/smartfarm?"
        "source=mkmlab_blueprint&variant=b&stage=pro&score=8&"
        "irrigation=2&logging=2&risk=2&budget=2"
    )
    status, final_url, _ = fetch_text(source_url)
    parsed = urlparse(final_url)
    qs = parse_qs(parsed.query)
    expected = {
        "source": "mkmlab_blueprint",
        "variant": "b",
        "stage": "pro",
        "score": "8",
        "irrigation": "2",
        "logging": "2",
        "risk": "2",
        "budget": "2",
    }
    actual = {k: (qs.get(k, [None])[0]) for k in expected}
    ok = status == 200 and all(actual[k] == v for k, v in expected.items())
    return CheckResult(
        name="smartfarm_redirect_params",
        ok=ok,
        details={
            "url": source_url,
            "final_url": final_url,
            "status": status,
            "expected": expected,
            "actual": actual,
        },
    )


def main() -> int:
    checks = [
        check_homepage(
            "https://mkmlab.space/",
            [
                "source=mkmlab_blueprint&variant=b",
                "/smartfarm-blueprint.html?variant=b",
            ],
            "kr_home_variant_b_links",
        ),
        check_homepage(
            "https://mkmlab.space/en.html",
            [
                "source=mkmlab_blueprint&variant=b",
                "/smartfarm-blueprint.html?variant=b",
            ],
            "en_home_variant_b_links",
        ),
        check_redirect(),
    ]

    all_ok = all(item.ok for item in checks)
    payload = {
        "schema": "variant_b_smoke_v1",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "ok": all_ok,
        "checks": [
            {"name": item.name, "ok": item.ok, "details": item.details}
            for item in checks
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
