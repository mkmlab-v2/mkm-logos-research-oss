#!/usr/bin/env python3
"""Auto partner credit claim verification chain (CDP Chrome, read-only, no GPU).

  py scripts/nvidia_partner_credit_auto_chain_v1.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "reports/nvidia_partner_credit_auto_chain_latest.json"
SSOT = ROOT / "reports/nvidia_inception_email_credit_routing_ssot_v1_latest.json"
POINTER = ROOT / "reports/nvidia_inception_account_pointer_v1.json"

BILLING_ID = "019340-DD2318-993817"
LAMBDA_WS = "e8b0295884964f74855d5676d9e9aa45"
NEBIUS_PAYMENTS = "https://console.nebius.com/tenant-e00fe2zhs67gmz6wha/billing/payments"
NEBIUS_PROMO = "https://console.nebius.com/tenant-e00fe2zhs67gmz6wha/billing/promotions"
AZURE_STARTUPS = (
    "https://portal.azure.com/#view/Microsoft_Azure_Startups/"
    "AzureForStartups.ReactView/skipWizardRedirect~/true"
)
GCP_CREDITS = f"https://console.cloud.google.com/billing/{BILLING_ID}/credits"
GCP_STARTUP = "https://cloud.google.com/startup/apply?utm_content=eco_nvidia"
AWS_ACTIVATE = "https://aws.amazon.com/activate/portfolio/apply/"
LAMBDA_URLS = [
    f"https://cloud.lambda.ai/workspace/{LAMBDA_WS}/settings/billing",
    f"https://cloud.lambda.ai/workspace/{LAMBDA_WS}/billing",
    "https://cloud.lambda.ai/settings/billing",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _text(page, timeout: int = 15_000) -> str:
    try:
        return page.inner_text("body", timeout=timeout) or ""
    except Exception:
        return ""


def _credit_amounts(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"\$[\d,]+(?:\.\d{2})?", text)))[:12]


def _login_needed(text: str, url: str) -> bool:
    low = (text + " " + url).lower()
    return any(
        x in low
        for x in (
            "sign in",
            "log in",
            "로그인",
            "choose an account",
            "accounts.google.com/signin",
            "login.microsoftonline",
        )
    )


def _probe_gmail(page, mail_index: int = 1) -> dict[str, Any]:
    queries = [
        ("nvidia_request", "from:inceptionprogram@nvidia.com newer_than:30d"),
        ("lambda", "from:lambda (credit OR inception OR promo) newer_than:30d"),
        ("gcp", 'from:google.com (startup OR "cloud credit" OR inception) newer_than:30d'),
        ("aws", "from:aws (activate OR credit OR inception) newer_than:30d"),
        ("azure", "from:microsoft.com (startup OR credit OR founders) newer_than:30d"),
        ("nebius", "from:nebius (credit OR promo OR inception) newer_than:30d"),
    ]
    out: dict[str, Any] = {"step": "gmail_partner_mail", "mail_index": mail_index, "queries": []}
    page.goto(
        f"https://mail.google.com/mail/u/{mail_index}/#inbox",
        wait_until="domcontentloaded",
        timeout=120_000,
    )
    page.wait_for_timeout(3000)
    out["gmail_title"] = page.title()
    for label, q in queries:
        page.goto(
            f"https://mail.google.com/mail/u/{mail_index}/#search/{quote(q)}",
            wait_until="domcontentloaded",
            timeout=120_000,
        )
        page.wait_for_timeout(5000)
        body = _text(page)
        no_results = (
            "검색어와 일치하는 메일이 없습니다" in body
            or "didn't find any messages" in body.lower()
        )
        hits: list[str] = []
        if not no_results:
            for m in re.finditer(r"([^\n]{10,180})", body):
                t = re.sub(r"\s+", " ", m.group(1).strip())
                if any(k in t.lower() for k in ("lambda", "nvidia", "google", "aws", "azure", "nebius", "credit", "startup", "inception")):
                    if "Gmail에 이 대화" not in t and t not in hits:
                        hits.append(t[:160])
        out["queries"].append(
            {
                "label": label,
                "no_results": no_results,
                "hit_count": len(hits),
                "hits": hits[:8],
            }
        )
    shot = ROOT / "reports/nvidia_partner_gmail_auto_latest.png"
    page.screenshot(path=str(shot), full_page=False, timeout=20_000)
    out["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
    return out


def _probe_lambda(page) -> dict[str, Any]:
    out: dict[str, Any] = {"step": "lambda_billing_credits", "urls_tried": []}
    best_text = ""
    for url in LAMBDA_URLS:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=90_000)
            page.wait_for_timeout(5000)
            text = _text(page)
            out["urls_tried"].append({"url": url, "final_url": page.url[:200], "text_len": len(text)})
            if len(text) > len(best_text) and "404" not in text[:200]:
                best_text = text
                out["url"] = page.url[:200]
        except Exception as exc:
            out["urls_tried"].append({"url": url, "error": str(exc)[:120]})
    text = best_text or _text(page)
    out["logged_in"] = not _login_needed(text, page.url) and "lambda" in page.url.lower()
    out["credit_amounts_seen"] = _credit_amounts(text)
    out["has_credit_balance"] = any(
        k in text.lower() for k in ("credit balance", "promotional credit", "available credit", "billing credit")
    )
    out["inception_mentioned"] = "inception" in text.lower() or "nvidia" in text.lower()
    m = re.search(r"(?:credit|balance)[^\$]{0,30}(\$[\d,]+(?:\.\d{2})?)", text, re.I)
    if m:
        out["credit_balance_hint"] = m.group(1)
    out["verdict"] = (
        "credits_visible"
        if out.get("credit_balance_hint") or (out["credit_amounts_seen"] and out["has_credit_balance"])
        else "no_inception_credits_yet"
    )
    shot = ROOT / "reports/nvidia_lambda_billing_auto_latest.png"
    page.screenshot(path=str(shot), full_page=True, timeout=25_000)
    out["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
    out["snippet"] = text[:600].replace("\n", " | ")
    return out


def _probe_gcp(page) -> dict[str, Any]:
    out: dict[str, Any] = {"step": "gcp_billing_credits", "billing_id": BILLING_ID}
    page.goto(GCP_CREDITS, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(7000)
    text = _text(page)
    out["url"] = page.url[:200]
    out["logged_in"] = not _login_needed(text, page.url)
    credits: list[dict[str, str]] = []
    for block in re.split(r"\n{2,}", text):
        if "$" in block or "₩" in block or "크레딧" in block or "Credit" in block:
            line = re.sub(r"\s+", " ", block.strip())[:200]
            if len(line) > 10:
                credits.append({"line": line})
    out["credit_blocks"] = credits[:15]
    out["nvidia_inception_in_page"] = bool(re.search(r"nvidia|inception|startup program", text, re.I))
    out["has_active_credits"] = bool(re.search(r"remaining|잔액|available|남", text, re.I))
    shot = ROOT / "reports/nvidia_gcp_credits_auto_latest.png"
    page.screenshot(path=str(shot), full_page=True, timeout=25_000)
    out["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
    # startup apply status page
    page.goto(GCP_STARTUP, wait_until="domcontentloaded", timeout=90_000)
    page.wait_for_timeout(4000)
    st = _text(page)
    out["startup_apply"] = {
        "url": page.url[:200],
        "snippet": st[:400].replace("\n", " | "),
        "apply_or_status": any(k in st.lower() for k in ("apply", "status", "approved", "pending", "신청")),
    }
    out["verdict"] = (
        "nvidia_startup_credit_listed"
        if out["nvidia_inception_in_page"]
        else "no_nvidia_inception_credit_in_billing_yet"
    )
    return out


def _probe_nebius(page) -> dict[str, Any]:
    out: dict[str, Any] = {"step": "nebius_billing_promo"}
    for label, url in (("payments", NEBIUS_PAYMENTS), ("promotions", NEBIUS_PROMO)):
        page.goto(url, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(5000)
        text = _text(page)
        block: dict[str, Any] = {
            "label": label,
            "url": page.url[:200],
            "logged_in": not _login_needed(text, page.url),
            "amounts": _credit_amounts(text),
            "snippet": text[:400].replace("\n", " | "),
        }
        if label == "payments":
            m = re.search(r"Balance\s*\$?([\d,.]+)", text, re.I)
            if m:
                block["balance_usd"] = float(m.group(1).replace(",", ""))
            out["payments"] = block
        else:
            out["promotions"] = block
    promo_text = (out.get("promotions") or {}).get("snippet", "")
    pay_url = (out.get("payments") or {}).get("url", "")
    logged_in_console = "auth.nebius.com" not in pay_url and "console.nebius.com" in pay_url
    out["logged_in_console"] = logged_in_console
    out["inception_5k_promo"] = logged_in_console and bool(
        re.search(r"5000|5,000|inception|nvidia.*promo", promo_text, re.I)
    )
    out["verdict"] = (
        "inception_promo_visible"
        if out["inception_5k_promo"]
        else ("session_expired" if "auth.nebius.com" in pay_url else "prepaid_only_no_inception_promo")
    )
    shot = ROOT / "reports/nvidia_nebius_billing_auto_latest.png"
    page.screenshot(path=str(shot), full_page=True, timeout=25_000)
    out["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
    return out


def _probe_azure(page) -> dict[str, Any]:
    out: dict[str, Any] = {"step": "azure_startups_hub"}
    page.goto(AZURE_STARTUPS, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(7000)
    text = _text(page)
    out["url"] = page.url[:200]
    out["logged_in"] = "moksorinw@gmail.com" in text or "onmicrosoft.com" in text.lower()
    out["linkedin_verification"] = "LinkedIn" in text
    out["credit_amounts_seen"] = _credit_amounts(text)
    out["inception_mentioned"] = "inception" in text.lower() or "nvidia" in text.lower()
    out["verdict"] = (
        "linkedin_gate"
        if out["linkedin_verification"]
        else ("credits_visible" if out["credit_amounts_seen"] else "no_startup_credits_yet")
    )
    shot = ROOT / "reports/nvidia_azure_startups_auto_latest.png"
    page.screenshot(path=str(shot), full_page=True, timeout=25_000)
    out["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
    out["snippet"] = text[:500].replace("\n", " | ")
    return out


def _probe_aws(page) -> dict[str, Any]:
    out: dict[str, Any] = {"step": "aws_activate_landing"}
    page.goto(AWS_ACTIVATE, wait_until="domcontentloaded", timeout=90_000)
    page.wait_for_timeout(4000)
    text = _text(page)
    out["url"] = page.url[:200]
    out["logged_in"] = "sign in" not in text.lower()[:500] or "aws" in page.url
    out["snippet"] = text[:400].replace("\n", " | ")
    out["verdict"] = "landing_only_check_email_for_portfolio_link"
    return out


def _summarize(steps: list[dict[str, Any]]) -> dict[str, Any]:
    by = {s.get("step"): s for s in steps if s.get("step")}
    return {
        "lambda": by.get("lambda_billing_credits", {}).get("verdict"),
        "gcp": by.get("gcp_billing_credits", {}).get("verdict"),
        "nebius": by.get("nebius_billing_promo", {}).get("verdict"),
        "azure": by.get("azure_startups_hub", {}).get("verdict"),
        "aws": by.get("aws_activate_landing", {}).get("verdict"),
        "gmail_new_partner_mail": any(
            not q.get("no_results")
            for q in by.get("gmail_partner_mail", {}).get("queries", [])
            if q.get("label") in ("aws", "gcp", "azure", "nebius")
        ),
        "any_usable_inception_credit": False,
    }


def _patch_ssot(run: dict[str, Any]) -> None:
    summary = run.get("summary") or {}
    ssot: dict[str, Any] = {}
    if SSOT.is_file():
        try:
            ssot = json.loads(SSOT.read_text(encoding="utf-8-sig"))
        except Exception:
            pass
    ssot["partner_claim_auto_chain"] = {
        "last_run_utc": run.get("generated_at_utc"),
        "artifact": str(OUT.relative_to(ROOT)).replace("\\", "/"),
        "summary": summary,
        "steps": [
            {
                "step": s.get("step"),
                "verdict": s.get("verdict"),
                "credit_balance_hint": s.get("credit_balance_hint"),
                "balance_usd": (s.get("payments") or {}).get("balance_usd"),
            }
            for s in run.get("steps", [])
            if s.get("step")
        ],
    }
    ssot["updated_at_utc"] = run.get("generated_at_utc")
    SSOT.write_text(json.dumps(ssot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ptr: dict[str, Any] = {}
    if POINTER.is_file():
        try:
            ptr = json.loads(POINTER.read_text(encoding="utf-8-sig"))
        except Exception:
            pass
    ptr["last_partner_claim_auto_utc"] = run.get("generated_at_utc")
    ptr["partner_claim_auto_chain"] = str(OUT.relative_to(ROOT)).replace("\\", "/")
    ec = ptr.setdefault("email_routing_no1kmedi", {})
    ec["partner_claim_status_as_of_auto"] = summary
    POINTER.write_text(json.dumps(ptr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    run: dict[str, Any] = {
        "schema": "nvidia_partner_credit_auto_chain_v1",
        "generated_at_utc": _utc(),
        "cost_policy": {"no_gpu": True, "no_new_charges": True, "read_only": True},
        "steps": [],
    }

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = ctx.new_page()
        probes = (
            _probe_gmail,
            _probe_lambda,
            _probe_gcp,
            _probe_nebius,
            _probe_azure,
            _probe_aws,
        )
        for probe in probes:
            try:
                run["steps"].append(probe(page))
            except Exception as exc:
                run["steps"].append({"step": probe.__name__, "error": str(exc)[:300]})
        page.close()

    run["summary"] = _summarize(run["steps"])
    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _patch_ssot(run)

    print(f"OK -> {OUT}")
    print(json.dumps(run["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
