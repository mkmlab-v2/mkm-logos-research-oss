#!/usr/bin/env python3
"""Live probe: no1kmedi.com apex must serve national KM /ask (not a-codeai or hub leak)."""
from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "no1kmedi_national_km_ask_live_probe_v1_latest.json"

APEX = "https://no1kmedi.com"
ASK = f"{APEX}/ask"

GOOD_MARKERS = (
    "no1kmedi 한의학 AI",
    "대국민 한의학",
    "NationalKmAsk",
    "km-ask-app",
    "km-ask-title",
)
BAD_MARKERS = (
    "A-CODEAI",
    "Token Compression Open Bench",
    "a-codeai.com",
    "Join Waitlist for Controlled Beta",
)


def _fetch(url: str, *, follow: bool = False) -> dict:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "mkm-no1kmedi-national-km-probe/1"},
        method="GET",
    )
    row: dict = {"url": url, "ok": False}
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            row["status"] = resp.status
            body = resp.read(120_000).decode("utf-8", errors="replace")
            row["final_url"] = resp.geturl()
            row["body_len"] = len(body)
            row["body_sample"] = body[:400]
            row["body"] = body
            row["ok"] = 200 <= int(resp.status) < 400
    except urllib.error.HTTPError as e:
        row["status"] = e.code
        body = e.read(8000).decode("utf-8", errors="replace") if e.fp else ""
        row["body"] = body
        row["body_sample"] = body[:400]
        row["ok"] = False
    except (urllib.error.URLError, ssl.SSLError, TimeoutError) as e:
        row["error"] = str(e)[:300]
    return row


def _redirect_probe(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "mkm-no1kmedi-national-km-probe/1"},
        method="GET",
    )
    row: dict = {"url": url, "ok": False}
    try:
        ctx = ssl.create_default_context()

        class NoRedirect(urllib.request.HTTPErrorProcessor):
            def http_response(self, request, response):
                return response

            https_response = http_response

        no_redir = urllib.request.build_opener(NoRedirect)
        with no_redir.open(req, timeout=25) as resp:
            row["status"] = resp.status
            row["location"] = resp.headers.get("Location")
            row["ok"] = int(resp.status) in (200, 301, 302, 307, 308)
    except urllib.error.HTTPError as e:
        row["status"] = e.code
        row["location"] = e.headers.get("Location") if e.headers else None
        row["ok"] = e.code in (301, 302, 307, 308) or (200 <= e.code < 400)
    except (urllib.error.URLError, ssl.SSLError, TimeoutError) as e:
        row["error"] = str(e)[:300]
    return row


def _classify_html(body: str) -> dict:
    good = [m for m in GOOD_MARKERS if m in body]
    bad = [m for m in BAD_MARKERS if m in body]
    return {
        "good_markers": good,
        "bad_markers": bad,
        "looks_like_national_km_ask": bool(good) and not bad,
        "looks_like_acodeai_leak": bool(bad),
    }


def main() -> int:
    root_redir = _redirect_probe(f"{APEX}/")
    ask_page = _fetch(ASK, follow=True)
    body = ask_page.get("body") or ""
    classification = _classify_html(body)

    loc = (root_redir.get("location") or "").lower()
    root_to_ask = "/ask" in loc or ask_page.get("final_url", "").rstrip("/").endswith("/ask")

    gate_ok = classification["looks_like_national_km_ask"] and not classification["looks_like_acodeai_leak"]
    all_ok = gate_ok and ask_page.get("ok") and root_to_ask

    out = {
        "schema": "no1kmedi_national_km_ask_live_probe_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "all_ok": all_ok,
        "root_redirect": root_redir,
        "ask_page": {
            "status": ask_page.get("status"),
            "final_url": ask_page.get("final_url"),
            "ok": ask_page.get("ok"),
            "classification": classification,
        },
        "root_to_ask": root_to_ask,
        "recover_hint": (
            "VPS: bash scripts/deploy/linux/fix_no1kmedi_domain_recommended_v1.sh "
            "&& pm2 restart no1kmedi-com — ensure apex vhost proxies :3010 with Host no1kmedi.com; "
            "disable conflicting a-codeai/mkmlab apex vhost. "
            "Local repro: py scripts/probe_no1kmedi_national_km_ask_live_v1.py"
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if all_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
