#!/usr/bin/env python3
"""Live snapshot of NVIDIA Phoenix portal (CDP Chrome, read-only).

  py scripts/nvidia_phoenix_portal_snapshot_v1.py
  py scripts/nvidia_phoenix_portal_snapshot_v1.py --cdp-url http://127.0.0.1:9222
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PHOENIX_HOME = "https://programs.nvidia.com/phoenix/"
PHOENIX_BENEFITS = "https://programs.nvidia.com/phoenix/benefits"
PHOENIX_PROFILE = "https://programs.nvidia.com/phoenix/profile"
OUT = ROOT / "reports/nvidia_phoenix_portal_live_latest.json"
SSOT = ROOT / "reports/nvidia_inception_email_credit_routing_ssot_v1_latest.json"
POINTER = ROOT / "reports/nvidia_inception_account_pointer_v1.json"

PARTNER_KEYS = (
    ("aws", ("AWS", "Amazon Web Services")),
    ("gcp", ("Google Cloud", "Google")),
    ("lambda", ("Lambda",)),
    ("nebius", ("Nebius",)),
    ("azure", ("Azure", "Microsoft")),
    ("innovation_lab", ("Innovation Lab",)),
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_text(page, timeout: int = 15_000) -> str:
    try:
        return page.inner_text("body", timeout=timeout) or ""
    except Exception:
        return ""


def _logged_in(url: str, text: str) -> bool:
    u = url.lower()
    if "login" in u or "signin" in u or "auth" in u and "phoenix" not in u:
        return False
    if "sign in" in text.lower()[:800] and "benefits" not in text.lower()[:800]:
        return False
    return True


def _extract_table_rows(page) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    selectors = ("table tr", '[role="row"]', ".benefit-row", "li")
    for sel in selectors:
        try:
            els = page.locator(sel).all()
            if len(els) < 2:
                continue
            for el in els[:80]:
                try:
                    t = (el.inner_text(timeout=2000) or "").strip()
                except Exception:
                    continue
                if not t or len(t) < 6:
                    continue
                if any(k in t for k in ("Benefit", "Partner", "Status", "Requested", "Available")):
                    if len(t) < 40 and t.count("\n") < 2:
                        continue
                rows.append({"raw": t.replace("\n", " | ")[:300]})
            if rows:
                break
        except Exception:
            continue
    return rows


def _parse_table_row(raw: str) -> dict[str, Any] | None:
    if not raw or "Provider" in raw and "Status" in raw:
        return None
    parts = [p.strip() for p in raw.split("\t") if p.strip()]
    if len(parts) < 4:
        return None
    benefit, provider, btype, requestor = parts[0], parts[1], parts[2], parts[3]
    status = parts[4] if len(parts) > 4 else "unknown"
    date = parts[5] if len(parts) > 5 else None
    key = "other"
    bl = benefit.lower()
    if "aws" in bl or provider.upper() == "AWS":
        key = "aws"
    elif "google" in bl or provider.lower() == "google":
        key = "gcp"
    elif "lambda" in bl:
        key = "lambda"
    elif "nebius" in bl:
        key = "nebius"
    elif "azure" in bl or "microsoft" in bl.lower():
        key = "azure"
    elif "innovation lab" in bl:
        key = "innovation_lab"
    return {
        "partner_key": key,
        "benefit": benefit,
        "provider": provider,
        "type": btype,
        "requestor": requestor,
        "status": status,
        "requested_date": date,
        "nvidia_confirmed": "NVIDIA Confirmed" in status,
        "partner_follow_up_required": "Follow up with the partner" in status,
    }


def _dedupe_benefits(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        k = row.get("partner_key", "")
        benefit = row.get("benefit", "")
        if k in seen and k != "other":
            continue
        if benefit in seen:
            continue
        seen.add(k if k != "other" else benefit)
        seen.add(benefit)
        out.append(row)
    return out


def _parse_benefits(text: str) -> list[dict[str, Any]]:
    benefits: list[dict[str, Any]] = []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    status_re = re.compile(
        r"(Confirmed|Under Review|Pending|Approved|Rejected|Follow up|Available|Requested|Declined)",
        re.I,
    )

    for key, aliases in PARTNER_KEYS:
        found = False
        for i, line in enumerate(lines):
            if not any(a.lower() in line.lower() for a in aliases):
                continue
            ctx = " ".join(lines[max(0, i - 1) : min(len(lines), i + 6)])
            sm = status_re.search(ctx)
            status = sm.group(1) if sm else "unknown"
            amount = None
            am = re.search(r"\$[\d,]+(?:\s*[-–]\s*\$[\d,]+)?", ctx)
            if am:
                amount = am.group(0)
            benefits.append(
                {
                    "partner_key": key,
                    "title_hint": line[:120],
                    "amount_hint": amount,
                    "status_hint": status,
                    "context": ctx[:400],
                }
            )
            found = True
            break
        if not found:
            benefits.append({"partner_key": key, "status_hint": "not_found_in_page"})

    return benefits


def _probe_page(page, url: str, label: str) -> dict[str, Any]:
    page.goto(url, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(5000)
    text = _safe_text(page)
    out: dict[str, Any] = {
        "label": label,
        "url": page.url[:300],
        "title": page.title()[:200],
        "logged_in": _logged_in(page.url, text),
        "text_len": len(text),
    }
    if label == "benefits":
        raw_rows = _extract_table_rows(page)
        out["table_rows"] = raw_rows
        parsed_from_table = [
            p for p in (_parse_table_row(r.get("raw", "")) for r in raw_rows) if p
        ]
        out["benefits_canonical"] = _dedupe_benefits(parsed_from_table)
        out["benefits_parsed"] = out["benefits_canonical"] or _parse_benefits(text)
        out["has_requested"] = "Requested" in text or "requested" in text.lower()
        out["has_available"] = "Available" in text
        out["follow_up_partner"] = "Follow up with the partner" in text or "follow up" in text.lower()
    if label == "profile":
        for pat, key in (
            (r"moksorin\w*", "org_slug_hint"),
            (r"@[\w.-]+\.\w+", "email_hint"),
            (r"Approved|Under Review|Pending", "member_status_hint"),
        ):
            m = re.search(pat, text, re.I)
            if m:
                out[key] = m.group(0)
        out["snippet"] = text[:1200].replace("\n", " | ")
    if label == "home":
        out["snippet"] = text[:800].replace("\n", " | ")
    shot = ROOT / f"reports/nvidia_phoenix_{label}_live_latest.png"
    page.screenshot(path=str(shot), full_page=True, timeout=30_000)
    out["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
    return out


def _merge_ssot(snapshot: dict[str, Any]) -> None:
    benefits_step = next(
        (s for s in snapshot.get("pages", []) if s.get("label") == "benefits"),
        {},
    )
    home_step = next((s for s in snapshot.get("pages", []) if s.get("label") == "home"), {})
    parsed = benefits_step.get("benefits_canonical") or benefits_step.get("benefits_parsed") or []
    phoenix_block = {
        "last_live_probe_utc": snapshot.get("generated_at_utc"),
        "portal_base": PHOENIX_HOME,
        "org_slug": "moksorinetwork",
        "portal_welcome_user": "giryun",
        "logged_in": all(p.get("logged_in") for p in snapshot.get("pages", [])),
        "home_snippet": home_step.get("snippet", "")[:400],
        "benefits_url": PHOENIX_BENEFITS,
        "benefits": parsed,
        "follow_up_partner_cta": benefits_step.get("follow_up_partner"),
        "screenshots": [p.get("screenshot") for p in snapshot.get("pages", []) if p.get("screenshot")],
        "disambiguation": {
            "portal_login_email": "moksorinw@no1kmedi.com",
            "partner_mail_inbox": "moksorinw@gmail.com (Gmail u/1)",
            "not_inception": "jema12@mkmlife.com (Vertex Free Trial only)",
            "not_inception_mail": "giryun288@gmail.com (Gmail u/0)",
            "confirmed_means": "NVIDIA approved request; partner claim/onboarding still required for usable credits",
        },
    }
    ssot: dict[str, Any] = {}
    if SSOT.is_file():
        try:
            ssot = json.loads(SSOT.read_text(encoding="utf-8-sig"))
        except Exception:
            ssot = {}
    ssot["phoenix_portal_live"] = phoenix_block
    ssot["updated_at_utc"] = snapshot.get("generated_at_utc")
    SSOT.write_text(json.dumps(ssot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ptr: dict[str, Any] = {}
    if POINTER.is_file():
        try:
            ptr = json.loads(POINTER.read_text(encoding="utf-8-sig"))
        except Exception:
            ptr = {}
    ptr["phoenix_portal_live_json"] = str(OUT.relative_to(ROOT)).replace("\\", "/")
    ptr["routing_ssot_json"] = str(SSOT.relative_to(ROOT)).replace("\\", "/")
    ptr["last_phoenix_probe_utc"] = snapshot.get("generated_at_utc")
    POINTER.write_text(json.dumps(ptr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    args = ap.parse_args()

    snapshot: dict[str, Any] = {
        "schema": "nvidia_phoenix_portal_live_v1",
        "generated_at_utc": _utc(),
        "cdp_url": args.cdp_url,
        "pages": [],
    }

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(args.cdp_url)
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = ctx.new_page()
        for url, label in (
            (PHOENIX_HOME, "home"),
            (PHOENIX_BENEFITS, "benefits"),
            (PHOENIX_PROFILE, "profile"),
        ):
            try:
                snapshot["pages"].append(_probe_page(page, url, label))
            except Exception as exc:
                snapshot["pages"].append({"label": label, "error": str(exc)[:300]})
        page.close()

    OUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _merge_ssot(snapshot)

    logged = [p.get("logged_in") for p in snapshot["pages"]]
    print(f"OK phoenix snapshot -> {OUT}")
    print(f"logged_in per page: {logged}")
    benefits = next((p for p in snapshot["pages"] if p.get("label") == "benefits"), {})
    for b in benefits.get("benefits_canonical") or benefits.get("benefits_parsed") or []:
        amt = b.get("benefit") or b.get("amount_hint") or ""
        st = b.get("status") or b.get("status_hint") or ""
        print(f"  {b.get('partner_key')}: {st[:60]} | {amt[:50]}")
    return 0 if any(logged) else 2


if __name__ == "__main__":
    raise SystemExit(main())
