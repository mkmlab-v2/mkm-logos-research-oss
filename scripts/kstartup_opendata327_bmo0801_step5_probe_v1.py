"""Probe STEP05 인력정보 fields on BMO0801."""
from playwright.sync_api import sync_playwright
from kstartup_opendata327_bmo0801_autofill_v1 import (
    _open_task_edit,
    _pick_pms_page,
    _unlock_page_for_user,
    _wait_pms_logged_in,
)

TASK = "20460558"
CDP = "http://127.0.0.1:9223"

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(CDP, timeout=15000)
    page = _pick_pms_page(b.contexts[0])
    if not _wait_pms_logged_in(page, 15):
        print("login_timeout")
        raise SystemExit(1)
    nav = _open_task_edit(page, TASK)
    print("nav", nav)
    if not nav.get("ok"):
        raise SystemExit(1)
    _unlock_page_for_user(page)
    page.locator("#mf_wfm_contents_generatorStepBox_4_stepBox").click(timeout=5000)
    page.wait_for_timeout(2000)
    info = page.evaluate(
        """() => ({
          body: (document.body.innerText||'').includes('인력정보'),
          inputs: [...document.querySelectorAll('input[id^="mf_wfm_contents_"],textarea[id^="mf_wfm_contents_"],select[id^="mf_wfm_contents_"]')]
            .filter(el => el.offsetParent !== null || el.type==='hidden')
            .map(el => ({id: el.id, tag: el.tagName, val: (el.value||'').slice(0,50), ro: el.readOnly})),
          buttons: [...document.querySelectorAll('a[id^="mf_wfm_contents_"],button[id^="mf_wfm_contents_"]')]
            .filter(el => /추가|등록|인력|저장|임시/.test(el.innerText||''))
            .map(el => ({id: el.id, text: (el.innerText||'').trim().slice(0,30)})),
        })"""
    )
    import json
    print(json.dumps(info, ensure_ascii=False, indent=2))
