#!/usr/bin/env python3
"""Nebius billing — Promotions / Apply promo code (CDP, read-only apply if code known)."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "reports/nvidia_nebius_promo_claim_latest.json"
PROMO_URL = "https://console.nebius.com/tenant-e00fe2zhs67gmz6wha/billing/promotions"
PAYMENTS_URL = "https://console.nebius.com/tenant-e00fe2zhs67gmz6wha/billing/payments"
USAGE_URL = "https://console.nebius.com/tenant-e00fe2zhs67gmz6wha/billing/consumption"
LANDING = (
    "https://nebius.com/nebius-nvidia-inception-credit-offering"
    "?utm_campaign=nvidiainception&utm_medium=referral&utm_source=nvidia"
)
CLAIM_LINKS = ROOT / "reports/nvidia_inception_email_claim_links_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _text(page) -> str:
    try:
        return page.inner_text("body", timeout=15_000) or ""
    except Exception:
        return ""


def _amounts(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"\$[\d,]+(?:\.\d{2})?", text)))[:12]


def _find_console(browser):
    for ctx in browser.contexts:
        for pg in ctx.pages:
            if "console.nebius.com" in (pg.url or ""):
                return pg
    return None


def _click(page, *labels: str) -> str | None:
    for label in labels:
        for loc in (
            page.get_by_role("button", name=label, exact=False),
            page.get_by_role("link", name=label, exact=False),
            page.get_by_text(label, exact=False),
        ):
            try:
                el = loc.first
                if el.count() and el.is_visible(timeout=2000):
                    el.click(timeout=8000)
                    return label
            except Exception:
                continue
    return None


def _load_promo_codes() -> list[str]:
    codes: list[str] = []
    if CLAIM_LINKS.is_file():
        try:
            doc = json.loads(CLAIM_LINKS.read_text(encoding="utf-8-sig"))
            for em in doc.get("emails", []):
                if em.get("partner_key") != "nebius":
                    continue
                blob = " ".join(
                    filter(
                        None,
                        [
                            em.get("body_snippet"),
                            " ".join(em.get("links") or []),
                        ],
                    )
                )
                for m in re.finditer(
                    r"\b([A-Z0-9]{4,5}(?:-[A-Z0-9]{4,5}){2,5})\b",
                    blob.upper(),
                ):
                    codes.append(m.group(1))
        except Exception:
            pass
    return list(dict.fromkeys(codes))[:8]


def _try_apply_promo_dialog(page, run: dict, codes: list[str]) -> None:
    clicked = _click(
        page,
        "Apply promo code",
        "Apply promotion",
        "프로모 코드 적용",
        "프로모션 코드",
        "Redeem",
    )
    if not clicked:
        return
    run["apply_promo_clicked"] = clicked
    page.wait_for_timeout(2500)

    dialog_text = ""
    for fr in page.frames:
        try:
            t = fr.inner_text("body", timeout=1500) or ""
            if "promo" in t.lower() or "code" in t.lower():
                dialog_text = t
        except Exception:
            continue

    field = None
    for loc in (
        page.get_by_placeholder(re.compile("promo|code", re.I)),
        page.get_by_label(re.compile("promo|code", re.I)),
        page.locator("[role='dialog'] input"),
        page.locator("input[type='text']"),
        page.locator("input:not([type='hidden']):not([type='checkbox'])"),
    ):
        try:
            cand = loc.first
            if cand.count() and cand.is_visible(timeout=1500):
                field = cand
                break
        except Exception:
            continue

    if field is None and not codes:
        run["promo_dialog"] = "opened_no_input_visible"
        run["promo_dialog_snippet"] = dialog_text[:300].replace("\n", " | ")
        return

    applied = False
    trial_codes = codes or [""]
    for code in trial_codes:
        if field is not None and code:
            try:
                field.click(timeout=3000)
                field.fill(code, timeout=5000)
                run.setdefault("codes_tried", []).append(code)
            except Exception as exc:
                run["fill_error"] = str(exc)[:120]
        for btn in ("Apply", "Redeem", "Submit", "Confirm", "적용", "확인"):
            if _click(page, btn):
                run["promo_submit"] = btn
                page.wait_for_timeout(3000)
                applied = bool(code)
                break
        if applied:
            break

    body = _text(page).lower()
    run["promo_apply_result"] = {
        "applied": applied,
        "dialog_visible": bool(dialog_text),
        "success_hint": any(
            k in body for k in ("success", "applied", "activated", "적용", "완료")
        ),
        "error_hint": any(
            k in body for k in ("invalid", "expired", "not found", "required", "오류", "유효하지")
        ),
        "snippet": _text(page)[:600].replace("\n", " | "),
    }


def _claim_listed_promos(page, run: dict) -> None:
    text = _text(page)
    low = text.lower()
    if not any(k in low for k in ("inception", "nvidia", "5000", "5,000", "promo")):
        run["listed_promos"] = []
        return

    claimed = _click(
        page,
        "Claim",
        "Activate",
        "Apply",
        "Get started",
        "클레임",
        "활성화",
    )
    if claimed:
        run["listed_promo_clicked"] = claimed
        page.wait_for_timeout(3000)


def main() -> int:
    from playwright.sync_api import sync_playwright

    run: dict = {
        "schema": "nvidia_nebius_promo_claim_v1",
        "generated_at_utc": _utc(),
        "promo_codes_from_email": _load_promo_codes(),
    }

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = _find_console(browser)
        if page is None:
            page = browser.contexts[0].new_page()
            page.goto(PROMO_URL, wait_until="domcontentloaded", timeout=120_000)
        page.bring_to_front()

        if "auth.nebius.com" in (page.url or ""):
            run["human_gate"] = "nebius_session_expired_relogin"
            OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(run, ensure_ascii=False, indent=2))
            return 2

        for label, url in (
            ("promotions", PROMO_URL),
            ("payments", PAYMENTS_URL),
            ("usage", USAGE_URL),
        ):
            step: dict = {"label": label}
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=120_000)
                page.wait_for_timeout(5000)
                text = _text(page)
                step["url"] = page.url[:240]
                step["amounts"] = _amounts(text)
                step["snippet"] = text[:500].replace("\n", " | ")
                step["inception_visible"] = bool(
                    re.search(r"inception|nvidia|5000|5,000", text, re.I)
                )
                if label == "promotions":
                    _claim_listed_promos(page, step)
                if label in ("promotions", "usage", "payments"):
                    _try_apply_promo_dialog(page, step, run["promo_codes_from_email"])
                    text = _text(page)
                    step["amounts_after"] = _amounts(text)
                run.setdefault("steps", []).append(step)
            except Exception as exc:
                step["error"] = str(exc)[:200]
                run.setdefault("steps", []).append(step)

        if not run.get("promo_codes_from_email"):
            try:
                page.goto(LANDING, wait_until="domcontentloaded", timeout=120_000)
                page.wait_for_timeout(3000)
                landing_text = _text(page)
                run["landing"] = {
                    "url": page.url[:200],
                    "snippet": landing_text[:400].replace("\n", " | "),
                    "has_claim_cta": bool(
                        re.search(r"log in|subscribe|apply|claim", landing_text, re.I)
                    ),
                }
                _click(page, "Log in to AI Cloud", "Get started", "Subscribe")
                page.wait_for_timeout(3000)
            except Exception as exc:
                run["landing_error"] = str(exc)[:160]

        page.goto(PROMO_URL, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(4000)
        final_text = _text(page)
        run["final"] = {
            "url": page.url[:240],
            "balance_amounts": _amounts(final_text),
            "inception_5k_visible": bool(
                re.search(r"5000|5,000", final_text)
            ),
            "snippet": final_text[:700].replace("\n", " | "),
        }

        shot = ROOT / "reports/nvidia_nebius_promo_claim_latest.png"
        try:
            page.screenshot(path=str(shot), full_page=True, timeout=25_000)
            run["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
        except Exception:
            pass

    amounts = run.get("final", {}).get("balance_amounts") or []
    has_5k = any("5,000" in a or "5000" in a for a in amounts)
    run["claim_ok"] = has_5k or bool(
        (run.get("steps") or [{}])[-1].get("promo_apply_result", {}).get("success_hint")
    )
    if not run.get("claim_ok") and not run.get("human_gate"):
        run["human_gate"] = (
            "no_inception_promo_code_in_email_yet"
            if not run.get("promo_codes_from_email")
            else "promo_code_apply_failed_or_pending"
        )
        run["hint"] = (
            "NVIDIA Inception Nebius 메일에 프로모 코드가 아직 없을 수 있음. "
            "Phoenix Benefits Requested 반영 후 재시도 또는 Nebius 지원/랜딩 링크 확인."
        )

    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0 if run.get("claim_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
