"""K-Startup PMS BMO0801 — OpenData 327 과제 20460495 STEP02~04 autofill (Playwright CDP).

Usage (external Chrome, user logged in on CDP window):
  chrome.exe --remote-debugging-port=9222 --user-data-dir=%LOCALAPPDATA%\\kstartup-cdp-profile
  py scripts/kstartup_opendata327_bmo0801_autofill_v1.py --cdp-url http://127.0.0.1:9222 --wait-for-login-sec 180
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "kstartup_opendata327_bmo0801_autofill_latest.json"

TASK_ID = "20460495"
TASK_ID_FALLBACKS = (TASK_ID, "20460558")
HISTORY_URL = "https://pms.k-startup.go.kr/biz/screen/NCOB0101M0100"
HISTORY_URL_LEGACY = "https://pms.k-startup.go.kr/biz/screen/BMO1101M0100"
HISTORY_URLS = (HISTORY_URL, HISTORY_URL_LEGACY)
FORM_URL = "https://pms.k-startup.go.kr/biz/screen/BMO0801M0100"

TSKS_NM = "정책자금 융자 신청서 자동 초안 생성(RAG·근거연동·출력보류)"
TSKS_CTNT = (
    "공고·신청서식·기재요령·사업계획서 예시를 버전관리·인덱싱하고, "
    "기업정보와 RAG로 항목별 초안을 생성한다. "
    "근거 미연결·필수누락 시 출력보류(HOLD) 후 담당자 확인을 거쳐 "
    "PDF(hwp 단계적) 산출·감사로그를 제공한다."
)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _pick_pms_page(context) -> Any:
    for page in context.pages:
        if "pms.k-startup.go.kr" in (page.url or ""):
            return page
    if context.pages:
        return context.pages[-1]
    return context.new_page()


def _dismiss_alerts(page) -> None:
    for _ in range(5):
        try:
            btn = page.get_by_role("button", name="확인")
            if btn.count() and btn.first.is_visible():
                btn.first.click(timeout=800)
                page.wait_for_timeout(400)
                continue
        except Exception:
            pass
        try:
            link = page.get_by_role("link", name="확인")
            if link.count() and link.first.is_visible():
                link.first.click(timeout=800)
                page.wait_for_timeout(400)
                continue
        except Exception:
            pass
        break


def _set_input(page, selector: str, value: str) -> bool:
    loc = page.locator(selector)
    if not loc.count():
        return False
    el = loc.first
    try:
        if el.get_attribute("readonly"):
            return False
    except Exception:
        pass
    try:
        el.scroll_into_view_if_needed(timeout=2000)
    except Exception:
        pass
    try:
        el.fill(value, timeout=5000)
        page.wait_for_timeout(200)
        return True
    except Exception:
        pass
    try:
        el.fill(value, force=True, timeout=5000)
        page.wait_for_timeout(200)
        return True
    except Exception:
        pass
    try:
        ok = page.evaluate(
            """([sel, val]) => {
              const el = document.querySelector(sel);
              if (!el || el.readOnly) return false;
              el.value = val;
              el.dispatchEvent(new Event('input', { bubbles: true }));
              el.dispatchEvent(new Event('change', { bubbles: true }));
              return true;
            }""",
            [selector, value],
        )
        page.wait_for_timeout(200)
        return bool(ok)
    except Exception:
        return False


def _wait_pms_logged_in(page, wait_sec: int, *, target_url: str = "") -> bool:
    import time

    if target_url:
        try:
            page.goto(target_url, wait_until="domcontentloaded", timeout=120_000)
            page.wait_for_timeout(2000)
        except Exception:
            pass

    deadline = time.time() + wait_sec
    while time.time() < deadline:
        url = page.url or ""
        body = ""
        try:
            body = page.inner_text("body", timeout=3000)
        except Exception:
            pass
        if "pms.k-startup.go.kr" in url and "webLGIN" not in url and "tokenInfoRelay" not in url:
            task_hit = any(tid in body for tid in TASK_ID_FALLBACKS)
            if (
                "로그아웃" in body
                or "사업신청" in body
                or task_hit
                or "과제번호" in body
                or "수정하기" in body
                or "제출서류" in body
                or "BMO0902" in url
                or "BMO0801" in url
                or "BMO1101" in url
            ):
                return True
        page.wait_for_timeout(1500)
    return False


def _resolve_task_id(page, preferred: str) -> str | None:
    if preferred:
        return preferred
    page.goto(HISTORY_URL_LEGACY, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(3500)
    _dismiss_alerts(page)
    try:
        body = page.inner_text("body", timeout=10_000)
    except Exception:
        body = ""
    for tid in TASK_ID_FALLBACKS:
        if tid in body:
            return tid
    return None


def _click_bmo1101_edit(page, task_id: str) -> str | None:
    edit_id = page.evaluate(
        """(taskId) => {
          for (const el of document.querySelectorAll('[id$="_btn_edit"]')) {
            let p = el.parentElement;
            for (let i = 0; i < 12 && p; i++, p = p.parentElement) {
              const t = (p.innerText || '').replace(/\\s+/g, ' ').trim();
              if (!t.includes(taskId)) continue;
              if (!/과제번호\\s*:/.test(t)) continue;
              const idx = t.indexOf(taskId);
              const others = (t.match(/20\\d{6}/g) || []).filter(x => x !== taskId);
              if (others.some(o => t.slice(0, idx).includes(o))) continue;
              return el.id;
            }
          }
          return null;
        }""",
        task_id,
    )
    if edit_id:
        return edit_id
    return page.evaluate(
        """(taskId) => {
          for (const el of document.querySelectorAll('[id$="_btn_edit"]')) {
            let p = el.parentElement;
            for (let i = 0; i < 12 && p; i++, p = p.parentElement) {
              if ((p.innerText || '').includes(taskId)) return el.id;
            }
          }
          return null;
        }""",
        task_id,
    )


def _open_task_edit(page, task_id: str) -> dict[str, Any]:
    if "BMO0801" in (page.url or ""):
        try:
            body = page.inner_text("body", timeout=8000)
        except Exception:
            body = ""
        if task_id in body:
            return {"ok": True, "task": task_id, "url": page.url, "via": "already_on_bmo0801"}

    edit_id: str | None = None
    opened_from = ""
    for hist_url in HISTORY_URLS:
        page.goto(hist_url, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(3500)
        _dismiss_alerts(page)
        try:
            body = page.inner_text("body", timeout=10_000)
        except Exception:
            body = ""
        if task_id not in body:
            continue
        edit_id = _click_bmo1101_edit(page, task_id)
        if edit_id:
            opened_from = hist_url
            break
        row = page.locator("tr").filter(has_text=task_id)
        if row.count():
            edit = row.first.get_by_role("link", name="수정하기")
            if edit.count():
                edit.first.click(timeout=10_000)
                edit_id = "fallback_row_edit"
                opened_from = hist_url
                break

    if not edit_id:
        return {
            "ok": False,
            "reason": "history row not found",
            "history_urls_tried": list(HISTORY_URLS),
        }

    if edit_id != "fallback_row_edit":
        page.locator(f"#{edit_id}").click(timeout=10_000)
    page.wait_for_timeout(5000)
    _dismiss_alerts(page)
    if "BMO0801" not in (page.url or ""):
        page.goto(FORM_URL, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(4000)
        _dismiss_alerts(page)
    body = page.inner_text("body", timeout=10_000)
    if "모의공고" in body:
        return {"ok": False, "reason": "mock announcement banner detected"}
    return {"ok": True, "task": task_id, "url": page.url, "edit_id": edit_id, "via": opened_from}


def _expand_corp_detail_fields(page) -> bool:
    try:
        return bool(
            page.evaluate(
                """() => {
                  let changed = false;
                  document
                    .querySelectorAll(
                      '[id^="mf_wfm_contents_dt_H"],[id^="mf_wfm_contents_dd_H"],[id^="mf_wfm_contents_H016"]'
                    )
                    .forEach((el) => {
                      if (getComputedStyle(el).display === 'none' || el.offsetHeight === 0) {
                        el.style.display = 'block';
                        el.style.height = 'auto';
                        changed = true;
                      }
                    });
                  document.querySelectorAll('dl[id^="mf_wfm_contents_wq_uuid"]').forEach((el) => {
                    if (el.offsetHeight === 0) {
                      el.style.height = 'auto';
                      changed = true;
                    }
                  });
                  return changed;
                }"""
            )
        )
    except Exception:
        return False


def _unlock_page_for_user(page) -> dict:
    try:
        return page.evaluate(
            """() => {
              const out = {removed: []};
              for (const id of ['_modal', 'mf_wfm_contents_NBMO0421P01']) {
                const el = document.getElementById(id);
                if (el) {
                  el.style.display = 'none';
                  el.style.pointerEvents = 'none';
                  out.removed.push(id);
                }
              }
              document.querySelectorAll('.w2modal_popup').forEach((el) => {
                el.style.display = 'none';
                el.style.pointerEvents = 'none';
              });
              document.body.style.pointerEvents = 'auto';
              document.body.style.overflow = 'auto';
              return out;
            }"""
        )
    except Exception:
        return {"removed": []}


def _close_blocking_modals(page) -> None:
    for sel in (
        "#mf_wfm_contents_NBMO0421P01_wframe_btn_close2",
        "#mf_wfm_contents_NBMO0421P01_wframe_btn_close",
        "#mf_wfm_contents_NBMO0421P01_close",
    ):
        try:
            loc = page.locator(sel)
            if loc.count() and loc.first.is_visible():
                loc.first.click(timeout=3000)
                page.wait_for_timeout(800)
                _dismiss_alerts(page)
                return
        except Exception:
            pass


def _click_save(page) -> bool:
    _close_blocking_modals(page)
    _dismiss_alerts(page)
    try:
        ok = page.evaluate(
            """() => {
              const el = document.querySelector('#mf_wfm_contents_btn_save');
              if (!el) return false;
              el.scrollIntoView({block: 'center'});
              el.click();
              return true;
            }"""
        )
        if ok:
            page.wait_for_timeout(2000)
            _dismiss_alerts(page)
            return True
    except Exception:
        pass
    for sel in (
        "#mf_wfm_contents_btn_save",
        '[id="mf_wfm_contents_btn_save"]',
    ):
        try:
            loc = page.locator(sel)
            if loc.count():
                loc.first.scroll_into_view_if_needed(timeout=2000)
                loc.first.click(timeout=5000)
                page.wait_for_timeout(2000)
                _dismiss_alerts(page)
                return True
        except Exception:
            pass
    for name in ("저장", "임시저장"):
        try:
            link = page.get_by_role("link", name=name)
            if link.count() and link.first.is_visible():
                link.first.click(timeout=5000)
                page.wait_for_timeout(2000)
                _dismiss_alerts(page)
                return True
        except Exception:
            pass
        try:
            btn = page.get_by_role("button", name=name)
            if btn.count() and btn.first.is_visible():
                btn.first.click(timeout=5000)
                page.wait_for_timeout(2000)
                _dismiss_alerts(page)
                return True
        except Exception:
            pass
    return False


def _fill_step2(page) -> dict[str, Any]:
    _close_blocking_modals(page)
    _expand_corp_detail_fields(page)
    auto_input = False
    for label, eid in (
        ("기업상세정보 불러오기", "mf_wfm_contents_btn_ntrpInfoSearch"),
        ("기업상세정보 불러오기", "mf_wfm_contents_btn_autoInput"),
    ):
        try:
            loc = page.get_by_text(label, exact=False)
            if loc.count():
                loc.first.click(timeout=8000)
                page.wait_for_timeout(3500)
                _dismiss_alerts(page)
                auto_input = True
        except Exception:
            try:
                page.locator(f"#{eid}").click(timeout=5000)
                page.wait_for_timeout(3500)
                _dismiss_alerts(page)
                auto_input = True
            except Exception:
                pass
    fields = {
        "mf_wfm_contents_ibx_instEngNm": "Moksori Network Inc.",
        "mf_wfm_contents_ibx_hmpgAddr": "https://jema-ai.com",
        "mf_wfm_contents_ibx_majrProdMtitNm": "정책자금 신청서 자동 초안 생성 AI(RAG·근거연동·출력보류 게이트)",
        "mf_wfm_contents_ibx_empmNmprCnt": "1",
        "mf_wfm_contents_ibx_salesAmt": "0",
        "mf_wfm_contents_ibx_telno": "010-3677-0676",
    }
    filled: dict[str, Any] = {"auto_input_clicked": auto_input}
    for fid, val in fields.items():
        loc = page.locator(f"#{fid}")
        if not loc.count():
            filled[fid] = False
            continue
        try:
            cur = (loc.first.input_value() or "").strip()
        except Exception:
            cur = ""
        if cur and fid == "mf_wfm_contents_ibx_salesAmt":
            filled[fid] = "skipped_existing"
            continue
        if cur and fid in (
            "mf_wfm_contents_ibx_empmNmprCnt",
            "mf_wfm_contents_ibx_telno",
        ):
            filled[fid] = "skipped_existing"
            continue
        filled[fid] = _set_input(page, f"#{fid}", val)
    cal = page.locator('[id^="mf_wfm_contents_wq_uuid"][id$="_input"]').first
    if cal.count():
        try:
            if not (cal.input_value() or "").strip():
                cal.fill("2024-12-31")
                filled["uprng_date"] = True
        except Exception:
            filled["uprng_date"] = False
    cert = ""
    try:
        cert = page.locator("#mf_wfm_contents_btn_certi").inner_text(timeout=2000).strip()
    except Exception:
        pass
    return {"filled": filled, "cert_button": cert}


def _add_representative(page) -> dict[str, Any]:
    try:
        page.locator("#mf_wfm_contents_btn_addRprsvList").click(timeout=5000)
    except Exception:
        return {"opened": False}
    page.wait_for_timeout(1500)
    _dismiss_alerts(page)
    if not page.locator("#mf_wfm_contents_BMO0305P01_wframe_ibx_rprsvNm").count():
        return {"opened": False, "popup": False}
    _set_input(page, "#mf_wfm_contents_BMO0305P01_wframe_ibx_rprsvNm", "이기륜")
    try:
        page.locator("#mf_wfm_contents_BMO0305P01_wframe_rdo_vldYn_input_0").click(timeout=2000)
    except Exception:
        pass
    _set_input(page, "#mf_wfm_contents_BMO0305P01_wframe_cal_vldBgngYmd_input", "2021-01-05")
    _set_input(page, "#mf_wfm_contents_BMO0305P01_wframe_cal_vldEndYmd_input", "2099-12-31")
    try:
        page.locator("#mf_wfm_contents_BMO0305P01").get_by_role("link", name="적용").click(timeout=3000)
    except Exception:
        try:
            page.get_by_role("link", name="적용").click(timeout=2000)
        except Exception:
            return {"opened": True, "applied": False}
    page.wait_for_timeout(1200)
    _dismiss_alerts(page)
    rep = ""
    try:
        rep = page.locator("#mf_wfm_contents_grd_addRprsvList_body_tbody").inner_text(timeout=2000).strip()
    except Exception:
        pass
    return {"opened": True, "applied": True, "rep_grid": rep[:120]}


def _click_step_box(page, box_index: int) -> bool:
    try:
        page.locator(f"#mf_wfm_contents_generatorStepBox_{box_index}_stepBox").click(timeout=5000)
        page.wait_for_timeout(1500)
        _dismiss_alerts(page)
        return True
    except Exception:
        return False


def _click_next(page) -> bool:
    try:
        ok = page.evaluate(
            "() => { const el=document.querySelector('#mf_wfm_contents_btn_next'); if(!el)return false; el.click(); return true; }"
        )
        if ok:
            page.wait_for_timeout(2000)
            _dismiss_alerts(page)
            return True
    except Exception:
        pass
    try:
        page.get_by_role("link", name="다음").click(timeout=3000)
        page.wait_for_timeout(2000)
        _dismiss_alerts(page)
        return True
    except Exception:
        return False


def _fill_step3(page) -> dict[str, Any]:
    _click_step_box(page, 2)
    page.wait_for_timeout(2000)
    name = ""
    phone = ""
    for _ in range(3):
        try:
            name = page.locator("#mf_wfm_contents_tbx_mnpwNm").first.input_value()
        except Exception:
            name = ""
        try:
            phone = page.locator("#mf_wfm_contents_ibx_cpno").first.input_value()
        except Exception:
            phone = ""
        if name or phone:
            break
        page.wait_for_timeout(1000)
    saved = _click_save(page)
    return {"ok": bool(name or phone), "name": name, "phone": phone, "saved": saved}


def _goto_step4(page) -> dict[str, Any]:
    if page.locator("#mf_wfm_contents_ibx_tsksNm").count():
        return {"step": 4, "via": "already"}
    msgs: list[str] = []
    for i in range(4):
        _dismiss_alerts(page)
        if page.locator("#mf_wfm_contents_ibx_tsksNm").count():
            return {"step": 4, "via": "next", "attempts": i}
        if not _click_next(page):
            break
    if not page.locator("#mf_wfm_contents_ibx_tsksNm").count():
        _click_step_box(page, 3)
    has = page.locator("#mf_wfm_contents_ibx_tsksNm").count() > 0
    return {"step": 4 if has else 2, "via": "stepbox", "cert_block": msgs}


def _pick_combo_button(page, button_id: str, label: str) -> bool:
    try:
        page.locator(f"#{button_id}").click(timeout=3000)
    except Exception:
        return False
    page.wait_for_timeout(600)
    try:
        page.locator("tr").filter(has_text=label).first.click(timeout=3000)
        page.wait_for_timeout(400)
        return True
    except Exception:
        try:
            page.get_by_text(label, exact=True).first.click(timeout=2000)
            page.wait_for_timeout(400)
            return True
        except Exception:
            return False


def _pick_combo(page, suffix: str, label: str) -> bool:
    legacy_map = {
        "entHopeRgnClcd": "mf_wfm_contents_sbx_fndHopeRegin_button",
        "spcTechFldClcd": "mf_wfm_contents_sbx_spctTchnShpr_button",
        "ictDtlClcd": "mf_wfm_contents_sbx_spctCmncDtl_button",
    }
    if suffix in legacy_map:
        return _pick_combo_button(page, legacy_map[suffix], label)
    inp = page.locator(f'[id^="mf_wfm_contents_sbx_"][id$="_input"]').filter(has=page.locator(f"[id*='{suffix}']"))
    if not inp.count():
        inp = page.locator(f'[id*="mf_wfm_contents_sbx_{suffix}"][id$="_input"]')
    if not inp.count():
        return False
    btn_id = (inp.first.get_attribute("id") or "").replace("_input", "_button")
    return _pick_combo_button(page, btn_id, label)


def _fill_step4(page) -> dict[str, Any]:
    if not page.locator("#mf_wfm_contents_ibx_tsksNm").count():
        return {"ok": False, "reason": "step4 fields missing"}
    _set_input(page, "#mf_wfm_contents_ibx_tsksNm", TSKS_NM)
    _set_input(page, "#mf_wfm_contents_ibx_tsksCtnt", TSKS_CTNT)
    try:
        page.locator("#mf_wfm_contents_sbx_suptShpr_input_1").click(timeout=2000)
    except Exception:
        pass
    page.wait_for_timeout(400)
    combos = {
        "entHopeRgnClcd": _pick_combo(page, "entHopeRgnClcd", "경기"),
        "spcTechFldClcd": _pick_combo(page, "spcTechFldClcd", "정보통신"),
        "ictDtlClcd": _pick_combo(page, "ictDtlClcd", "소프트웨어"),
    }
    tsks = page.locator("#mf_wfm_contents_ibx_tsksNm").input_value()
    ctnt = page.locator("#mf_wfm_contents_ibx_tsksCtnt").input_value()
    saved = _click_save(page)
    if not saved:
        try:
            page.get_by_role("link", name="임시저장").click(timeout=5000)
            page.wait_for_timeout(2000)
            _dismiss_alerts(page)
            saved = True
        except Exception:
            saved = False
    return {
        "ok": bool(tsks and ctnt),
        "tsksNm": tsks[:80],
        "ctnt_len": len(ctnt),
        "combos": combos,
        "saved": saved,
    }


def _goto_step5(page) -> dict[str, Any]:
    if page.locator("#mf_wfm_contents_btn_addMnpwInfo").count():
        return {"step": 5, "via": "already"}
    for i in range(4):
        _dismiss_alerts(page)
        if page.locator("#mf_wfm_contents_btn_addMnpwInfo").count():
            return {"step": 5, "via": "next", "attempts": i}
        if not _click_next(page):
            break
    if not page.locator("#mf_wfm_contents_btn_addMnpwInfo").count():
        _click_step_box(page, 4)
    has = page.locator("#mf_wfm_contents_btn_addMnpwInfo").count() > 0
    return {"step": 5 if has else 4, "via": "stepbox"}


def _fill_step5(page) -> dict[str, Any]:
    _click_step_box(page, 4)
    page.wait_for_timeout(2000)
    grid = ""
    try:
        grid = page.locator("#mf_wfm_contents_grd_mnpwInfo_body_tbody").inner_text(timeout=3000).strip()
    except Exception:
        grid = ""
    added = False
    if not grid or "이기륜" not in grid:
        try:
            page.locator("#mf_wfm_contents_btn_addMnpwInfo").click(timeout=5000)
            page.wait_for_timeout(2000)
            sel = page.locator('[id^="mf_wfm_contents_BMO0502P01_wframe_grd_mbrIden_button_"][id$="_3"]').first
            if sel.count():
                sel.click(timeout=5000)
                page.wait_for_timeout(1500)
                added = True
            else:
                try:
                    page.locator("#mf_wfm_contents_BMO0502P01_wframe_ibx_mnpwNm").fill("이기륜", timeout=2000)
                    page.locator("#mf_wfm_contents_BMO0502P01_wframe_btn_search").click(timeout=2000)
                    page.wait_for_timeout(1500)
                    page.locator('[id^="mf_wfm_contents_BMO0502P01_wframe_grd_mbrIden_button_"]').first.click(timeout=3000)
                    page.wait_for_timeout(1500)
                    added = True
                except Exception:
                    added = False
            try:
                page.locator("#mf_wfm_contents_BMO0502P01_wframe_btn_close").click(timeout=2000)
            except Exception:
                pass
            page.wait_for_timeout(800)
        except Exception:
            added = False
        try:
            grid = page.locator("#mf_wfm_contents_grd_mnpwInfo_body_tbody").inner_text(timeout=3000).strip()
        except Exception:
            grid = ""
    saved = _click_save(page)
    return {
        "ok": bool(grid) and ("이기륜" in grid or added),
        "grid_snippet": grid[:120],
        "added": added,
        "saved": saved,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    ap.add_argument("--wait-for-login-sec", type=int, default=120)
    ap.add_argument("--skip-rep", action="store_true")
    ap.add_argument("--task-id", default="", help=f"과제번호 (기본: {TASK_ID} 또는 {TASK_ID_FALLBACKS[1]})")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("pip install playwright && playwright install chromium", file=sys.stderr)
        return 2

    task_id = (args.task_id or "").strip()

    log: dict[str, Any] = {
        "schema": "kstartup_opendata327_bmo0801_autofill_v1",
        "generated_at_utc": _utc(),
        "task_id": task_id or None,
        "boundary_ack": "no_final_submit — human 제출완료 only",
    }

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(args.cdp_url.strip())
        except Exception as exc:
            log["error"] = f"cdp_connect_failed: {exc}"
            OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(log, ensure_ascii=False, indent=2))
            return 1

        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = _pick_pms_page(context)
        if "pms.k-startup" not in (page.url or ""):
            page.goto(HISTORY_URL, wait_until="domcontentloaded", timeout=120_000)

        if not _wait_pms_logged_in(page, args.wait_for_login_sec, target_url=""):
            log["error"] = "login_timeout — log in on the CDP Chrome window, then re-run"
            log["page_url"] = page.url
            log["cdp_hint"] = (
                "일반 Chrome 로그인 ≠ CDP 프로필. "
                f"전용 프로필: %LOCALAPPDATA%\\kstartup-cdp-profile 또는 "
                "Run-KstartupOpenData327Bmo0801Autofill_v1.ps1 -UseDefaultProfile"
            )
            OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return 1

        if not task_id:
            task_id = _resolve_task_id(page, "") or ""
        if not task_id:
            log["error"] = f"no_task_in_history — expected one of {TASK_ID_FALLBACKS}"
            OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return 1
        log["task_id"] = task_id

        log["open"] = _open_task_edit(page, task_id)
        if not log["open"].get("ok"):
            OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(log, ensure_ascii=False, indent=2))
            return 1

        log["step2"] = _fill_step2(page)
        log["step2_saved"] = _click_save(page)

        cert = log["step2"].get("cert_button", "")
        if cert == "인증하기":
            log["warning"] = "corp_cert_still_pending — complete 인증하기 on STEP02, re-run"

        log["step3"] = _fill_step3(page)
        if not args.skip_rep:
            rep_btn = page.locator("#mf_wfm_contents_btn_addRprsvList")
            if rep_btn.count() and rep_btn.first.is_visible():
                log["rep"] = _add_representative(page)
            else:
                log["rep"] = {"opened": False, "reason": "not_on_this_form_variant"}

        log["nav"] = _goto_step4(page)
        if log["nav"].get("step") == 4:
            log["step4"] = _fill_step4(page)
        else:
            log["step4"] = {"ok": False, "reason": "could not reach step4"}

        log["nav5"] = _goto_step5(page)
        if log["nav5"].get("step") == 5:
            log["step5"] = _fill_step5(page)
        else:
            log["step5"] = {"ok": False, "reason": "could not reach step5"}

        try:
            page.screenshot(path=str(ROOT / "reports" / "kstartup_opendata327_bmo0801_autofill_latest.png"), full_page=False)
            log["screenshot"] = "reports/kstartup_opendata327_bmo0801_autofill_latest.png"
        except Exception:
            pass

        log["unlock"] = _unlock_page_for_user(page)

        step2_ok = any(
            v is True or v == "skipped_existing"
            for k, v in log.get("step2", {}).get("filled", {}).items()
            if k != "auto_input_clicked"
        )
        ok = bool(log.get("step5", {}).get("ok")) or bool(log.get("step4", {}).get("ok")) or (
            step2_ok and log.get("step2_saved") and log.get("step3", {}).get("saved")
        )
        OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(log, ensure_ascii=False, indent=2))
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
