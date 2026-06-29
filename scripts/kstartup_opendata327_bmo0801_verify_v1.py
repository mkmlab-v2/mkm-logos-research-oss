"""BMO0801 read-only verify via Playwright CDP (OpenData 327)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kstartup_opendata327_bmo0801_autofill_v1 import (
    FORM_URL,
    HISTORY_URL_LEGACY,
    _dismiss_alerts,
    _expand_corp_detail_fields,
    _open_task_edit,
    _pick_pms_page,
    _wait_pms_logged_in,
)

BMO1101_URL = HISTORY_URL_LEGACY

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "kstartup_opendata327_bmo0801_verify_latest.json"

EXPECTED = {
    "mf_wfm_contents_ibx_instEngNm": "Moksori Network Inc.",
    "mf_wfm_contents_ibx_hmpgAddr": "https://jema-ai.com",
    "mf_wfm_contents_ibx_majrProdMtitNm": "정책자금 신청서 자동 초안 생성 AI(RAG·근거연동·출력보류 게이트)",
    "mf_wfm_contents_ibx_empmNmprCnt": "1",
    "mf_wfm_contents_ibx_telno": "010-3677-0676",
}
PRESENT_ONLY = frozenset({"mf_wfm_contents_ibx_salesAmt"})


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _open_task(page, task_id: str) -> dict[str, Any]:
    page.goto(HISTORY_URL_LEGACY, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(4000)
    _dismiss_alerts(page)
    if task_id not in page.inner_text("body", timeout=15_000):
        return {"ok": False, "reason": f"task {task_id} not in history"}
    edit_id = page.evaluate(
        """(taskId) => {
          for (const el of document.querySelectorAll('[id$="_btn_edit"]')) {
            let p = el.parentElement;
            for (let i = 0; i < 12 && p; i++, p = p.parentElement) {
              const t = (p.innerText || '').replace(/\\s+/g, ' ').trim();
              if (!t.includes(taskId)) continue;
              if (!/과제번호\\s*:\\s*/.test(t)) continue;
              const idx = t.indexOf(taskId);
              const slice = t.slice(Math.max(0, idx - 20), idx + taskId.length + 40);
              if (!slice.includes('과제번호') || slice.includes(taskId + ' ') === false) continue;
              const others = (t.match(/20\\d{6}/g) || []).filter(x => x !== taskId);
              const before = t.slice(0, idx);
              if (others.some(o => before.includes(o))) continue;
              return el.id;
            }
          }
          return null;
        }""",
        task_id,
    )
    if not edit_id:
        return {"ok": False, "reason": "edit_button_not_found"}
    page.locator(f"#{edit_id}").click(timeout=10_000)
    page.wait_for_timeout(5000)
    _dismiss_alerts(page)
    if "BMO0801" not in (page.url or ""):
        page.goto(FORM_URL, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(4000)
        _dismiss_alerts(page)
    return {"ok": True, "url": page.url, "edit_id": edit_id}


def _read_field(page, fid: str) -> dict[str, Any]:
    loc = page.locator(f"#{fid}")
    if not loc.count():
        return {"present": False, "value": "", "visible": False}
    try:
        visible = loc.first.is_visible()
    except Exception:
        visible = False
    try:
        val = loc.first.input_value()
    except Exception:
        val = ""
    try:
        ro = bool(loc.first.get_attribute("readonly"))
    except Exception:
        ro = False
    return {"present": True, "value": (val or "").strip(), "visible": visible, "readonly": ro}


def _probe_page(page) -> dict[str, Any]:
    try:
        body = page.inner_text("body", timeout=15_000)
    except Exception as exc:
        return {"error": str(exc)}
    flags = {
        "기업정보": "기업정보" in body,
        "공동인증서": "공동인증서" in body,
        "cert_complete": "인증완료" in body or "인증 완료" in body,
        "bbmo0011": "BBMO0011" in body or "사업신청 정보를 찾을 수 없습니다" in body,
        "임시저장": "임시저장" in body,
        "다음": "다음" in body,
    }
    cert_text = ""
    try:
        cert_text = page.locator("#mf_wfm_contents_btn_certi").inner_text(timeout=2000).strip()
    except Exception:
        pass
    rep_grid = ""
    try:
        rep_grid = page.locator("#mf_wfm_contents_grd_addRprsvList_body_tbody").inner_text(timeout=2000).strip()
    except Exception:
        pass
    step_boxes = page.evaluate(
        """() => [...document.querySelectorAll('[id*="generatorStepBox"][id$="_stepBox"]')]
          .map(el => ({id: el.id, text: (el.innerText||'').replace(/\\s+/g,' ').trim().slice(0,80)}))"""
    )
    return {
        "url": page.url,
        "title": page.title(),
        "flags": flags,
        "cert_button": cert_text,
        "rep_grid_preview": rep_grid[:200],
        "step_boxes": step_boxes[:8],
        "body_preview": body[:1200].replace("\n", " | "),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cdp-url", default="http://127.0.0.1:9223")
    ap.add_argument("--task-id", default="20460558")
    ap.add_argument("--wait-for-login-sec", type=int, default=30)
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("pip install playwright", file=sys.stderr)
        return 2

    log: dict[str, Any] = {
        "schema": "kstartup_opendata327_bmo0801_verify_v1",
        "generated_at_utc": _utc(),
        "task_id": args.task_id,
        "target_url": FORM_URL,
        "mode": "read_only_verify",
    }

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(args.cdp_url.strip())
        page = _pick_pms_page(browser.contexts[0])
        try:
            body0 = page.inner_text("body", timeout=5000)
        except Exception:
            body0 = ""
        if "404" in body0 or "webLGIN" in (page.url or ""):
            page.goto(BMO1101_URL, wait_until="domcontentloaded", timeout=120_000)
            page.wait_for_timeout(2000)
        if not _wait_pms_logged_in(page, args.wait_for_login_sec, target_url=""):
            log["error"] = "login_timeout"
            log["page_url"] = page.url
            OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(log, ensure_ascii=False, indent=2))
            return 1

        log["nav"] = _open_task_edit(page, args.task_id)
        if not log["nav"].get("ok"):
            log["nav"] = _open_task(page, args.task_id)
        if not log["nav"].get("ok"):
            OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(log, ensure_ascii=False, indent=2))
            return 1

        log["probe"] = _probe_page(page)
        _expand_corp_detail_fields(page)
        fields: dict[str, Any] = {}
        mismatches: list[str] = []
        for fid, expected in EXPECTED.items():
            row = _read_field(page, fid)
            row["expected"] = expected
            if fid == "mf_wfm_contents_ibx_instEngNm" and row.get("value"):
                norm = row["value"].replace(" ", "").replace(".", "").lower()
                exp = expected.replace(" ", "").replace(".", "").lower()
                row["match"] = norm == exp
            else:
                row["match"] = row.get("value") == expected if row.get("present") else False
            if row.get("present") and not row["match"] and row.get("value"):
                mismatches.append(fid)
            elif row.get("present") and not row.get("value"):
                mismatches.append(f"{fid}:empty")
            elif not row.get("present"):
                mismatches.append(f"{fid}:missing")
            fields[fid] = row
        for fid in PRESENT_ONLY:
            row = _read_field(page, fid)
            row["expected"] = "any_non_empty"
            row["match"] = bool(row.get("value")) if row.get("present") else False
            if row.get("present") and not row.get("value"):
                mismatches.append(f"{fid}:empty")
            elif not row.get("present"):
                mismatches.append(f"{fid}:missing")
            fields[fid] = row
        log["fields"] = fields
        log["mismatches"] = mismatches

        rep_ok = "이기륜" in (log["probe"].get("rep_grid_preview") or "")
        log["rep_present"] = rep_ok
        cert = log["probe"].get("cert_button") or ""
        log["cert_state"] = cert
        log["cert_ok"] = any(k in cert for k in ("인증완료", "완료", "재인증"))

        blockers: list[str] = []
        if log["probe"].get("flags", {}).get("bbmo0011"):
            blockers.append("bbmo0011_missing_context")
        if log["probe"].get("flags", {}).get("공동인증서") and not log["cert_ok"]:
            blockers.append("joint_cert_required")
        log["blockers"] = blockers

        filled_count = sum(1 for f in fields.values() if f.get("value"))
        match_count = sum(1 for f in fields.values() if f.get("match"))
        log["summary"] = {
            "fields_present": sum(1 for f in fields.values() if f.get("present")),
            "fields_filled": filled_count,
            "fields_match_expected": match_count,
            "verify_ok": not blockers and filled_count >= 4 and (match_count >= 3 or filled_count >= 5),
        }
        log["exit_ok"] = log["summary"]["verify_ok"]

        try:
            shot = ROOT / "reports" / "kstartup_opendata327_bmo0801_verify_latest.png"
            page.screenshot(path=str(shot), full_page=False)
            log["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
        except Exception:
            pass

        OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(log, ensure_ascii=False, indent=2))
        return 0 if log["exit_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
