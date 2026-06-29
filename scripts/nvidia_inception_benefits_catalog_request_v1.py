#!/usr/bin/env python3
"""Request Inception benefits from nvidia.com/programs/benefits/ (Tier-3: human login once).

  py scripts/nvidia_inception_benefits_catalog_request_v1.py --headed --wait-for-login-sec 300
  py scripts/nvidia_inception_benefits_catalog_request_v1.py --cdp-url http://127.0.0.1:9222

Skips Innovation Lab (already under review). Pop-ups must be allowed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "nvidia_inception_portal_product_autofill_v1",
    ROOT / "scripts" / "nvidia_inception_portal_product_autofill_v1.py",
)
autofill = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(autofill)

CATALOG_URL = "https://www.nvidia.com/programs/benefits/"
OUT = ROOT / "reports/nvidia_inception_benefits_catalog_request_latest.json"
PROFILE_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / "NvidiaInceptionAutofillChrome"

REQUEST_BLURB = (
    "MKM Document Intelligence Platform — B2B document compression & RAG "
    "(research harness ~47.5% token savings, ~0.89 Jaccard Golden-40). "
    "GPU credits for TensorRT-LLM/vLLM serving and Nemotron fine-tuning benchmarks. "
    "Not live trading. https://jema-ai.com"
)

# Order: highest GPU value first. Innovation Lab excluded (submitted_under_review).
DEFAULT_TARGETS = [
    "$100,000 in AWS Cloud Credits",
    "$2,000-$350,000 in Google Cloud Credits",
    "$7,500 in Lambda Cloud Credits",
    "$5,000 Nebius Cloud Credits",
    "$5,000 in Microsoft Azure Cloud Credits",
]

SKIP_PATTERNS = ("Innovation Lab", "英途", "创投", "技术赋能", "MathWorks", "Lintasarta", "Bria")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


FORM_ANSWERS_PATH = ROOT / "reports/nvidia_inception_benefits_form_answers_v1.json"
POINTER_PATH = ROOT / "reports/nvidia_inception_account_pointer_v1.json"


def _load_pointer() -> dict[str, Any]:
    if not POINTER_PATH.is_file():
        return {}
    try:
        return json.loads(POINTER_PATH.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _load_form_answers() -> dict[str, Any]:
    if FORM_ANSWERS_PATH.is_file():
        try:
            return json.loads(FORM_ANSWERS_PATH.read_text(encoding="utf-8-sig"))
        except Exception:
            pass
    return {}


def _pointer_email() -> str:
    pointer = _load_pointer()
    return (
        pointer.get("inception", {}).get("primary_login_email")
        or pointer.get("ngc", {}).get("cli_email_last_seen")
        or ""
    )


def _pointer_company_name() -> str:
    answers = _load_form_answers()
    if answers.get("company_name"):
        return str(answers["company_name"])
    pointer = _load_pointer()
    inc = pointer.get("inception", {}).get("company_form", {})
    return (
        inc.get("display_name")
        or pointer.get("inception", {}).get("organization_portal_name")
        or "mkmlab"
    )


def _validation_error_count(popup) -> int:
    n = 0
    for msg in ("This field is required", "Please complete this required field"):
        try:
            n += popup.get_by_text(msg, exact=False).count()
        except Exception:
            pass
    return n


def _airtable_select_answer(popup, question_substr: str, answer: str) -> bool:
    """Airtable form: find question row and pick Yes/No (or other) from dropdown."""
    try:
        row = popup.locator("div, label, p, span").filter(
            has_text=question_substr[:40]
        ).first
        if not row.count():
            return False
        container = row.locator("xpath=ancestor::*[self::div][position()<=6]").last
        for trigger in (
            container.locator("[role='combobox']"),
            container.locator("select"),
            container.locator("button").filter(has_text="Select"),
            container.locator("[class*='select']"),
        ):
            try:
                t = trigger.first
                if t.count() and t.is_visible(timeout=1500):
                    t.click(timeout=5000)
                    popup.wait_for_timeout(400)
                    opt = popup.get_by_role("option", name=answer, exact=True).first
                    if not opt.count():
                        opt = popup.get_by_text(answer, exact=True).first
                    if opt.count() and opt.is_visible(timeout=2000):
                        opt.click(timeout=5000)
                        popup.wait_for_timeout(300)
                        return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def _fill_labeled_input(popup, label_substr: str, value: str) -> bool:
    if not value:
        return False
    try:
        label = popup.get_by_text(label_substr, exact=False).first
        if label.count():
            block = label.locator("xpath=ancestor::*[self::div][position()<=5]").last
            for inp in (
                block.locator("input[type='text']"),
                block.locator("input[type='email']"),
                block.locator("input:not([type='hidden'])"),
            ):
                try:
                    field = inp.first
                    if field.count() and field.is_visible(timeout=1500):
                        field.click(timeout=3000)
                        field.fill(value, timeout=5000)
                        return True
                except Exception:
                    continue
        for ph in (label_substr, "Company Email", "Email"):
            loc = popup.get_by_placeholder(ph, exact=False).first
            if loc.count() and loc.is_visible(timeout=1000):
                loc.fill(value, timeout=5000)
                return True
    except Exception:
        pass
    return False


def _fill_airtable_benefit_form(popup, benefit_title: str, out: dict[str, Any]) -> None:
    """Fill NVIDIA partner Airtable popups (AWS/GCP/Azure 등)."""
    if "airtable.com" not in (popup.url or "").lower():
        return
    answers = _load_form_answers()
    company = str(answers.get("company_name") or _pointer_company_name())
    email = str(answers.get("company_email") or _pointer_email())
    desc = str(answers.get("description") or REQUEST_BLURB)
    fills: list[str] = []

    for q in answers.get("airtable_questions", []):
        match = str(q.get("match", ""))
        ans = str(q.get("answer", ""))
        if match and ans and _airtable_select_answer(popup, match, ans):
            fills.append(f"q:{match[:24]}={ans}")

    if answers.get("certify_checkbox", True):
        try:
            box = popup.get_by_role("checkbox").first
            if box.count() and box.is_visible(timeout=2000) and not box.is_checked():
                box.check(timeout=5000)
                fills.append("certify")
        except Exception:
            try:
                popup.get_by_text("Certify", exact=False).first.click(timeout=5000)
                fills.append("certify_label")
            except Exception:
                pass

    if _fill_labeled_input(popup, "Company Name", company):
        fills.append("company_name")
    if _fill_labeled_input(popup, "Company Email", email):
        fills.append("company_email")

    use_desc = answers.get("use_description_in", "notes_only")
    if use_desc == "notes_only":
        for ta in popup.locator("textarea").all():
            try:
                if not ta.is_visible(timeout=1000):
                    continue
                label_near = ta.locator("xpath=ancestor::*[self::div][position()<=4]").first
                txt = (label_near.inner_text(timeout=1000) or "").lower()
                if "company name" in txt:
                    continue
                ta.fill(desc, timeout=8000)
                fills.append("description_textarea")
                break
            except Exception:
                continue

    errs_before = _validation_error_count(popup)
    out["form_fills"] = fills
    out["validation_errors_before_submit"] = errs_before
    out["form_filled"] = bool(fills)

    skip = benefit_title in (answers.get("skip_submit_benefits") or [])
    only_if_clean = answers.get("submit_only_if_no_validation_errors", True)
    if skip:
        out["submit_skipped"] = "skip_submit_benefits"
        return
    if only_if_clean and errs_before > 0:
        out["submit_skipped"] = f"validation_errors={errs_before}"
        return

    for btn in ("Submit", "Apply", "Save", "Next", "Continue"):
        try:
            b = popup.get_by_role("button", name=btn, exact=False).first
            if b.count() and b.is_visible(timeout=2000) and b.is_enabled():
                b.click(timeout=8000)
                popup.wait_for_timeout(2500)
                errs_after = _validation_error_count(popup)
                out["submitted"] = btn if errs_after == 0 else False
                out["validation_errors_after_submit"] = errs_after
                out["submit_ok"] = errs_after == 0
                break
        except Exception:
            continue


def _phone_digits_ok(popup) -> bool:
    try:
        tel = popup.locator("input[type='tel']").first
        if not tel.count():
            return False
        raw = (tel.input_value(timeout=2000) or "")
        digits = re.sub(r"\D", "", raw)
        return len(digits) >= 10
    except Exception:
        return False


def _fill_lambda_benefit_form(popup, out: dict[str, Any]) -> None:
    """Lambda HubSpot lead form — lambda.ai/nvidia-inception."""
    if "lambda.ai" not in (popup.url or "").lower():
        return
    cfg = _load_form_answers().get("lambda") or {}
    pointer = _load_pointer()
    inc = pointer.get("inception", {}).get("company_form", {})
    fields = {
        "FIRST NAME": str(cfg.get("first_name") or pointer.get("inception", {}).get("welcome_display_name", "Giryun")),
        "LAST NAME": str(cfg.get("last_name") or "Lee"),
        "BUSINESS EMAIL": str(cfg.get("business_email") or _pointer_email()),
        "ORGANIZATION": str(cfg.get("organization") or inc.get("display_name") or "mkmlab"),
        "WEBSITE URL": str(cfg.get("website_url") or inc.get("website") or "https://jema-ai.com"),
    }
    phone = str(cfg.get("phone") or os.environ.get("MKM_INCEPTION_CONTACT_PHONE", "")).strip()
    phone_digits = re.sub(r"\D", "", phone)
    if phone_digits.startswith("82"):
        phone_digits = phone_digits[2:]
    if phone_digits.startswith("0"):
        phone_digits = phone_digits[1:]
    fills: list[str] = []

    for btn_text in (
        "Decline Non-essential",
        "필수적이지 않은 항목 거부",
        "Reject All",
        "Accept All",
        "모두 동의",
    ):
        try:
            b = popup.get_by_role("button", name=btn_text, exact=False).first
            if b.count() and b.is_visible(timeout=1500):
                b.click(timeout=5000)
                popup.wait_for_timeout(800)
                fills.append("cookie_dismiss")
                break
        except Exception:
            continue

    for label, value in fields.items():
        if not value:
            continue
        try:
            inp = popup.get_by_label(label, exact=False).first
            if inp.count() and inp.is_visible(timeout=2000):
                inp.fill(value, timeout=5000)
                fills.append(label.lower().replace(" ", "_"))
                continue
            inp = popup.locator(f"input[placeholder*='{label.split()[0]}' i]").first
            if inp.count() and inp.is_visible(timeout=1500):
                inp.fill(value, timeout=5000)
                fills.append(label.lower().replace(" ", "_"))
        except Exception:
            continue

    hubspot_map = {
        "firstname": fields["FIRST NAME"],
        "lastname": fields["LAST NAME"],
        "email": fields["BUSINESS EMAIL"],
        "company": fields["ORGANIZATION"],
        "website": fields["WEBSITE URL"],
        "jobtitle": str(cfg.get("job_title") or "CEO"),
    }
    for name, value in hubspot_map.items():
        if not value:
            continue
        try:
            inp = popup.locator(f"input[name='{name}']").first
            if inp.count() and inp.is_visible(timeout=1500):
                cur = (inp.input_value(timeout=1000) or "").strip()
                if not cur:
                    inp.fill(value, timeout=5000)
                    fills.append(name)
        except Exception:
            continue

    try:
        phone_inp = popup.get_by_label("PHONE", exact=False).first
        if phone_inp.count() and phone_inp.is_visible(timeout=1500):
            existing = (phone_inp.input_value(timeout=2000) or "").strip()
            if phone and not existing:
                phone_inp.fill(phone, timeout=5000)
                fills.append("phone")
            elif existing and len(existing.replace("+", "").replace(" ", "")) >= 8:
                fills.append("phone_existing")
                phone = existing
    except Exception:
        pass
    if phone_digits and "phone" not in fills and "phone_existing" not in fills:
        try:
            tel = popup.locator("input[type='tel']").first
            if tel.count() and tel.is_visible(timeout=2000):
                tel.click(timeout=3000)
                tel.fill(f"+82 {phone_digits}", timeout=5000)
                fills.append("phone")
                phone = phone_digits
        except Exception:
            pass

    country = str(cfg.get("country") or "South Korea")
    try:
        country_inp = popup.get_by_label("COUNTRY", exact=False).first
        if country_inp.count() and country_inp.is_visible(timeout=1500):
            country_inp.click(timeout=3000)
            popup.wait_for_timeout(300)
            popup.get_by_text(country, exact=False).first.click(timeout=5000)
            fills.append("country")
    except Exception:
        pass

    job = str(cfg.get("job_role") or "Founder / CEO")
    try:
        role = popup.locator("select[name='job_role']").first
        if role.count() and role.is_visible(timeout=2000):
            try:
                role.select_option(label=job)
            except Exception:
                role.select_option(value=job)
            fills.append("job_role")
        else:
            role = popup.get_by_label("JOB ROLE", exact=False).first
            if role.count() and role.is_visible(timeout=2000):
                role.select_option(label=job)
                fills.append("job_role")
            else:
                role.click(timeout=3000)
                popup.wait_for_timeout(400)
                popup.get_by_text(job, exact=False).first.click(timeout=5000)
                fills.append("job_role_click")
    except Exception:
        pass

    jtitle = str(cfg.get("job_title") or "CEO")
    if _fill_labeled_input(popup, "JOB TITLE", jtitle):
        fills.append("job_title")

    spend_raw = str(cfg.get("gpu_cloud_spend") or "0").replace("$", "").strip() or "0"
    try:
        spend_inp = popup.locator("input[name='cloud_spend']").first
        if spend_inp.count() and spend_inp.is_visible(timeout=2000):
            spend_inp.fill(spend_raw, timeout=5000)
            fills.append("cloud_spend")
    except Exception:
        pass

    try:
        tech = popup.locator("textarea[name='nvidia_technology'], input[name='nvidia_technology']").first
        if tech.count() and tech.is_visible(timeout=2000):
            nvidia_use = str(cfg.get("nvidia_platform_use") or REQUEST_BLURB)
            tech.fill(nvidia_use, timeout=8000)
            fills.append("nvidia_technology")
    except Exception:
        pass

    nvidia_use = str(cfg.get("nvidia_platform_use") or REQUEST_BLURB)
    if "nvidia_technology" not in fills:
      for ta in popup.locator("textarea").all():
        try:
            if not ta.is_visible(timeout=1000):
                continue
            block = ta.locator("xpath=ancestor::*[self::div][position()<=6]").first
            txt = (block.inner_text(timeout=1500) or "").lower()
            if "nvidia" in txt or "accelerated" in txt or not fills.count("nvidia_use"):
                ta.fill(nvidia_use, timeout=8000)
                fills.append("nvidia_use")
                break
        except Exception:
            continue

    errs_before = _validation_error_count(popup)
    out["form_fills"] = fills
    out["validation_errors_before_submit"] = errs_before
    out["form_filled"] = len(fills) >= 4
    has_phone = bool(phone_digits) and (
        "phone" in fills or "phone_existing" in fills or _phone_digits_ok(popup)
    )
    if errs_before > 0 or not has_phone:
        out["submit_skipped"] = "lambda_incomplete" if not has_phone else f"validation_errors={errs_before}"
        return

    try:
        consent = popup.locator("input[name*='LEGAL_CONSENT']").first
        if consent.count() and consent.is_visible(timeout=1500) and not consent.is_checked():
            consent.check(timeout=5000)
            fills.append("legal_consent")
    except Exception:
        pass

    for btn in ("Apply now", "Submit", "Get started", "Apply", "Send", "Continue"):
        try:
            b = popup.get_by_role("button", name=btn, exact=False).first
            if b.count() and b.is_visible(timeout=2000) and b.is_enabled():
                b.click(timeout=8000)
                popup.wait_for_timeout(2500)
                errs_after = _validation_error_count(popup)
                out["submitted"] = btn if errs_after == 0 else False
                out["validation_errors_after_submit"] = errs_after
                out["submit_ok"] = errs_after == 0
                break
        except Exception:
            continue
    if not out.get("submit_ok"):
        try:
            sub = popup.locator("input[type='submit'][value*='Apply' i]").first
            if sub.count() and sub.is_visible(timeout=2000):
                sub.click(timeout=8000)
                popup.wait_for_timeout(3000)
                errs_after = _validation_error_count(popup)
                out["submitted"] = "Apply now input"
                out["validation_errors_after_submit"] = errs_after
                out["submit_ok"] = errs_after == 0
        except Exception:
            pass
    try:
        body = popup.inner_text("body", timeout=5000) or ""
        if any(k in body.lower() for k in ("thank you", "thanks for", "submitted", "received your")):
            out["submit_ok"] = True
            out["thank_you_detected"] = True
    except Exception:
        pass


def _fill_gcp_partner_form(popup, out: dict[str, Any]) -> None:
    """Google Cloud startup apply — Google 계정 로그인 후 cloud.google.com/startup/apply."""
    url = (popup.url or "").lower()
    if "accounts.google.com" not in url and "cloud.google.com" not in url:
        return
    cfg = _load_form_answers().get("gcp") or {}
    gemail = str(
        cfg.get("google_account_email")
        or _load_pointer().get("email_routing_no1kmedi", {}).get("forward_to_gmail")
        or "moksorinw@gmail.com"
    )
    fills: list[str] = []

    if "accounts.google.com" in url:
        try:
            email_inp = popup.locator("input[type='email']").first
            if email_inp.count() and email_inp.is_visible(timeout=5000):
                email_inp.fill(gemail, timeout=8000)
                fills.append("google_email")
            for btn_name in ("Next", "다음"):
                btn = popup.get_by_role("button", name=btn_name, exact=False).first
                if btn.count() and btn.is_visible(timeout=2000):
                    btn.click(timeout=8000)
                    popup.wait_for_timeout(4000)
                    fills.append("google_next")
                    break
        except Exception:
            pass
        out["form_fills"] = fills
        out["human_gate"] = "google_password_mfa"
        if "challenge/pwd" in (popup.url or "").lower() or popup.locator("input[type='password']").count():
            out["human_gate"] = "google_password_mfa_on_screen"
        out["form_filled"] = bool(fills)
        return

    popup.wait_for_load_state("domcontentloaded", timeout=60_000)
    popup.wait_for_timeout(2000)
    company = str(cfg.get("startup_company_name") or _pointer_company_name())
    website = str(cfg.get("website") or "https://jema-ai.com")

    for label, value in (
        ("Company name", company),
        ("Company", company),
        ("Organization", company),
        ("Website", website),
        ("Company website", website),
    ):
        if _fill_labeled_input(popup, label, value):
            fills.append(label.lower().replace(" ", "_"))

    for ta in popup.locator("textarea").all():
        try:
            if ta.is_visible(timeout=1500):
                ta.fill(str(cfg.get("description") or REQUEST_BLURB), timeout=8000)
                fills.append("description")
                break
        except Exception:
            continue

    try:
        sk = popup.get_by_text("South Korea", exact=False).first
        if sk.count() and sk.is_visible(timeout=2000):
            sk.click(timeout=5000)
            fills.append("country")
    except Exception:
        pass

    errs = _validation_error_count(popup)
    out["form_fills"] = fills
    out["validation_errors_before_submit"] = errs
    out["form_filled"] = len(fills) >= 2
    if errs > 0:
        out["submit_skipped"] = f"validation_errors={errs}"
        return
    for btn in ("Submit", "Apply", "Continue", "Next", "Get started"):
        try:
            b = popup.get_by_role("button", name=btn, exact=False).first
            if b.count() and b.is_visible(timeout=2000) and b.is_enabled():
                b.click(timeout=8000)
                popup.wait_for_timeout(3000)
                out["submitted"] = btn
                out["submit_ok"] = _validation_error_count(popup) == 0
                break
        except Exception:
            continue


def _try_nvidia_sso_email(page) -> bool:
    email = _pointer_email()
    if not email:
        return False
    for loc in (
        page.get_by_placeholder("Enter your business email", exact=False),
        page.get_by_label("Email", exact=False),
        page.get_by_label("Business Email", exact=False),
        page.locator("input[type='email']"),
        page.locator("input[name*='email' i]"),
        page.locator("input[id*='email' i]"),
    ):
        try:
            field = loc.first
            if field.count() and field.is_visible(timeout=3000):
                field.fill(email, timeout=5000)
                for btn in (
                    page.get_by_role("button", name="Continue", exact=False),
                    page.get_by_role("button", name="Next", exact=False),
                    page.get_by_role("button", name="Sign Up / Login", exact=False),
                    page.get_by_role("button", name="Sign in", exact=False),
                ):
                    try:
                        b = btn.first
                        if b.count() and b.is_visible(timeout=2000):
                            b.click(timeout=5000)
                            page.wait_for_timeout(2500)
                            return True
                    except Exception:
                        continue
                return True
        except Exception:
            continue
    return False


def _bootstrap_session(page, context) -> tuple[str, Any]:
    """Phoenix logged-in session often unlocks benefits catalog. Returns (mode, active_page)."""
    page.goto("https://programs.nvidia.com/phoenix/benefits", wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(2500)
    if _catalog_logged_in(page) or "programs/benefits" in page.url:
        return "phoenix_benefits", page
    if autofill._logged_in(page):
        try:
            explore = page.get_by_text("Explore Benefits", exact=False).first
            if explore.count() and explore.is_visible(timeout=5000):
                with context.expect_page(timeout=20_000) as pinfo:
                    explore.click(timeout=10_000)
                cat = pinfo.value
                cat.wait_for_load_state("domcontentloaded", timeout=60_000)
                cat.wait_for_timeout(2000)
                return "explore_new_tab", cat
        except Exception:
            pass
    page.goto(CATALOG_URL, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(2500)
    return "catalog_direct", page


def _catalog_logged_in(page) -> bool:
    url = page.url.lower()
    if "login.nvgs.nvidia.com" in url:
        return False
    if "/login" in url and "phoenix" not in url and "programs/benefits" not in url:
        return False
    try:
        if page.get_by_placeholder("Search Benefits", exact=False).count():
            return True
        if page.get_by_text("Exclusive Member Benefits", exact=False).count():
            return True
        if page.get_by_text("Showing", exact=False).count() and page.get_by_text("Results", exact=False).count():
            return True
    except Exception:
        pass
    return "programs/benefits" in url and "login" not in url


def _wait_catalog_login(page, wait_sec: int) -> bool:
    if _catalog_logged_in(page):
        return True
    deadline = time.time() + wait_sec
    while time.time() < deadline:
        if _catalog_logged_in(page):
            return True
        time.sleep(2)
    return _catalog_logged_in(page)


def _set_region_south_korea(page) -> bool:
    for label in ("South Korea", "대한민국", "Korea"):
        try:
            btn = page.get_by_role("button", name=label, exact=False).first
            if btn.count() and btn.is_visible(timeout=2000):
                btn.click(timeout=5000)
                page.wait_for_timeout(1500)
                return True
        except Exception:
            continue
    try:
        region = page.get_by_text("Region", exact=False).first
        if region.count():
            region.click(timeout=3000)
            page.wait_for_timeout(500)
            sk = page.get_by_text("South Korea", exact=False).first
            if sk.count():
                sk.click(timeout=5000)
                page.wait_for_timeout(2000)
                return True
    except Exception:
        pass
    return False


def _search_queries_for_title(title: str) -> list[str]:
    """Catalog 검색어 — 긴 제목이 안 맞을 때 짧은 키워드 폴백."""
    queries = [title]
    if "Google Cloud" in title:
        queries.extend(["Google Cloud Credits", "Google Cloud"])
    if "AWS" in title:
        queries.extend(["AWS Cloud Credits", "AWS"])
    if "Lambda" in title:
        queries.extend(["Lambda Cloud", "Lambda"])
    if "Azure" in title:
        queries.extend(["Microsoft Azure", "Azure Cloud"])
    if "Nebius" in title:
        queries.append("Nebius")
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out


def _search_benefit(page, query: str) -> bool:
    for sel in (
        page.get_by_placeholder("Search Benefits", exact=False),
        page.locator("input[type='search']"),
        page.locator("input[placeholder*='Search' i]"),
    ):
        try:
            loc = sel.first
            if loc.count() and loc.is_visible(timeout=3000):
                loc.click(timeout=3000)
                loc.fill("", timeout=3000)
                loc.fill(query, timeout=5000)
                page.keyboard.press("Enter")
                page.wait_for_timeout(2500)
                return True
        except Exception:
            continue
    return False


def _click_request_on_page(page, context, title: str) -> dict[str, Any]:
    out: dict[str, Any] = {"title": title, "tile_clicked": False, "request_clicked": False, "popup_url": ""}
    try:
        tile = page.locator("a, button, [role='button'], [role='link']").filter(has_text=title).first
        if not tile.count():
            tile = page.get_by_text(title, exact=False).first
        if tile.count() and tile.is_visible(timeout=5000):
            tile.scroll_into_view_if_needed(timeout=5000)
            tile.click(timeout=10_000)
            page.wait_for_timeout(2000)
            out["tile_clicked"] = True
    except Exception as exc:
        out["tile_error"] = str(exc)[:200]
        return out

    popup = page
    try:
        with context.expect_page(timeout=12_000) as pinfo:
            for req in (
                page.get_by_role("button", name="Request Benefit"),
                page.get_by_role("link", name="Request Benefit"),
                page.get_by_text("Request Benefit", exact=False),
                page.locator("button, a").filter(has_text="Request Benefit"),
                page.locator("button, a").filter(has_text="Request"),
            ):
                try:
                    loc = req.first
                    if loc.count() and loc.is_visible(timeout=3000):
                        loc.click(timeout=10_000)
                        out["request_clicked"] = True
                        break
                except Exception:
                    continue
        if out["request_clicked"]:
            popup = pinfo.value
            popup.wait_for_load_state("domcontentloaded", timeout=60_000)
            popup.wait_for_timeout(2000)
            out["popup_url"] = popup.url
    except Exception:
        for req in (
            page.get_by_role("button", name="Request Benefit"),
            page.get_by_text("Request Benefit", exact=False),
        ):
            try:
                loc = req.first
                if loc.count() and loc.is_visible(timeout=3000):
                    loc.click(timeout=10_000)
                    out["request_clicked"] = True
                    page.wait_for_timeout(3000)
                    out["popup_url"] = page.url
                    popup = page
                    break
            except Exception:
                continue

    if out["request_clicked"]:
        if "airtable.com" in (out.get("popup_url") or "").lower():
            _fill_airtable_benefit_form(popup, title, out)
        elif "lambda.ai" in (out.get("popup_url") or "").lower():
            _fill_lambda_benefit_form(popup, out)
        elif "accounts.google.com" in (out.get("popup_url") or "").lower() or "cloud.google.com/startup" in (out.get("popup_url") or "").lower():
            _fill_gcp_partner_form(popup, out)
        else:
            for ta in popup.locator("textarea").all():
                try:
                    if ta.is_visible(timeout=2000):
                        ta.fill(REQUEST_BLURB, timeout=8000)
                        out["form_filled"] = True
                        break
                except Exception:
                    continue
            for btn in ("Submit", "Apply", "Save", "Next", "Continue"):
                try:
                    b = popup.get_by_role("button", name=btn, exact=False).first
                    if b.count() and b.is_visible(timeout=2000) and b.is_enabled():
                        b.click(timeout=8000)
                        popup.wait_for_timeout(2000)
                        out["submitted"] = btn
                        out["submit_ok"] = True
                        break
                except Exception:
                    continue
        shot = ROOT / f"reports/nvidia_benefit_request_{title[:30].replace(' ', '_').replace('$', '')}.png"
        try:
            popup.screenshot(path=str(shot), timeout=15_000)
            out["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
        except Exception:
            pass

    return out


def _should_skip(title: str) -> bool:
    t = title.lower()
    return any(p.lower() in t for p in SKIP_PATTERNS)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--cdp-url", default="")
    ap.add_argument("--wait-for-login-sec", type=int, default=120)
    ap.add_argument("--region", default="South Korea")
    ap.add_argument("--dry-run", action="store_true", help="Navigate only; no Request clicks")
    ap.add_argument("--targets", nargs="*", default=None)
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("pip install playwright && playwright install chromium", file=sys.stderr)
        return 2

    targets = args.targets or DEFAULT_TARGETS
    run: dict[str, Any] = {
        "schema": "nvidia_inception_benefits_catalog_request_v1",
        "generated_at_utc": _utc(),
        "catalog_url": CATALOG_URL,
        "region": args.region,
        "dry_run": args.dry_run,
        "skip_patterns": list(SKIP_PATTERNS),
        "targets": targets,
        "results": [],
    }

    with sync_playwright() as p:
        browser = None
        context = None
        page = None

        if args.cdp_url.strip():
            browser = p.chromium.connect_over_cdp(args.cdp_url.strip())
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.pages[0] if context.pages else context.new_page()
            autofill._inject_storage_state(context)
        else:
            # Do NOT use launch_persistent_context on NvidiaInceptionAutofillChrome —
            # conflicts with system Chrome (TargetClosedError / exit 2147483651).
            # Use: scripts/Start-ChromeForNvidiaInceptionCdp_v1.ps1 then --cdp-url
            browser = p.chromium.launch(
                headless=not args.headed,
                channel="chrome",
            )
            context = browser.new_context(viewport={"width": 1440, "height": 960})
            autofill._inject_storage_state(context)
            page = context.new_page()
            run["launch_mode"] = "ephemeral_chrome_channel"

        bootstrap, page = _bootstrap_session(page, context)

        if not _catalog_logged_in(page):
            autofill._try_phoenix_email_gate(page)
            _try_nvidia_sso_email(page)
        if not _catalog_logged_in(page):
            page.goto(CATALOG_URL, wait_until="domcontentloaded", timeout=120_000)
            page.wait_for_timeout(2000)
            _try_nvidia_sso_email(page)

        run["bootstrap"] = bootstrap
        if not _catalog_logged_in(page):
            if not _wait_catalog_login(page, args.wait_for_login_sec):
                run["error"] = "login_timeout — log in (allow pop-ups), then re-run"
                run["page_url"] = page.url
                OUT.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
                print(json.dumps(run, ensure_ascii=False, indent=2))
                if browser and not args.cdp_url:
                    browser.close()
                elif context and not args.cdp_url:
                    context.close()
                return 1

        try:
            autofill._save_storage_state(context)
            run["storage_state_saved"] = True
        except Exception:
            run["storage_state_saved"] = False

        run["region_set"] = _set_region_south_korea(page)
        run["page_url"] = page.url

        shot0 = ROOT / "reports/nvidia_benefits_catalog_before_requests.png"
        if autofill._safe_screenshot(page, shot0):
            run["screenshot_catalog"] = str(shot0.relative_to(ROOT)).replace("\\", "/")

        if args.dry_run:
            OUT.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(run, ensure_ascii=False, indent=2))
            if browser and not args.cdp_url:
                browser.close()
            return 0

        for title in targets:
            if _should_skip(title):
                run["results"].append({"title": title, "skipped": "skip_pattern"})
                continue
            found = False
            for q in _search_queries_for_title(title):
                if _search_benefit(page, q):
                    found = True
                    break
            if not found:
                run["results"].append({"title": title, "skipped": "search_miss"})
                continue
            item = _click_request_on_page(page, context, title)
            run["results"].append(item)
            page.goto(CATALOG_URL, wait_until="domcontentloaded", timeout=120_000)
            page.wait_for_timeout(2000)
            _set_region_south_korea(page)

        shot1 = ROOT / "reports/nvidia_benefits_catalog_after_requests.png"
        if autofill._safe_screenshot(page, shot1):
            run["screenshot_after"] = str(shot1.relative_to(ROOT)).replace("\\", "/")

        if browser and not args.cdp_url:
            browser.close()

    ok = any(
        r.get("submit_ok") or (r.get("request_clicked") and r.get("popup_url") and "nebius.com" in r.get("popup_url", ""))
        for r in run.get("results", [])
    )
    OUT.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0 if ok or run.get("region_set") else 1


if __name__ == "__main__":
    raise SystemExit(main())
