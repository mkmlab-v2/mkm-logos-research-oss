#!/usr/bin/env py
"""Live smoke for app.jema-ai.com/hub — delegation live1 DoD."""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/universe_hub_live_smoke_v1_latest.json"
ORIGIN = "https://app.jema-ai.com"
VALIDATION_NEEDLE = "빈 제출로 외부 사이트로 이동하지 않습니다"
UA = "MKM-Hub-LiveSmoke/1.0"


def fetch(
    url: str,
    max_bytes: int = 800_000,
    *,
    follow_redirects: bool = True,
) -> tuple[int, str, dict[str, str]]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    if follow_redirects:
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                headers = {k.lower(): v for k, v in resp.headers.items()}
                return resp.status, resp.read(max_bytes).decode("utf-8", "replace"), headers
        except urllib.error.HTTPError as exc:
            body = exc.read(500).decode("utf-8", "replace") if exc.fp else ""
            headers = {k.lower(): v for k, v in exc.headers.items()}
            return exc.code, body, headers

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
            return None

    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(req, timeout=30) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, resp.read(max_bytes).decode("utf-8", "replace"), headers
    except urllib.error.HTTPError as exc:
        body = exc.read(500).decode("utf-8", "replace") if exc.fp else ""
        headers = {k.lower(): v for k, v in exc.headers.items()}
        return exc.code, body, headers


def main() -> int:
    checks: list[dict] = []

    code_root, _, root_headers = fetch(f"{ORIGIN}/", follow_redirects=False)
    location = root_headers.get("location", "")
    root_ok = code_root in (301, 302, 307, 308) and "/hub" in location
    checks.append(
        {
            "id": "root_redirect_hub",
            "ok": root_ok,
            "detail": f"status={code_root} location={location!r}",
        }
    )

    code, html, _ = fetch(f"{ORIGIN}/hub")
    checks.append({"id": "hub_200", "ok": code == 200, "detail": f"status={code}"})

    code_cust, html_cust, _ = fetch(f"{ORIGIN}/hub/customize")
    customize_ok = code_cust == 200 and "Hub–Spoke" in html_cust and "패키지 라더" in html_cust
    if code_cust == 200 and not customize_ok:
        match = re.search(
            r"/_next/static/chunks/app/hub/customize/page-[^\"]+\.js",
            html_cust,
        )
        if match:
            ccode, chunk, _ = fetch(f"{ORIGIN}{match.group(0)}", max_bytes=2_000_000)
            customize_ok = ccode == 200 and (
                "WTT Persona OS" in chunk or "HubSpokeDiagram" in chunk
            )
    checks.append(
        {
            "id": "customize_hub_spoke",
            "ok": customize_ok,
            "detail": f"status={code_cust}",
        }
    )

    code_op, body_op, _ = fetch(f"{ORIGIN}/hub/operator")
    checks.append(
        {
            "id": "operator_403",
            "ok": code_op == 403,
            "detail": f"status={code_op} body={body_op[:80]!r}",
        }
    )

    found = VALIDATION_NEEDLE in html
    chunk_detail = "validation string in /hub html"
    if not found:
        match = re.search(r"/_next/static/chunks/app/hub/page-[^\"]+\.js", html)
        if match:
            chunk_url = f"{ORIGIN}{match.group(0)}"
            ccode, chunk, _ = fetch(chunk_url, max_bytes=2_000_000)
            found = VALIDATION_NEEDLE in chunk
            chunk_detail = f"chunk_status={ccode} needle_in_chunk={found}"
        else:
            chunk_detail = "hub page chunk not found in html"
    checks.append({"id": "empty_submit_guard", "ok": found, "detail": chunk_detail})

    payload = {
        "schema": "universe_hub_live_smoke_v1",
        "generated_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "origin": ORIGIN,
        "overall_ok": all(c["ok"] for c in checks),
        "checks": checks,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["overall_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
