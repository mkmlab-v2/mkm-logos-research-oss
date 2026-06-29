"""Dismiss overlays blocking user input; fill remaining STEP02 fields; save."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from kstartup_opendata327_bmo0801_autofill_v1 import (
    _click_save,
    _close_blocking_modals,
    _dismiss_alerts,
    _expand_corp_detail_fields,
    _pick_pms_page,
    _set_input,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "kstartup_opendata327_bmo0801_unlock_latest.json"
CDP = "http://127.0.0.1:9223"

FIELDS = {
    "mf_wfm_contents_ibx_instEngNm": "Moksori Network Inc.",
    "mf_wfm_contents_ibx_hmpgAddr": "https://jema-ai.com",
    "mf_wfm_contents_ibx_majrProdMtitNm": (
        "정책자금 신청서 자동 초안 생성 AI(RAG·근거연동·출력보류 게이트)"
    ),
}


def _unlock_page(page) -> dict:
    return page.evaluate(
        """() => {
          const out = {removed: []};
          for (const id of ['_modal', 'mf_wfm_contents_NBMO0421P01']) {
            const el = document.getElementById(id);
            if (el && getComputedStyle(el).display !== 'none') {
              el.style.display = 'none';
              el.style.pointerEvents = 'none';
              out.removed.push(id);
            }
          }
          document.querySelectorAll('.w2modal_popup').forEach((el) => {
            el.style.display = 'none';
            el.style.pointerEvents = 'none';
            out.removed.push('w2modal_popup');
          });
          document.body.style.pointerEvents = 'auto';
          document.body.style.overflow = 'auto';
          return out;
        }"""
    )


def main() -> int:
    log: dict = {"schema": "kstartup_opendata327_bmo0801_unlock_v1"}
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP, timeout=15000)
        except Exception as exc:
            log["error"] = f"cdp_connect_failed: {exc}"
            OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(log, ensure_ascii=False, indent=2))
            return 1

        page = _pick_pms_page(browser.contexts[0])
        log["url_before"] = page.url

        _close_blocking_modals(page)
        log["unlock"] = _unlock_page(page)
        _dismiss_alerts(page)
        _expand_corp_detail_fields(page)

        filled = {}
        for fid, val in FIELDS.items():
            cur = ""
            try:
                cur = (page.locator(f"#{fid}").first.input_value() or "").strip()
            except Exception:
                pass
            if fid == "mf_wfm_contents_ibx_instEngNm" and cur.replace(" ", "").lower() == val.replace(" ", "").lower():
                filled[fid] = "skipped_ok"
                continue
            if cur and fid not in (
                "mf_wfm_contents_ibx_hmpgAddr",
                "mf_wfm_contents_ibx_majrProdMtitNm",
            ):
                filled[fid] = "skipped_existing"
                continue
            ok = _set_input(page, f"#{fid}", val)
            filled[fid] = ok

        log["filled"] = filled
        log["saved"] = _click_save(page)
        _unlock_page(page)

        after = {}
        _expand_corp_detail_fields(page)
        for fid in FIELDS:
            try:
                after[fid] = page.locator(f"#{fid}").first.input_value()
            except Exception:
                after[fid] = ""
        log["values_after"] = after
        log["url_after"] = page.url
        log["user_can_click"] = True

        OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(log, ensure_ascii=False, indent=2))
        ok = log.get("saved") and any(after.get(k) for k in (
            "mf_wfm_contents_ibx_hmpgAddr",
            "mf_wfm_contents_ibx_majrProdMtitNm",
            "mf_wfm_contents_ibx_instEngNm",
        ))
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
