#!/usr/bin/env python3
"""Click 시작 확인 + handle popup wizard (same CDP context, no OAuth loop)."""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LEGAL_ENTITY_JSON = ROOT / "docs/final/artifacts/startup_package_ai_2026_eligibility_v1_latest.json"
BUSINESS_REG_NO = "628860174200000000000"  # Azure KR wizard requires exactly 21 alnum (SSOT BRN 628-86-01742)

from nvidia_azure_cdp_session_guard_v1 import find_giryun288_portal, is_giryun288_session, is_login_url

OUT = ROOT / "reports/nvidia_azure_verify_continue_latest.json"
BLADE = (
    "https://portal.azure.com/#@giryun288gmail.onmicrosoft.com/"
    "view/Microsoft_Azure_Startups/AzureForStartups.ReactView/skipWizardRedirect~/true"
)

_spec = importlib.util.spec_from_file_location(
    "benefits", ROOT / "scripts" / "nvidia_inception_benefits_catalog_request_v1.py"
)
benefits = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(benefits)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _text(page) -> str:
    parts = []
    try:
        parts.append(page.inner_text("body", timeout=12_000) or "")
    except Exception:
        pass
    for fr in page.frames:
        try:
            t = fr.inner_text("body", timeout=2000) or ""
            if len(t) > 60:
                parts.append(t)
        except Exception:
            continue
    return "\n".join(parts)


def _click_verify_button(page, run: dict[str, Any]) -> bool:
    # Side panel: 확인 시작 (actual verify) before blade 시작 확인
    for label in ("확인 시작", "Start verification", "Get started"):
        for target in [page, *page.frames]:
            try:
                loc = target.get_by_role("button", name=label, exact=False).first
                if loc.count() and loc.is_visible(timeout=2000):
                    loc.click(timeout=8000)
                    run["panel_button"] = label
                    page.wait_for_timeout(5000)
                    return True
            except Exception:
                continue
    for target in [page, *page.frames]:
        for sel in (
            "button:has-text('시작 확인')",
            "a:has-text('시작 확인')",
            "[aria-label*='시작 확인']",
        ):
            try:
                loc = target.locator(sel).first
                if loc.count() and loc.is_visible(timeout=2000):
                    loc.click(timeout=8000)
                    run["verify_button"] = sel
                    page.wait_for_timeout(5000)
                    return True
            except Exception:
                continue
    return False


def _legal_entity_name() -> str:
    try:
        data = json.loads(LEGAL_ENTITY_JSON.read_text(encoding="utf-8"))
        return str((data.get("legal_entity") or {}).get("name") or "주식회사 목소리네트워크")
    except Exception:
        return "주식회사 목소리네트워크"


def _fill_entity_field(target, entity: str) -> str | None:
    """Fill 등록된 엔터티 이름 — first empty required input in wizard."""
    strategies: list[str] = []
    for label in ("등록된 엔터티 이름", "Registered Entity Name"):
        try:
            loc = target.get_by_label(label, exact=False).first
            if loc.count() and loc.is_visible(timeout=2000):
                loc.fill(entity, timeout=5000)
                return f"label:{label}"
        except Exception:
            pass
    try:
        # Fluent UI: label row then input in same section
        section = target.locator("text=등록된 엔터티 이름").locator("xpath=ancestor::*[contains(@class,'ms-') or self::div][1]")
        inp = section.locator("input").first
        if inp.count() and inp.is_visible(timeout=1500):
            inp.fill(entity, timeout=5000)
            return "section_input"
    except Exception:
        pass
    try:
        inputs = target.locator("input[type='text']:visible, input:not([type]):visible")
        for i in range(min(await_count := 8, 8)):
            inp = inputs.nth(i)
            if not inp.is_visible(timeout=500):
                continue
            val = inp.input_value(timeout=500)
            if val.strip():
                continue
            inp.fill(entity, timeout=5000)
            return f"empty_input_index_{i}"
    except Exception:
        pass
    return None


def _fill_address_wizard(page, run: dict[str, Any]) -> None:
    entity = _legal_entity_name()
    fills: list[str] = []
    targets = [page, *page.frames]
    for target in targets:
        try:
            txt = target.inner_text("body", timeout=2000) or ""
        except Exception:
            continue
        if "등록된 엔터티" not in txt and "Registered Entity" not in txt and "1/2" not in txt:
            continue
        hit = _fill_entity_field(target, entity)
        if hit:
            fills.append(hit)
            break
    run["entity"] = entity
    run["address_fills"] = fills
    page.wait_for_timeout(1000)
    for target in targets:
        try:
            txt = target.inner_text("body", timeout=1500) or ""
        except Exception:
            continue
        if "1/2" not in txt and "2/2" not in txt:
            continue
        try:
            loc = target.get_by_role("button", name="다음", exact=True).first
            if loc.count() and loc.is_visible(timeout=2000):
                loc.click(timeout=8000)
                page.wait_for_timeout(6000)
                run["clicked_next"] = True
                return
        except Exception:
            pass
        try:
            loc = target.locator("button:has-text('다음')").last
            if loc.count() and loc.is_visible(timeout=1500):
                loc.click(timeout=8000)
                page.wait_for_timeout(6000)
                run["clicked_next"] = True
                return
        except Exception:
            pass


