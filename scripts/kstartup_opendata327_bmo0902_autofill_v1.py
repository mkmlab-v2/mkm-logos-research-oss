"""K-Startup PMS BMO0902 — OpenData 327 과제 20460495 (Playwright CDP).

- 표준항목(과제명·과제내용·지원분야·지역·기술분야) — STEP04 동일 필드
- T1069 사업계획서 PDF / T1279 사업자등록증 업로드
- 빈 textarea 자동 채움(개요 SSOT 요약)
- 임시저장만 (제출완료 금지)

수동(로그인 Chrome): scripts/kstartup_opendata327_pms_standard_items_console_v1.js → F12 Console

Usage:
  py scripts/kstartup_opendata327_bmo0902_autofill_v1.py --cdp-url http://127.0.0.1:9222 --wait-for-login-sec 300
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kstartup_opendata327_bmo0801_autofill_v1 import (
    HISTORY_URL_LEGACY,
    HISTORY_URLS,
    TASK_ID as DEFAULT_TASK_ID,
    _dismiss_alerts,
    _fill_step4,
    _pick_pms_page,
    _unlock_page_for_user,
    _utc,
    _wait_pms_logged_in,
)

TASK_ID_FALLBACKS = (DEFAULT_TASK_ID, "20460558")
BMO1101_URL = HISTORY_URL_LEGACY

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "kstartup_opendata327_bmo0902_autofill_latest.json"

BMO0902_URL = "https://pms.k-startup.go.kr/biz/screen/BMO0902M0100"
OVERVIEW = ROOT / "docs/final/artifacts/ai_opendata_challenge_2026_327_business_plan_overview_v1.md"

PLAN_PDF_CANDIDATES = [
    ROOT / "reports/moksori_ai_opendata327_task1_business_plan_v1.pdf",
    ROOT / "reports/opendata_327_part_b_v1.pdf",
    ROOT / "reports/opendata_327_submission_bcd_merged_v1.pdf",
]

BRN_PDF_ENV = "MKM_OPENDATA327_BRN_PDF"


def _resolve_plan_pdf() -> Path | None:
    for p in PLAN_PDF_CANDIDATES:
        if p.is_file() and p.stat().st_size > 1000:
            return p
    return None


def _resolve_brn_pdf() -> Path | None:
    import os

    raw = (os.environ.get(BRN_PDF_ENV) or "").strip()
    if raw:
        p = Path(raw)
        if p.is_file():
            return p
    for guess in (
        ROOT / "reports/opendata_327_business_registration_v1.pdf",
        ROOT / "docs/final/artifacts/business_registration_6288601742.pdf",
    ):
        if guess.is_file():
            return guess
    return None


def _plain_section(md: str, heading: str, max_chars: int = 4000) -> str:
    pat = rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)"
    m = re.search(pat, md, re.MULTILINE | re.DOTALL)
    if not m:
        return ""
    text = m.group(1)
    text = re.sub(r"^> .*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > max_chars:
        text = text[: max_chars - 3] + "..."
    return text


def _validate_page(page, *, task_id: str, probe: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        body = page.inner_text("body", timeout=10_000)
    except Exception as exc:
        return {"ok": False, "reason": f"body_read_failed: {exc}"}
    if "BBMO0011" in body or "사업신청 정보를 찾을 수 없습니다" in body:
        return {"ok": False, "reason": "missing_task_context_bbmo0011"}
    if "모의공고" in body or "모의사업신청" in body:
        return {"ok": False, "reason": "mock_announcement_banner"}
    probe = probe or {}
    if probe.get("fileAddLinks", 0) > 0 or any("T1069" in r for r in probe.get("docRows", [])):
        return {"ok": True, "task_visible": task_id in body, "via": "attachment_grid"}
    if task_id in body:
        return {"ok": True, "task_visible": True}
    if "중진공" in body or "OpenData" in body or "정책자금" in body or "T1069" in body:
        return {"ok": True, "task_visible": False, "note": "task_id_not_in_body"}
    return {"ok": False, "reason": "unexpected_page_content"}


def _probe_page(page) -> dict[str, Any]:
    try:
        return page.evaluate(
            """() => {
              const body = document.body.innerText || '';
              const files = [...document.querySelectorAll('input[type=file]')].map(i => ({
                id: i.id, name: i.name, accept: i.accept || '',
                visible: !!(i.offsetParent || i.getClientRects().length)
              }));
              const tas = [...document.querySelectorAll('textarea')].filter(t => t.id && t.id.startsWith('mf_wfm'))
                .map(t => ({ id: t.id, len: (t.value || '').length, ro: t.readOnly }));
              const rows = [...document.querySelectorAll('tr')].map(r => (r.innerText || '').replace(/\\s+/g,' ').trim())
                .filter(t => /T\\d{4}|사업계획|사업자등록|제출서류|첨부/.test(t)).slice(0, 20);
              const adds = [...document.querySelectorAll('a,button')].filter(x => (x.textContent||'').includes('파일추가')).length;
              return {
                url: location.href,
                title: document.title,
                has첨부: body.includes('제출서류') || body.includes('첨부'),
                has표준: body.includes('표준항목'),
                fileInputs: files,
                textareas: tas,
                docRows: rows,
                fileAddLinks: adds
              };
            }"""
        )
    except Exception as exc:
        return {"error": str(exc)}


def _resolve_task_id(page, preferred: str) -> str | None:
    if preferred:
        return preferred
    page.goto(BMO1101_URL, wait_until="domcontentloaded", timeout=120_000)
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


def _click_bmo1101_edit(page, task_id: str) -> bool:
    edit_id = page.evaluate(
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
    if edit_id:
        page.locator(f"#{edit_id}").click(timeout=10_000)
        page.wait_for_timeout(5000)
        _dismiss_alerts(page)
        return True
    row = page.locator("tr").filter(has_text=task_id)
    if row.count():
        edit = row.first.get_by_role("link", name="수정하기")
        if edit.count():
            edit.first.click(timeout=10_000)
            page.wait_for_timeout(5000)
            _dismiss_alerts(page)
            return True
    return False


def _goto_bmo0902(page) -> None:
    page.goto(BMO0902_URL, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(4000)
    _dismiss_alerts(page)


def _open_task_if_needed(page, task_id: str) -> dict[str, Any]:
    probe = _probe_page(page)
    url = page.url or ""
    if "BMO0902" in url and probe.get("fileAddLinks", 0) > 0:
        return {"ok": True, "via": "already_on_form", "url": url, "task_id": task_id}

    page.goto(BMO1101_URL, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(3500)
    _dismiss_alerts(page)
    if task_id not in page.inner_text("body", timeout=10_000):
        return {"ok": False, "reason": f"task {task_id} not in BMO1101 history"}
    if not _click_bmo1101_edit(page, task_id):
        return {"ok": False, "reason": f"수정하기_missing for {task_id}"}
    _goto_bmo0902(page)
    probe = _probe_page(page)
    if probe.get("fileAddLinks", 0) > 0:
        return {
            "ok": True,
            "via": "bmo1101_edit_then_bmo0902",
            "task_id": task_id,
            "url": page.url,
        }
    return {"ok": False, "reason": "bmo0902_grid_empty_after_edit", "task_id": task_id}


def _upload_in_row(page, row_hint: str, file_path: Path) -> dict[str, Any]:
    if not file_path.is_file():
        return {"ok": False, "reason": "file_missing", "path": str(file_path)}
    row = page.locator("tr").filter(has_text=row_hint)
    if not row.count():
        row = page.locator("div").filter(has_text=row_hint)
    if not row.count():
        return {"ok": False, "reason": "row_not_found", "hint": row_hint}
    target = row.first
    add = target.get_by_role("link", name="파일추가")
    if not add.count():
        add = target.get_by_text("파일추가")
    try:
        with page.expect_file_chooser(timeout=12_000) as fc_info:
            add.first.click(timeout=6000)
        fc_info.value.set_files(str(file_path.resolve()))
        page.wait_for_timeout(3500)
        _dismiss_alerts(page)
        return {"ok": True, "hint": row_hint, "file": str(file_path)}
    except Exception as exc:
        fi = target.locator('input[type="file"]')
        if fi.count():
            try:
                fi.first.set_input_files(str(file_path.resolve()))
                page.wait_for_timeout(3500)
                _dismiss_alerts(page)
                return {"ok": True, "hint": row_hint, "via": "hidden_input", "file": str(file_path)}
            except Exception as exc2:
                return {"ok": False, "hint": row_hint, "error": f"{exc}; {exc2}"}
        return {"ok": False, "hint": row_hint, "error": str(exc)}


def _upload_any_file_input(page, file_path: Path) -> dict[str, Any]:
    loc = page.locator('input[type="file"]')
    n = loc.count()
    if not n:
        return {"ok": False, "reason": "no_file_input"}
    for i in range(n):
        try:
            loc.nth(i).set_input_files(str(file_path.resolve()))
            page.wait_for_timeout(2500)
            return {"ok": True, "index": i, "file": str(file_path)}
        except Exception:
            continue
    return {"ok": False, "reason": "all_file_inputs_failed"}


def _fill_textareas_from_ssot(page) -> dict[str, Any]:
    if not OVERVIEW.is_file():
        return {"skipped": True, "reason": "overview_missing"}
    md = OVERVIEW.read_text(encoding="utf-8")
    chunks = {
        "개발": _plain_section(md, "1. 과제 해결방안 (개발계획)", 3500),
        "혁신": _plain_section(md, "2. 혁신성", 2500),
        "시장": _plain_section(md, "3. 가치창출 및 시장성", 2500),
    }
    filled: list[str] = []
    for ta in page.locator("textarea").all():
        try:
            tid = ta.get_attribute("id") or ""
            if ta.get_attribute("readonly"):
                continue
            cur = ta.input_value()
            if cur and len(cur.strip()) > 20:
                continue
            label_hint = ""
            try:
                label_hint = page.evaluate(
                    """(id) => {
                      const el = document.getElementById(id);
                      if (!el) return '';
                      let p = el.parentElement;
                      for (let i = 0; i < 8 && p; i++, p = p.parentElement) {
                        const t = (p.innerText || '').slice(0, 200);
                        if (t.length > 5) return t;
                      }
                      return '';
                    }""",
                    tid,
                )
            except Exception:
                pass
            pick = chunks.get("개발", "")
            if "혁신" in label_hint or "AI" in label_hint:
                pick = chunks.get("혁신") or pick
            elif "시장" in label_hint:
                pick = chunks.get("시장") or pick
            if not pick:
                continue
            ta.fill(pick[:8000])
            filled.append(tid)
        except Exception:
            continue
    return {"filled_ids": filled, "count": len(filled)}


def _temp_save(page) -> bool:
    _unlock_page_for_user(page)
    _dismiss_alerts(page)
    for name in ("임시저장", "저장"):
        try:
            page.get_by_role("link", name=name).click(timeout=5000)
            page.wait_for_timeout(2500)
            _dismiss_alerts(page)
            return True
        except Exception:
            continue
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    ap.add_argument("--wait-for-login-sec", type=int, default=300)
    ap.add_argument("--skip-upload", action="store_true")
    ap.add_argument("--task-id", default="", help=f"과제번호 (기본: {DEFAULT_TASK_ID} 또는 {TASK_ID_FALLBACKS[1]})")
    ap.add_argument("--brn-pdf", default="", help="사업자등록증 PDF 경로")
    ap.add_argument("--plan-pdf", default="", help="사업계획서 PDF 경로")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("pip install playwright && playwright install chromium", file=sys.stderr)
        return 2

    plan = Path(args.plan_pdf) if args.plan_pdf else _resolve_plan_pdf()
    brn = Path(args.brn_pdf) if args.brn_pdf else _resolve_brn_pdf()

    task_id = (args.task_id or "").strip()

    log: dict[str, Any] = {
        "schema": "kstartup_opendata327_bmo0902_autofill_v1",
        "generated_at_utc": _utc(),
        "task_id": task_id or None,
        "target_url": BMO0902_URL,
        "plan_pdf": str(plan) if plan else None,
        "brn_pdf": str(brn) if brn else None,
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

        if not _wait_pms_logged_in(page, args.wait_for_login_sec, target_url=BMO1101_URL):
            log["error"] = (
                "login_timeout — CDP Chrome 창에서 K-Startup 로그인 후 재실행 "
                "(일반 Chrome만 로그인된 경우: Run-KstartupOpenData327Bmo0902Autofill_v1.ps1 -UseDefaultProfile)"
            )
            log["page_url"] = page.url
            OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return 1

        if not task_id:
            task_id = _resolve_task_id(page, "") or ""
        if not task_id:
            log["error"] = f"no_task_in_history — expected one of {TASK_ID_FALLBACKS}"
            OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return 1
        log["task_id"] = task_id

        log["nav"] = _open_task_if_needed(page, task_id)
        if not log["nav"].get("ok"):
            OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(log, ensure_ascii=False, indent=2))
            return 1

        if "BMO0902" not in (page.url or ""):
            _goto_bmo0902(page)

        log["probe"] = _probe_page(page)
        log["validate"] = _validate_page(page, task_id=task_id, probe=log["probe"])

        if page.locator("#mf_wfm_contents_ibx_tsksNm").count():
            for tab_label in ("표준항목", "STEP04", "표준 항목"):
                try:
                    tab = page.get_by_text(tab_label, exact=False)
                    if tab.count():
                        tab.first.click(timeout=2000)
                        page.wait_for_timeout(800)
                        break
                except Exception:
                    continue
            try:
                log["standard_items"] = _fill_step4(page)
            except Exception as exc:
                log["standard_items"] = {"ok": False, "reason": "fill_step4_exception", "error": str(exc)}
        else:
            log["standard_items"] = {"ok": False, "reason": "ibx_tsksNm_not_on_page"}

        if not log["validate"].get("ok"):
            OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(log, ensure_ascii=False, indent=2))
            return 1

        log["textareas"] = _fill_textareas_from_ssot(page)
        log["unlock"] = _unlock_page_for_user(page)

        if not args.skip_upload:
            uploads: dict[str, Any] = {}
            if plan:
                for hint in ("T1069", "사업계획서"):
                    uploads[hint] = _upload_in_row(page, hint, plan)
                    if uploads[hint].get("ok"):
                        break
                if not any(uploads.get(h, {}).get("ok") for h in uploads):
                    uploads["fallback_first_file_input"] = _upload_any_file_input(page, plan)
            else:
                uploads["plan"] = {"ok": False, "reason": "no_plan_pdf_in_repo"}
            if brn:
                for hint in ("T0589", "T1279", "사업자등록"):
                    uploads[f"brn_{hint}"] = _upload_in_row(page, hint, brn)
                    if uploads[f"brn_{hint}"].get("ok"):
                        break
            else:
                uploads["brn"] = {
                    "ok": False,
                    "reason": "brn_pdf_not_set",
                    "hint_env": BRN_PDF_ENV,
                }
            log["uploads"] = uploads

        log["temp_save"] = _temp_save(page)

        try:
            shot = ROOT / "reports" / "kstartup_opendata327_bmo0902_autofill_latest.png"
            page.screenshot(path=str(shot), full_page=False)
            log["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
        except Exception:
            pass

        upload_ok = False
        if log.get("uploads"):
            upload_ok = any(
                v.get("ok") for v in log["uploads"].values() if isinstance(v, dict)
            )
        std_ok = log.get("standard_items", {}).get("ok")
        ok = std_ok or log.get("temp_save") or upload_ok or (log.get("textareas", {}).get("count", 0) > 0)
        log["exit_ok"] = ok
        OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(log, ensure_ascii=False, indent=2))
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
