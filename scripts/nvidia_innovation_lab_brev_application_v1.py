#!/usr/bin/env python3
"""Innovation Lab Brev application (developer.nvidia.com) — CDP or headed profile.

  py scripts/nvidia_innovation_lab_brev_application_v1.py --cdp-url http://127.0.0.1:9222 --wait-for-login-sec 180
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
PAYLOAD = ROOT / "reports/nvidia_innovation_lab_brev_application_payload_v1.json"
OUT = ROOT / "reports/nvidia_innovation_lab_brev_application_run_latest.json"
PROFILE = ROOT / "reports/nvidia_innovation_brev_playwright_profile"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _on_login_page(page) -> bool:
    url = page.url.lower()
    if "login" in url or "sign" in url and "application" not in url:
        return True
    try:
        if page.get_by_text("Log in or sign up", exact=False).count():
            return True
        if page.get_by_label("Email", exact=False).count() and page.get_by_role("button", name="Next").count():
            return True
    except Exception:
        pass
    return False


def _wait_login(page, wait_sec: int, email_hint: str) -> bool:
    if not _on_login_page(page):
        return True
    try:
        em = page.get_by_label("Email", exact=False).first
        if em.count() and em.is_visible(timeout=5000) and email_hint:
            em.fill(email_hint, timeout=5000)
            page.get_by_role("button", name="Next", exact=True).first.click(timeout=8000)
            page.wait_for_timeout(2000)
    except Exception:
        pass
    deadline = __import__("time").time() + wait_sec
    while __import__("time").time() < deadline:
        if not _on_login_page(page) and "innovation-lab" in page.url.lower():
            return True
        page.wait_for_timeout(2000)
    return not _on_login_page(page)


def _fill_labeled(page, labels: list[str], value: str) -> bool:
    for lab in labels:
        try:
            loc = page.get_by_label(lab, exact=False).first
            if loc.count() and loc.is_visible(timeout=3000):
                loc.click(timeout=3000)
                loc.fill(value, timeout=8000)
                return True
        except Exception:
            continue
    return False


def _fill_placeholder(page, patterns: list[str], value: str) -> bool:
    for pat in patterns:
        try:
            loc = page.get_by_placeholder(re.compile(pat, re.I)).first
            if loc.count() and loc.is_visible(timeout=3000):
                loc.fill(value, timeout=8000)
                return True
        except Exception:
            continue
    return False


def _select_option(page, labels: list[str], option: str) -> bool:
    for lab in labels:
        try:
            loc = page.get_by_label(lab, exact=False).first
            if loc.count():
                loc.select_option(label=option, timeout=5000)
                return True
        except Exception:
            try:
                loc.select_option(value=option, timeout=5000)
                return True
            except Exception:
                continue
    return False


def _fill_textareas(page, value: str, max_count: int = 5) -> int:
    n = 0
    for ta in page.locator("textarea").all()[:max_count]:
        try:
            if ta.is_visible(timeout=2000):
                ta.click(timeout=3000)
                ta.fill(value[: min(len(value), 4000)], timeout=8000)
                n += 1
        except Exception:
            continue
    return n


def _apply_form(page, fields: dict[str, str]) -> dict[str, bool]:
    r: dict[str, bool] = {}
    r["company_name"] = _fill_labeled(
        page, ["Company", "Organization", "Company name", "Startup"], fields["company_name"]
    ) or _fill_placeholder(page, ["company", "organization"], fields["company_name"])
    r["website"] = _fill_labeled(page, ["Website", "URL", "Company website"], fields["website"]) or _fill_placeholder(
        page, ["website", "url"], fields["website"]
    )
    r["product_name"] = _fill_labeled(
        page, ["Product", "Project name", "Application name"], fields["product_name"]
    ) or _fill_placeholder(page, ["product", "project"], fields["product_name"])
    r["use_case"] = _fill_labeled(page, ["Use case", "Describe", "Objective"], fields["use_case"])
    r["project_summary"] = _fill_labeled(
        page, ["Summary", "Description", "Project description", "Tell us"], fields["project_summary"]
    )
    r["country"] = _select_option(page, ["Country", "Region"], fields["country"])
    filled_ta = _fill_textareas(page, fields["project_summary"])
    r["textareas_filled"] = filled_ta > 0
    if not r["use_case"] and filled_ta > 0:
        r["use_case"] = True
    return r


def _check_all_requirements(page) -> int:
    n = 0
    patterns = (
        r"latency guarantees",
        r"synthetic or non-production",
        r"TB of storage",
        r"within 60 days",
        r"explore and/or optimize",
        r"acceptance is not guaranteed",
    )
    for pat in patterns:
        try:
            cb = page.get_by_role("checkbox", name=re.compile(pat, re.I)).first
            if cb.count() and not cb.is_checked():
                cb.check(force=True, timeout=5000)
                n += 1
        except Exception:
            try:
                loc = page.locator("label").filter(has_text=re.compile(pat, re.I)).first
                if loc.count():
                    loc.click(timeout=5000)
                    n += 1
            except Exception:
                continue
    return n


def _software_matrix(page, prefer: str = "Interested") -> int:
    n = 0
    for row in page.locator("tr").all():
        try:
            txt = row.inner_text(timeout=2000)
            if not txt or "Using" not in txt:
                continue
            cell = row.get_by_text(prefer, exact=True).first
            if cell.count():
                cell.click(timeout=5000)
                n += 1
        except Exception:
            continue
    if n < 5:
        for rad in page.locator(f"input[type='radio'][value*='nterest' i], input[type='radio']").all():
            try:
                name = rad.get_attribute("name") or ""
                if rad.is_visible(timeout=500) and name:
                    # one per group: pick Interested if value matches
                    val = rad.get_attribute("value") or ""
                    if "interest" in val.lower() or prefer.lower() in val.lower():
                        rad.check(force=True, timeout=3000)
                        n += 1
            except Exception:
                continue
    return n


def _fill_matrix_and_selects_js(page) -> dict[str, int]:
    return page.evaluate(
        """() => {
        let matrix = 0, selects = 0;
        const table = document.querySelector('table');
        if (table) {
            const headerRow = table.querySelector('thead tr') || table.querySelector('tr');
            let interestedCol = -1;
            if (headerRow) {
                [...headerRow.querySelectorAll('th, td')].forEach((c, i) => {
                    if ((c.textContent || '').trim() === 'Interested') interestedCol = i;
                });
            }
            table.querySelectorAll('tbody tr, tr').forEach(tr => {
                const cells = tr.querySelectorAll('td');
                if (!cells.length || cells.length < 3) return;
                if (interestedCol >= 0 && cells[interestedCol]) {
                    const r = cells[interestedCol].querySelector('input[type=radio]');
                    if (r && !r.checked) { r.click(); matrix++; return; }
                }
                tr.querySelectorAll('input[type=radio]').forEach(radio => {
                    const id = radio.id;
                    const lbl = id ? document.querySelector('label[for="' + id + '"]') : null;
                    const t = lbl ? (lbl.textContent || '').trim() : '';
                    if (t === 'Interested' && !radio.checked) { radio.click(); matrix++; }
                });
            });
        }
        document.querySelectorAll('select').forEach(sel => {
            const opt0 = sel.options[0];
            const txt = opt0 ? (opt0.text || '').toLowerCase() : '';
            if (sel.selectedIndex <= 0 || txt.includes('select')) {
                for (let i = 1; i < sel.options.length; i++) {
                    const o = sel.options[i];
                    if (o.value && !(o.text || '').toLowerCase().startsWith('select')) {
                        sel.selectedIndex = i;
                        sel.dispatchEvent(new Event('change', { bubbles: true }));
                        selects++;
                        break;
                    }
                }
            }
        });
        return { matrix, selects };
    }"""
    )


def _fill_lightning_comboboxes(page) -> int:
    n = 0
    for trigger in page.locator(
        "button:has-text('Select'), [role='combobox'], .slds-combobox__input"
    ).all():
        try:
            if not trigger.is_visible(timeout=1500):
                continue
            txt = trigger.inner_text(timeout=1000) or ""
            if "select" not in txt.lower() and trigger.get_attribute("role") != "combobox":
                continue
            trigger.click(timeout=5000)
            page.wait_for_timeout(800)
            opt = page.locator("[role='option'], .slds-listbox__option").first
            if opt.count() and opt.is_visible(timeout=3000):
                opt.click(timeout=5000)
                n += 1
                page.wait_for_timeout(500)
        except Exception:
            continue
    return n


def _fill_all_selects(page) -> int:
    n = 0
    for sel in page.locator("select").all():
        try:
            if not sel.is_visible(timeout=2000):
                continue
            cur = sel.input_value(timeout=2000)
            if cur and "select" not in cur.lower():
                continue
            opts = sel.locator("option")
            for i in range(opts.count()):
                t = (opts.nth(i).inner_text(timeout=1000) or "").strip()
                v = opts.nth(i).get_attribute("value") or ""
                if t and "select" not in t.lower()[:10] and v:
                    sel.select_option(index=i, timeout=5000)
                    n += 1
                    break
        except Exception:
            continue
    return n


def _select_first_valid_option(page, label_fragment: str) -> bool:
    try:
        sel = page.get_by_label(label_fragment, exact=False).first
        if not sel.count():
            sel = page.locator("select").filter(has=page.locator(f"text={label_fragment}")).first
        if not sel.count():
            return False
        opts = sel.locator("option")
        for i in range(opts.count()):
            val = opts.nth(i).get_attribute("value") or ""
            text = opts.nth(i).inner_text(timeout=1000) or ""
            if val and val not in ("", "Select...", "select") and "select" not in text.lower()[:8]:
                sel.select_option(index=i, timeout=5000)
                return True
    except Exception:
        pass
    return False


def _agree_terms(page) -> bool:
    try:
        terms = page.locator("input[type='checkbox']").filter(
            has=page.locator("text=Terms and Conditions")
        )
        if terms.count():
            terms.first.check(force=True, timeout=5000)
            return True
    except Exception:
        pass
    for cb in page.locator("input[type='checkbox']").all():
        try:
            parent = cb.locator("xpath=ancestor::*[contains(., 'Terms and Conditions')][1]")
            if parent.count() and not cb.is_checked():
                cb.check(force=True, timeout=5000)
                return True
        except Exception:
            continue
    try:
        page.get_by_text("Terms and Conditions", exact=False).first.click(timeout=5000)
        return True
    except Exception:
        return False


def _submit(page) -> bool:
    for label in ("Submit", "Apply", "Save", "Continue", "Next"):
        try:
            btn = page.get_by_role("button", name=label, exact=False).first
            if btn.count() and btn.is_visible(timeout=3000):
                btn.scroll_into_view_if_needed(timeout=5000)
                btn.click(timeout=10_000)
                page.wait_for_timeout(3000)
                return True
        except Exception:
            continue
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--payload", type=Path, default=PAYLOAD)
    ap.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--wait-for-login-sec", type=int, default=120)
    ap.add_argument("--no-submit", action="store_true")
    args = ap.parse_args()

    data = json.loads(args.payload.read_text(encoding="utf-8-sig"))
    url = data["application_url"]
    fields = data["fields"]
    email_hint = data.get("login_email_hint", "")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("pip install playwright && playwright install chromium", file=sys.stderr)
        return 2

    run: dict[str, Any] = {
        "schema": "nvidia_innovation_lab_brev_application_run_v1",
        "generated_at_utc": _utc(),
        "url": url,
        "logged_in": False,
        "field_results": {},
        "submitted": False,
        "screenshots": [],
    }

    with sync_playwright() as p:
        if args.cdp_url.strip():
            browser = p.chromium.connect_over_cdp(args.cdp_url.strip())
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.new_page()
        else:
            PROFILE.mkdir(parents=True, exist_ok=True)
            context = p.chromium.launch_persistent_context(
                str(PROFILE), headless=not args.headed, viewport={"width": 1400, "height": 900}
            )
            page = context.new_page()

        page.goto(url, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(3000)
        run["page_url_after_goto"] = page.url

        if _on_login_page(page):
            run["login_page"] = True
            ok = _wait_login(page, args.wait_for_login_sec, email_hint)
            run["logged_in"] = ok
            if not ok:
                run["error"] = "login_timeout — complete NVIDIA Developer login in browser (password/2FA)"
                shot = ROOT / "reports/nvidia_innovation_lab_brev_login.png"
                page.screenshot(path=str(shot), full_page=True)
                run["screenshots"].append(str(shot.relative_to(ROOT)).replace("\\", "/"))
                OUT.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
                print(json.dumps(run, indent=2))
                return 1
        else:
            run["logged_in"] = True

        page.wait_for_timeout(2000)
        run["page_url"] = page.url
        run["field_results"] = _apply_form(page, fields)
        # Fix website if typo
        _fill_labeled(page, ["Organization URL", "Website"], fields["website"])
        _fill_labeled(page, ["Organization", "University name"], fields["company_name"])

        run["checkboxes_checked"] = _check_all_requirements(page)
        run["software_matrix_selected"] = _software_matrix(page, "Interested")
        js_counts = _fill_matrix_and_selects_js(page)
        run["software_matrix_selected"] = js_counts.get("matrix", 0) or run.get("software_matrix_selected", 0)
        run["selects_filled"] = js_counts.get("selects", 0)
        if run["selects_filled"] == 0:
            run["selects_filled"] = _fill_all_selects(page)
        run["combobox_filled"] = _fill_lightning_comboboxes(page)
        run["workload_selected"] = _select_first_valid_option(page, "Project Workload") or _select_first_valid_option(
            page, "GPU workload"
        )
        run["storage_selected"] = _select_first_valid_option(page, "Data Storage") or _select_first_valid_option(
            page, "storage"
        )
        run["terms_agreed"] = _agree_terms(page)

        shot = ROOT / "reports/nvidia_innovation_lab_brev_application.png"
        page.screenshot(path=str(shot), full_page=True)
        run["screenshots"].append(str(shot.relative_to(ROOT)).replace("\\", "/"))

        if not args.no_submit:
            try:
                submit_btn = page.get_by_role("button", name="Submit", exact=True).first
                if submit_btn.count() and submit_btn.is_visible(timeout=3000):
                    submit_btn.scroll_into_view_if_needed(timeout=5000)
                    submit_btn.click(timeout=12_000)
                    run["submitted"] = True
                else:
                    run["submitted"] = _submit(page)
            except Exception:
                run["submitted"] = _submit(page)
            if run["submitted"]:
                page.wait_for_timeout(4000)
                shot2 = ROOT / "reports/nvidia_innovation_lab_brev_after_submit.png"
                page.screenshot(path=str(shot2), full_page=True)
                run["screenshots"].append(str(shot2.relative_to(ROOT)).replace("\\", "/"))
                run["page_url_after_submit"] = page.url

        if not args.cdp_url.strip():
            context.close()

    OUT.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    ok = run.get("logged_in") and (
        sum(1 for k, v in run.get("field_results", {}).items() if k != "textareas_filled" and v) >= 2
        or run.get("field_results", {}).get("textareas_filled")
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