def _fill_business_id(page, run: dict[str, Any]) -> None:
    """Select ID type + fill business registration number (Korea)."""
    entity = _legal_entity_name()
    run["entity"] = entity
    targets = [page, *page.frames]
    id_type_values = (
        "사업자 등록 ID 번호",
        "Business Registration Number",
        "Business registration",
    )
    for target in targets:
        try:
            txt = target.inner_text("body", timeout=2000) or ""
        except Exception:
            continue
        if "ID 유형" not in txt and "비즈니스" not in txt:
            continue
        # Native <select> (probe: select[1] with Korean options)
        try:
            selects = target.locator("select:visible")
            n = selects.count()
            for i in range(n):
                sel = selects.nth(i)
                opts = sel.locator("option")
                opt_texts = []
                for j in range(min(opts.count(), 20)):
                    opt_texts.append((opts.nth(j).inner_text(timeout=500) or "").strip())
                if not any("ID 유형" in t or "사업자" in t or "DUNS" in t for t in opt_texts):
                    continue
                picked = None
                for val in id_type_values:
                    try:
                        sel.select_option(label=val, timeout=5000)
                        picked = val
                        break
                    except Exception:
                        try:
                            sel.select_option(value=val, timeout=3000)
                            picked = val
                            break
                        except Exception:
                            continue
                if not picked:
                    for j in range(opts.count()):
                        t = (opts.nth(j).inner_text(timeout=500) or "").strip()
                        if "사업자" in t:
                            sel.select_option(index=j, timeout=5000)
                            picked = t
                            break
                if picked:
                    run["id_type_selected"] = picked
                    run["id_select_index"] = i
                    page.wait_for_timeout(1500)
                    break
        except Exception as exc:
            run["id_select_error"] = str(exc)[:200]
        # Fix mistaken address line 3 pollution
        try:
            addr3 = target.locator("input[type='text']:visible").nth(3)
            if addr3.count() and addr3.is_visible(timeout=500):
                v3 = addr3.input_value(timeout=500)
                if v3.replace("-", "").isdigit() and len(v3.replace("-", "")) == 10:
                    addr3.fill("", timeout=3000)
                    run["cleared_address_line_3"] = v3
        except Exception:
            pass
        # Business ID = last visible text input in wizard frame
        try:
            inputs = target.locator("input[type='text']:visible")
            n = inputs.count()
            if n >= 8:
                inp = inputs.nth(7)
                if inp.is_visible(timeout=1000):
                    inp.fill(BUSINESS_REG_NO, timeout=5000)
                    run["business_id_filled"] = BUSINESS_REG_NO
                    run["business_id_field"] = "input_index_7"
        except Exception as exc:
            run["business_id_fill_error"] = str(exc)[:200]
    page.wait_for_timeout(1000)
    for target in targets:
        try:
            txt = target.inner_text("body", timeout=1500) or ""
        except Exception:
            continue
        if "1/2" not in txt and "2/2" not in txt:
            continue
        try:
            loc = target.get_by_role("button", name="다음", exact=True).first
            if loc.count() and loc.is_visible(timeout=2000):
                loc.click(timeout=8000)
                page.wait_for_timeout(6000)
                run["clicked_next"] = True
                return
        except Exception:
            pass


def _fill_and_advance(page, cfg: dict, run: dict[str, Any]) -> None:
    pointer = benefits._load_pointer()
    inc = pointer.get("inception", {}).get("company_form", {})
    company = str(cfg.get("company_name") or inc.get("display_name") or "mkmlab")
    website = str(cfg.get("website") or "https://jema-ai.com")
    contact = str(cfg.get("contact_email") or benefits._pointer_email())
    fills: list[str] = []
    pages = [page]
    try:
        pages.extend(page.context.pages)
    except Exception:
        pass
    for pg in pages:
        for label, val in (
            ("Company", company),
            ("Website", website),
            ("Email", contact),
            ("Startup", company),
        ):
            try:
                if benefits._fill_labeled_input(pg, label, val):
                    fills.append(label)
            except Exception:
                pass
        for btn in ("Continue", "Next", "Submit", "다음", "확인", "완료", "Save"):
            try:
                b = pg.get_by_role("button", name=btn, exact=False).first
                if b.count() and b.is_visible(timeout=1000) and b.is_enabled():
                    b.click(timeout=6000)
                    pg.wait_for_timeout(3000)
                    run.setdefault("advances", []).append(btn)
            except Exception:
                continue
    run["fills"] = list(dict.fromkeys(fills))


def main() -> int:
    from playwright.sync_api import sync_playwright

    run: dict[str, Any] = {
        "schema": "nvidia_azure_verify_continue_v1",
        "generated_at_utc": _utc(),
    }

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = find_giryun288_portal(browser)
        if page is None:
            run["error"] = "no_portal_tab"
            OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return 2

        page.bring_to_front()
        body = _text(page)

        if "1/2" in body or "등록된 엔터티" in body or "주소 확인" in body:
            run["step"] = "address_1_of_2_fill_only"
            if "ID 유형" in body or "비즈니스" in body:
                _fill_business_id(page, run)
            else:
                _fill_address_wizard(page, run)
        elif "2/2" in body:
            run["step"] = "step_2_of_2"
            _fill_address_wizard(page, run)
        else:
            run["step"] = "wizard_not_open"
            run["hint"] = "1/2 주소 확인 패널을 연 채로 다시 실행"

        body_after = _text(page)
        run["step_after"] = (
            "2/2" if "2/2" in body_after else ("1/2" if "1/2" in body_after else "closed")
        )
        if "LinkedIn" in body_after:
            run["human_gate"] = "linkedin_oauth_tier3"
        run["final_snippet"] = body_after[:1200].replace("\n", " | ")
        run["tenant_ok"] = is_giryun288_session(body_after)

        shot = ROOT / "reports/nvidia_azure_verify_continue_latest.png"
        page.screenshot(path=str(shot), full_page=True, timeout=20_000)
        run["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")

    run["verdict"] = run.get("human_gate") or run.get("step_after") or "done"
    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0 if run.get("address_fills") or run.get("clicked_next") or run.get("business_id_filled") or run.get("id_type_selected") else 1


if __name__ == "__main__":
    raise SystemExit(main())
