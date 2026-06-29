"""K-Startup PMS — 2026 창업패키지(AI 인재 실증형) autofill (Playwright CDP).

- 사업신청내역(BMO1101)에서 프로그램 행 찾기 → 수정하기
- 또는 --pms-url 로 직접 진입
- paste_ready 텍스트 → 빈 textarea 순차/라벨 매칭 채움
- 임시저장만 (제출완료 금지)

Usage:
  py scripts/kstartup_startup_package_ai_autofill_v1.py --cdp-url http://127.0.0.1:9222
  py scripts/kstartup_startup_package_ai_autofill_v1.py --probe-only --pms-url \"https://pms.k-startup.go.kr/...\"
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from kstartup_opendata327_bmo0801_autofill_v1 import (
    _add_representative,
    _dismiss_alerts,
    _fill_step4,
    _goto_step4,
    _pick_combo,
    _pick_pms_page,
    _set_input,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "docs/final/artifacts/kstartup_startup_package_ai_pms_config_v1.json"
PASTE_DIR = ROOT / "reports/kstartup_startup_package_ai_paste_ready"
OUT = ROOT / "reports/kstartup_startup_package_ai_autofill_latest.json"

PLAN_PDF_ENV = "MKM_STARTUP_PKG_PLAN_PDF"
AI_TALENT_PDF_ENV = "MKM_STARTUP_PKG_AI_TALENT_PDF"

LABEL_HINTS: list[tuple[str, str]] = [
    ("plan_01_summary_paste.txt", "개요|요약|사업개요|Executive"),
    ("plan_02_market_problem_paste.txt", "시장|문제|필요|pain"),
    ("plan_03_tech_roadmap_paste.txt", "기술|개발|추진|실현|방안"),
    ("plan_04_growth_funding_paste.txt", "성장|자금|사업화|전략"),
    ("plan_05_team_paste.txt", "팀|역량|대표|인력"),
    ("plan_06_ai_talent_2p_paste.txt", "AI 인재|인재 활용|채용|매칭"),
]


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_config() -> dict[str, Any]:
    if CONFIG.is_file():
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    return {}


def _paste_body(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    raw = re.sub(r"^\[창업패키지[^\]]*\]\s*\n+", "", raw)
    raw = re.sub(r"^#+ .+\n+", "", raw, count=1)
    return raw.strip()


def _load_paste_chunks() -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    for fname, hint in LABEL_HINTS:
        p = PASTE_DIR / fname
        if not p.is_file():
            continue
        chunks.append({"file": fname, "hint": hint, "text": _paste_body(p)})
    return chunks


def _probe_page(page) -> dict[str, Any]:
    try:
        return page.evaluate(
            """() => {
              const body = document.body.innerText || '';
              const inputs = [...document.querySelectorAll('input[id^="mf_wfm"], textarea[id^="mf_wfm"]')]
                .slice(0, 80).map(el => ({
                  tag: el.tagName, id: el.id, type: el.type || '',
                  ro: el.readOnly, len: (el.value || '').length
                }));
              const tas = [...document.querySelectorAll('textarea')].filter(t => t.id)
                .map(t => ({ id: t.id, len: (t.value || '').length, ro: t.readOnly }));
              const files = [...document.querySelectorAll('input[type=file]')].map(i => ({
                id: i.id, accept: i.accept || ''
              }));
              return {
                url: location.href, title: document.title,
                body_snippet: body.slice(0, 500),
                inputs, textareas: tas, fileInputs: files
              };
            }"""
        )
    except Exception as exc:
        return {"error": str(exc)}


DOYAK_PMS_ENTRY = (
    "https://www.k-startup.go.kr/web/contents/webPMSBizUnvs.do"
    "?returnUrl=/screen/BMO0101M01?pbancId=0661001"
)


def _wire_dialog_accept(page) -> None:
    try:
        page.on("dialog", lambda d: d.accept())
    except Exception:
        pass


def _wait_for_pms_page(context, wait_sec: int) -> Any | None:
    import time

    deadline = time.time() + wait_sec
    while time.time() < deadline:
        for pg in context.pages:
            u = pg.url or ""
            if "pms.k-startup.go.kr" in u and "webLGIN" not in u:
                return pg
        time.sleep(1.5)
    return None


def _is_pms_host_url(url: str) -> bool:
    """True only for pms.k-startup.go.kr host — not webLGIN endPoint query params."""
    try:
        return urlparse(url or "").netloc == "pms.k-startup.go.kr"
    except Exception:
        return False


def _attach_pms_page(context, prefer_url: str = "") -> Any | None:
    """Prefer an open PMS tab (CDP may default to unrelated tabs e.g. NVIDIA benefits)."""
    prefer_path = prefer_url.split("?")[0] if prefer_url else ""
    fallback = None
    for pg in context.pages:
        u = pg.url or ""
        if not _is_pms_host_url(u):
            continue
        if prefer_path and prefer_path in u:
            return pg
        fallback = pg
    return fallback


def _pick_work_page(context) -> Any:
    pms_pg = _attach_pms_page(context)
    if pms_pg is not None:
        return pms_pg
    order = (
        lambda u: (
            0 if "pms.k-startup.go.kr" in u else 1 if "pbancSn=177670" in u else 2 if "webLGIN" in u else 9
        )
    )
    pages = sorted(context.pages, key=lambda p: order(p.url or ""))
    return pages[0] if pages else _pick_pms_page(context)


def _session_ready(page) -> bool:
    try:
        return bool(
            page.evaluate(
                """() => {
              const t = document.body.innerText || '';
              if (t.includes('로그아웃') || t.includes('마이페이지')) return true;
              const links = [...document.querySelectorAll('a')].map(a => (a.textContent||'').trim());
              if (links.includes('로그아웃')) return true;
              if (links.includes('마이페이지') && !links.includes('회원가입')) return true;
              if (location.href.includes('pms.k-startup') && t.includes('사업신청')) return true;
              return false;
            }"""
            )
        )
    except Exception:
        return False


def _wait_logged_in(page, wait_sec: int) -> bool:
    import time

    deadline = time.time() + wait_sec
    while time.time() < deadline:
        url = page.url or ""
        if "webLGIN" in url:
            page.wait_for_timeout(1500)
            continue
        if _session_ready(page):
            return True
        if "pms.k-startup.go.kr" in url and "tokenInfoRelay" not in url:
            try:
                if "mf_wfm" in (page.content() or ""):
                    return True
            except Exception:
                pass
        page.wait_for_timeout(1200)
    return False


def _open_from_portal(page, portal_url: str, track: str = "도약", context: Any = None) -> dict[str, Any]:
    popup_err = ""
    if "pbancSn=177670" not in (page.url or ""):
        page.goto(portal_url, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(3500)
    _dismiss_alerts(page)
    _wire_dialog_accept(page)
    js_fn = "fn_177670_2_open" if track == "도약" else "fn_177670_1_open"
    ctx = context or page.context
    try:
        with ctx.expect_page(timeout=25_000) as pop:
            page.evaluate(f"() => {{ if (typeof {js_fn} === 'function') {js_fn}(); }}")
        new = pop.value
        _wire_dialog_accept(new)
        new.wait_for_load_state("domcontentloaded", timeout=90_000)
        new.wait_for_timeout(2500)
        _dismiss_alerts(new)
        out: dict[str, Any] = {
            "ok": True,
            "via": js_fn,
            "url": new.url,
            "popup": True,
        }
        if "webLGIN" in new.url:
            out["pms_sso_pending"] = True
            out["note"] = "통합로그인(Any-ID) 탭에서 간편인증 후 스크립트가 PMS 대기"
        return out
    except Exception as exc_popup:
        popup_err = str(exc_popup)
        try:
            btn = page.get_by_role("link", name="창업도약패키지" if track == "도약" else "초기창업패키지")
            if btn.count():
                with ctx.expect_page(timeout=25_000) as pop:
                    btn.first.click(timeout=10_000)
                new = pop.value
                _wire_dialog_accept(new)
                new.wait_for_load_state("domcontentloaded", timeout=90_000)
                return {"ok": True, "via": "track_button", "url": new.url, "popup": True}
        except Exception as exc2:
            popup_err = f"{popup_err}; {exc2}"
    apply_names = (
        "창업도약패키지",
        "초기창업패키지",
        "사업신청관리",
        "사업신청",
        "신청하기",
    )
    if track == "초기":
        apply_names = ("초기창업패키지",) + apply_names
    else:
        apply_names = ("창업도약패키지",) + apply_names
    for name in apply_names:
        for loc in (
            page.get_by_role("link", name=name),
            page.get_by_role("button", name=name),
            page.get_by_text(name, exact=False),
        ):
            try:
                if loc.count():
                    with page.expect_popup(timeout=15_000) as pop:
                        loc.first.click(timeout=8000)
                    new = pop.value
                    new.wait_for_load_state("domcontentloaded", timeout=60_000)
                    page.wait_for_timeout(3000)
                    _dismiss_alerts(new)
                    return {"ok": True, "via": name, "url": new.url, "popup": True}
            except Exception:
                try:
                    if loc.count():
                        loc.first.click(timeout=8000)
                        page.wait_for_timeout(5000)
                        _dismiss_alerts(page)
                        if "pms.k-startup" in page.url or "사업신청" in page.inner_text("body", timeout=5000):
                            return {"ok": True, "via": name, "url": page.url}
                except Exception:
                    continue
    return {
        "ok": False,
        "reason": "portal_apply_button_not_found",
        "url": page.url,
        "popup_err": popup_err,
    }


def _open_from_history(page, history_url: str, keywords: list[str]) -> dict[str, Any]:
    page.goto(history_url, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(3500)
    _dismiss_alerts(page)
    body = page.inner_text("body", timeout=15_000)
    row = None
    for kw in keywords:
        loc = page.locator("tr").filter(has_text=kw)
        if loc.count():
            row = loc.first
            break
    if row is None:
        return {"ok": False, "reason": "history_row_not_found", "keywords": keywords}
    for link_name in ("수정하기", "신청하기", "작성하기", "계속하기"):
        link = row.get_by_role("link", name=link_name)
        if link.count():
            link.first.click(timeout=10_000)
            page.wait_for_timeout(4000)
            _dismiss_alerts(page)
            return {"ok": True, "via": link_name, "url": page.url}
    return {"ok": False, "reason": "no_edit_link_on_row"}


def _textarea_label(page, tid: str) -> str:
    try:
        return page.evaluate(
            """(id) => {
              const el = document.getElementById(id);
              if (!el) return '';
              let p = el.parentElement;
              for (let i = 0; i < 10 && p; i++, p = p.parentElement) {
                const t = (p.innerText || '').slice(0, 300);
                if (t.length > 8) return t;
              }
              return '';
            }""",
            tid,
        )
    except Exception:
        return ""


def _fill_textareas(page, chunks: list[dict[str, str]]) -> dict[str, Any]:
    filled: list[str] = []
    seq_idx = 0
    for ta in page.locator("textarea").all():
        try:
            tid = ta.get_attribute("id") or ""
            if not tid or ta.get_attribute("readonly"):
                continue
            cur = (ta.input_value() or "").strip()
            if len(cur) > 30:
                continue
            label = _textarea_label(page, tid)
            pick = ""
            for ch in chunks:
                if re.search(ch["hint"], label, re.IGNORECASE):
                    pick = ch["text"]
                    break
            if not pick and seq_idx < len(chunks):
                pick = chunks[seq_idx]["text"]
                seq_idx += 1
            if not pick:
                continue
            ta.fill(pick[:12000])
            filled.append(tid)
        except Exception:
            continue
    return {"filled_ids": filled, "count": len(filled)}


def _upload_first_file_input(page, file_path: Path) -> dict[str, Any]:
    fi = page.locator('input[type="file"]')
    if not fi.count():
        return {"ok": False, "reason": "no_file_input"}
    try:
        fi.first.set_input_files(str(file_path.resolve()))
        page.wait_for_timeout(2500)
        return {"ok": True, "via": "first_file_input", "file": str(file_path)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _upload_file_row(page, hint: str, file_path: Path) -> dict[str, Any]:
    if not file_path.is_file():
        return {"ok": False, "reason": "file_missing", "path": str(file_path)}
    row = page.locator("tr").filter(has_text=hint)
    if not row.count():
        return {"ok": False, "reason": "row_not_found", "hint": hint}
    add = row.first.get_by_role("link", name="파일추가")
    if not add.count():
        add = row.first.get_by_text("파일추가")
    try:
        with page.expect_file_chooser(timeout=12_000) as fc_info:
            add.first.click(timeout=6000)
        fc_info.value.set_files(str(file_path.resolve()))
        page.wait_for_timeout(3000)
        _dismiss_alerts(page)
        return {"ok": True, "hint": hint, "file": str(file_path)}
    except Exception as exc:
        fi = row.first.locator('input[type="file"]')
        if fi.count():
            try:
                fi.first.set_input_files(str(file_path.resolve()))
                page.wait_for_timeout(2500)
                return {"ok": True, "hint": hint, "via": "hidden_input", "file": str(file_path)}
            except Exception as exc2:
                return {"ok": False, "error": f"{exc}; {exc2}"}
        return {"ok": False, "error": str(exc)}


def _accept_terms_and_advance(page) -> dict[str, Any]:
    """BMO0701 STEP01 약관동의 → 다음 → 신청서작성(기창업자)."""
    out: dict[str, Any] = {"steps": []}
    body = ""
    try:
        body = page.inner_text("body", timeout=5000)
    except Exception:
        pass
    if "약관에 동의" not in body and "STEP01" not in body:
        return {"ok": True, "skipped": True, "reason": "not_terms_step"}

    try:
        page.evaluate(
            """() => {
              const all = document.getElementById('mf_wfm_contents_agreeAll_input_0');
              if (all) { all.checked = true; all.click(); }
              document.querySelectorAll('input[type=radio][id*="agreChcAbleYn_input_0"]')
                .forEach(r => { r.checked = true; r.click(); });
            }"""
        )
        page.wait_for_timeout(800)
        out["steps"].append("terms_checked")
    except Exception as exc:
        out["terms_error"] = str(exc)

    for sel in ("#mf_wfm_contents_btn_next",):
        try:
            loc = page.locator(sel)
            if loc.count():
                loc.first.click(timeout=10_000)
                page.wait_for_timeout(4000)
                _dismiss_alerts(page)
                out["steps"].append("clicked_next")
                break
        except Exception as exc:
            out["next_error"] = str(exc)
            try:
                page.evaluate(
                    "() => { const n=document.getElementById('mf_wfm_contents_btn_next'); if(n)n.click(); }"
                )
                page.wait_for_timeout(4000)
                _dismiss_alerts(page)
                out["steps"].append("clicked_next_js")
            except Exception as exc2:
                out["next_js_error"] = str(exc2)

    body2 = page.inner_text("body", timeout=5000)
    if "신청서작성" in body2 and "STEP01" not in body2[:800]:
        try:
            apply = page.locator("#mf_wfm_contents_btn_apply")
            if apply.count():
                apply.first.click(timeout=10_000)
                page.wait_for_timeout(5000)
                _dismiss_alerts(page)
                out["steps"].append("clicked_apply_founded")
        except Exception as exc:
            out["apply_error"] = str(exc)

    out["ok"] = True
    out["url"] = page.url
    return out


def _pms_click_js(page, element_id: str) -> bool:
    try:
        page.evaluate(f"() => {{ const el=document.getElementById('{element_id}'); if(el) el.click(); }}")
        page.wait_for_timeout(2500)
        _dismiss_alerts(page)
        return True
    except Exception:
        return False


WIZARD_URL_MARKERS = (
    "BMO0701",
    "BMO0801",
    "BMO0601",
    "BMO0901",
    "BMO0902",
    "BMO0303",
    "BMO0304",
    "BMO0305",
)
OFF_WIZARD_URL_MARKERS = ("BMO1101", "NCOB0101")


def _on_apply_wizard(url: str, body: str) -> bool:
    u = url or ""
    if any(m in u for m in WIZARD_URL_MARKERS):
        return True
    if "공고조회/신청" in body and any(
        k in body for k in ("약관에 동의", "기업정보", "신청자정보", "일반현황", "인력정보", "사업계획")
    ):
        return True
    return False


def _recover_wizard_from_history(
    page, history_url: str, keywords: list[str], apply_entry_url: str = ""
) -> dict[str, Any]:
    """사업신청내역 수정하기 또는 pbancId 직접 진입으로 위저드 복귀."""
    u = page.url or ""
    body = ""
    try:
        body = page.inner_text("body", timeout=5000)
    except Exception:
        pass
    if _on_apply_wizard(u, body):
        return {"ok": True, "skipped": True, "url": u}
    nav = _open_from_history(page, history_url, keywords)
    if nav.get("ok"):
        page.wait_for_timeout(2500)
        _dismiss_alerts(page)
        return {"ok": True, "via": "history_recover", "url": page.url, **nav}
    if apply_entry_url:
        page.goto(apply_entry_url, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(3500)
        _dismiss_alerts(page)
        return {"ok": True, "via": "pms_apply_entry", "url": page.url}
    return nav


def _is_apply_entry_screen(url: str, body: str) -> bool:
    u = url or ""
    if "BMO0101" in u:
        return True
    b = body or ""
    return "주관기관" in b and any(k in b for k in ("신청", "도약", "AI"))


def _fill_apply_entry_bmo0101(page, cfg: dict[str, Any]) -> dict[str, Any]:
    """G3 — BMO0101 공고 신청 화면: 트랙·딥테크·주관기관 1곳 선택 후 신청 진입."""
    import os

    prog = cfg.get("program") or {}
    pms = cfg.get("pms") or {}
    track = prog.get("track") or "도약"
    deeptech = prog.get("deeptech") or "AI·빅데이터"
    host_pref = (
        (pms.get("host_institution_name") or "").strip()
        or os.environ.get("MKM_STARTUP_PKG_HOST_INSTITUTION", "").strip()
    )
    out: dict[str, Any] = {"actions": [], "host_selected": None, "host_pref": host_pref or None}

    for label in (track, deeptech):
        try:
            loc = page.get_by_text(label, exact=False)
            if loc.count():
                loc.first.click(timeout=6000)
                page.wait_for_timeout(1200)
                out["actions"].append(f"track:{label}")
        except Exception:
            pass

    host_result = page.evaluate(
        """(pref) => {
          const body = document.body.innerText || '';
          if (!body.includes('주관') && !document.querySelector('input[type=radio]')) {
            return { skipped: true, reason: 'no_host_section' };
          }
          const radios = [...document.querySelectorAll('input[type=radio]')];
          let target = null;
          if (pref) {
            for (const r of radios) {
              const row = r.closest('tr') || r.closest('li') || r.parentElement;
              const txt = (row?.innerText || '').trim();
              if (txt.includes(pref)) { target = r; break; }
            }
          }
          if (!target) {
            for (const r of radios) {
              if (r.offsetParent === null) continue;
              const row = r.closest('tr') || r.parentElement;
              const txt = (row?.innerText || '').trim();
              if (txt.length > 4 && !txt.includes('동의') && !txt.includes('비동의')) {
                target = r;
                break;
              }
            }
          }
          if (!target) return { ok: false, reason: 'no_radio' };
          target.click();
          target.dispatchEvent(new Event('change', { bubbles: true }));
          const row = target.closest('tr') || target.parentElement;
          return { ok: true, name: (row?.innerText || '').trim().slice(0, 160) };
        }""",
        host_pref,
    )
    out["host"] = host_result
    if host_result.get("ok"):
        out["host_selected"] = host_result.get("name")
        out["actions"].append("host_radio")

    for label in ("신청하기", "신청", "접수", "다음", "사업신청", "확인"):
        clicked = False
        try:
            btn = page.get_by_role("button", name=re.compile(label))
            if btn.count():
                btn.first.click(timeout=8000)
                clicked = True
        except Exception:
            pass
        if not clicked:
            try:
                loc = page.get_by_text(label, exact=False)
                if loc.count():
                    loc.first.click(timeout=5000)
                    clicked = True
            except Exception:
                pass
        if clicked:
            page.wait_for_timeout(3500)
            _dismiss_alerts(page)
            out["actions"].append(f"cta:{label}")
            break

    out["url"] = page.url
    out["ok"] = bool(host_result.get("ok") or host_result.get("skipped"))
    return out


def _fill_company_step(page, cfg: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"actions": []}
    body = page.inner_text("body", timeout=5000)
    if "기업정보" not in body and "BMO0801" not in (page.url or ""):
        return {"skipped": True}
    entity = cfg.get("legal_entity") or {}
    brn = entity.get("brn", "")
    for label, eid in (
        ("기업상세정보 불러오기", "mf_wfm_contents_btn_autoInput"),
        ("저장", "mf_wfm_contents_btn_save"),
    ):
        try:
            loc = page.get_by_text(label, exact=False)
            if loc.count():
                loc.first.click(timeout=8000)
                page.wait_for_timeout(3500)
                _dismiss_alerts(page)
                out["actions"].append(label)
        except Exception:
            if _pms_click_js(page, eid):
                out["actions"].append(f"{label}_js")
    fields = {
        "mf_wfm_contents_ibx_instEngNm": "Moksori Network Inc.",
        "mf_wfm_contents_ibx_hmpgAddr": "https://jema-ai.com",
        "mf_wfm_contents_ibx_majrProdMtitNm": (
            "공공·정책 신청 문서 AI 초안 생성 플랫폼 (RAG·근거연동·출력보류 게이트)"
        ),
        "mf_wfm_contents_ibx_empmNmprCnt": "1",
        "mf_wfm_contents_ibx_salesAmt": "0",
        "mf_wfm_contents_ibx_telno": "010-3677-0676",
    }
    filled: dict[str, bool] = {}
    for fid, val in fields.items():
        try:
            loc = page.locator(f"#{fid}")
            if loc.count() and loc.first.is_visible():
                filled[fid] = _set_input(page, f"#{fid}", val)
        except Exception:
            filled[fid] = False
    out["filled"] = {k: v for k, v in filled.items() if v}
    if brn:
        try:
            brn_loc = page.locator("#mf_wfm_contents_ibx_bsmnRegNo")
            if brn_loc.count() and not (brn_loc.input_value() or "").strip():
                page.evaluate(
                    """(brn) => {
                      const el = document.getElementById('mf_wfm_contents_ibx_bsmnRegNo');
                      if (el && !el.readOnly) { el.value = brn; el.dispatchEvent(new Event('input',{bubbles:true})); }
                    }""",
                    brn.replace("-", ""),
                )
                out["actions"].append("brn_typed")
        except Exception:
            pass
    if page.locator("#mf_wfm_contents_btn_save").count():
        _pms_click_js(page, "mf_wfm_contents_btn_save")
        out["actions"].append("저장_js")
    if page.locator("#mf_wfm_contents_btn_addRprsvList").count():
        out["rep"] = _add_representative(page)
    out["url"] = page.url
    return out


def _wizard_next_only(page) -> bool:
    """위저드 본문 '다음'만 — 사이드/전역 text=다음 클릭 금지."""
    try:
        clicked = page.evaluate(
            """() => {
              const n = document.getElementById('mf_wfm_contents_btn_next');
              if (!n || n.offsetParent === null) return false;
              n.click();
              return true;
            }"""
        )
        if clicked:
            page.wait_for_timeout(3000)
            _dismiss_alerts(page)
            return True
    except Exception:
        pass
    return False


def _count_empty_textareas(page) -> tuple[int, int]:
    total = page.locator("textarea").count()
    empty = 0
    for ta in page.locator("textarea").all():
        try:
            if len((ta.input_value() or "").strip()) < 30:
                empty += 1
        except Exception:
            pass
    return total, empty


def _advance_until_textareas(page, max_clicks: int = 10) -> dict[str, Any]:
    """빈 textarea 나올 때까지 저장·위저드 다음만 클릭. BMO0601 이탈 시 중단."""
    clicks = 0
    last_url = ""
    for _ in range(max_clicks):
        url = page.url or ""
        if any(m in url for m in OFF_WIZARD_URL_MARKERS) and "공고조회/신청" not in (
            page.inner_text("body", timeout=3000) or ""
        ):
            return {
                "ok": False,
                "clicks": clicks,
                "reason": "off_wizard_screen",
                "last_url": url,
            }
        total, empty = _count_empty_textareas(page)
        if total > 0 and empty > 0:
            return {"ok": True, "textareas": total, "empty": empty, "clicks": clicks, "last_url": url}
        tsks = page.locator("#mf_wfm_contents_ibx_tsksNm")
        if tsks.count():
            try:
                if tsks.first.is_visible():
                    nav = _goto_step4(page)
                    if nav.get("step") == 4 and tsks.first.is_visible():
                        step4 = _fill_step4(page)
                        return {
                            "ok": bool(step4.get("ok")),
                            "clicks": clicks,
                            "via": "step4_fill",
                            "step4": step4,
                            "last_url": page.url,
                        }
            except Exception:
                pass
        _pms_click_js(page, "mf_wfm_contents_btn_save")
        if not _wizard_next_only(page):
            break
        clicks += 1
        new_url = page.url or ""
        if new_url == last_url and clicks > 1:
            break
        last_url = new_url
    total, empty = _count_empty_textareas(page)
    return {
        "ok": total > 0 and empty > 0,
        "clicks": clicks,
        "textareas": total,
        "empty": empty,
        "last_url": page.url,
    }


def _temp_save(page) -> bool:
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
    ap.add_argument("--wait-pms-sso-sec", type=int, default=180, help="통합로그인 후 PMS 탭 대기")
    ap.add_argument("--pms-url", default="", help="사업신청 PMS 화면 URL (history 생략)")
    ap.add_argument("--portal-url", default="", help="K-Startup 공고 상세 URL (pbancSn)")
    ap.add_argument("--from-portal", action="store_true", help="공고 상세에서 사업신청 클릭")
    ap.add_argument("--probe-only", action="store_true")
    ap.add_argument("--skip-upload", action="store_true")
    ap.add_argument(
        "--skip-submission-gate",
        action="store_true",
        help="Bypass upload gate (default: require human gates + forbidden scan).",
    )
    args = ap.parse_args()

    if not args.skip_submission_gate and not args.probe_only:
        gate_script = ROOT / "scripts/check_kstartup_startup_package_ai_submission_gate_v1.py"
        gate_rc = subprocess.call([sys.executable, str(gate_script)], cwd=str(ROOT))
        if gate_rc != 0:
            print(
                "submission gate blocked autofill — complete human gates + forbidden scan, "
                "or use --skip-submission-gate (emergency only)",
                file=sys.stderr,
            )
            return gate_rc

    cfg = _load_config()
    prog = cfg.get("program") or {}
    pms = cfg.get("pms") or {}
    history_url = pms.get("history_url") or "https://pms.k-startup.go.kr/biz/screen/BMO1101M0100"
    keywords = pms.get("row_match_keywords") or ["AI 인재", "창업패키지"]
    apply_entry_url = pms.get("pms_apply_entry_url") or (
        "https://pms.k-startup.go.kr/biz/screen/BMO0101M01?pbancId=0661001"
    )
    form_override = args.pms_url or pms.get("form_url_override") or ""
    portal_url = (
        args.portal_url
        or prog.get("portal_detail_url")
        or ""
    )
    track = prog.get("track") or "도약"
    from_portal = args.from_portal or bool(portal_url and not form_override)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("pip install playwright && playwright install chromium", file=sys.stderr)
        return 2

    import os

    att = cfg.get("attachments") or {}
    filled = cfg.get("filled_outputs") or {}
    plan_pdf = Path(os.environ.get(PLAN_PDF_ENV, "").strip()) if os.environ.get(PLAN_PDF_ENV) else None
    if not plan_pdf or not plan_pdf.is_file():
        filled_pdf = filled.get("plan_pdf")
        if filled_pdf:
            candidate = ROOT / filled_pdf
            if candidate.is_file():
                plan_pdf = candidate
    ai_pdf = Path(os.environ.get(AI_TALENT_PDF_ENV, "").strip()) if os.environ.get(AI_TALENT_PDF_ENV) else None
    if not ai_pdf or not ai_pdf.is_file():
        filled_ai = filled.get("ai_talent_pdf")
        if filled_ai:
            candidate = ROOT / filled_ai
            if candidate.is_file():
                ai_pdf = candidate
    log_plan_source = str(plan_pdf) if plan_pdf else ""

    log: dict[str, Any] = {
        "schema": "kstartup_startup_package_ai_autofill_v1",
        "generated_at_utc": _utc(),
        "program": (cfg.get("program") or {}).get("title"),
        "boundary_ack": "no_final_submit — human 제출완료 only",
        "opendata_lane": "not_used",
    }

    chunks = _load_paste_chunks()
    if not chunks:
        log["error"] = f"paste_pack_missing — run build_kstartup_startup_package_ai_paste_ready_v1.py"
        OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return 1

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(args.cdp_url.strip())
        except Exception as exc:
            log["error"] = f"cdp_connect_failed: {exc}"
            OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return 1

        context = browser.contexts[0] if browser.contexts else browser.new_context()
        prefer_pms = form_override or apply_entry_url
        pms_pg = _attach_pms_page(context, prefer_pms)
        page = pms_pg if pms_pg is not None else _pick_work_page(context)
        log["attach_url"] = page.url
        log["open_tabs"] = [pg.url for pg in context.pages]

        cur_url = page.url or ""
        if _is_pms_host_url(cur_url) and _session_ready(page):
            logged_in = True
        elif "webLGIN" in cur_url and ("pms" in cur_url or "webPMSBizUnvs" in cur_url):
            log["pms_sso_pending"] = True
            pms_pg = _wait_for_pms_page(context, args.wait_pms_sso_sec)
            logged_in = pms_pg is not None
        else:
            try:
                logged_in = _wait_logged_in(page, args.wait_for_login_sec)
            except Exception as wait_exc:
                log["wait_error"] = str(wait_exc)
                page = _pick_work_page(context)
                logged_in = _wait_logged_in(page, max(30, args.wait_for_login_sec // 3))

        if not logged_in and pms_pg is None and form_override:
            try:
                page.goto(form_override, wait_until="domcontentloaded", timeout=120_000)
                page.wait_for_timeout(2500)
                _dismiss_alerts(page)
                logged_in = _is_pms_host_url(page.url or "") and _session_ready(page)
                log["nav_fallback"] = {"ok": logged_in, "url": page.url}
            except Exception as nav_exc:
                log["nav_fallback_error"] = str(nav_exc)

        if not logged_in and pms_pg is None:
            log["error"] = (
                "login_timeout — 공고 페이지(마이페이지) 또는 통합로그인 탭에서 "
                "간편인증 완료 후 재실행"
            )
            log["page_url"] = page.url
            log["hint"] = "창업도약패키지 클릭 → confirm 확인 → Any-ID 로그인 → PMS 진입"
            OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return 1

        if pms_pg and _is_pms_host_url(pms_pg.url or ""):
            page = pms_pg
            log["pms_attached"] = page.url

        if form_override:
            cur = page.url or ""
            if form_override.split("?")[0] not in cur:
                page.goto(form_override, wait_until="domcontentloaded", timeout=120_000)
                page.wait_for_timeout(3000)
            _dismiss_alerts(page)
            if "webLGIN" in (page.url or "") or not _session_ready(page):
                if not _wait_logged_in(page, args.wait_for_login_sec):
                    pms_pg = _wait_for_pms_page(context, args.wait_pms_sso_sec)
                    if pms_pg:
                        page = pms_pg
                    else:
                        log["error"] = (
                            "login_timeout — CDP Chrome에서 Any-ID 간편인증 완료 후 재실행"
                        )
                        log["page_url"] = page.url
                        OUT.write_text(
                            json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
                        )
                        return 1
            log["nav"] = {"ok": True, "via": "pms_url", "url": page.url, "skipped_reload": form_override.split("?")[0] in cur}
        elif _is_pms_host_url(page.url or ""):
            log["nav"] = {"ok": True, "via": "pms_tab_already", "url": page.url}
        elif from_portal and portal_url:
            log["nav"] = _open_from_portal(page, portal_url, track=track, context=context)
            if log["nav"].get("pms_sso_pending"):
                pms_pg = _wait_for_pms_page(context, args.wait_pms_sso_sec)
                if pms_pg:
                    page = pms_pg
                    log["nav"]["pms_sso_pending"] = False
                    log["nav"]["pms_url"] = page.url
                else:
                    log["error"] = (
                        "pms_sso_timeout — 열린 통합로그인 탭에서 간편인증(네이버/카카오 등) "
                        "완료 후 재실행"
                    )
                    log["open_tabs"] = [pg.url for pg in context.pages]
                    OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                    return 1
            elif log["nav"].get("popup"):
                for pg in context.pages:
                    if "pms.k-startup" in (pg.url or ""):
                        page = pg
                        break
                else:
                    page = context.pages[-1] if context.pages else page
        else:
            log["nav"] = _open_from_history(page, history_url, keywords)

        log["probe"] = _probe_page(page)
        OUT_PROBE = ROOT / "reports/kstartup_startup_package_ai_pms_probe_latest.json"
        OUT_PROBE.write_text(json.dumps(log["probe"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        if args.probe_only:
            log["mode"] = "probe_only"
            OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(log, ensure_ascii=False, indent=2))
            return 0

        if not log["nav"].get("ok") and not form_override:
            log["hint"] = "PMS URL을 --pms-url 로 주거나 config form_url_override 설정"
            OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return 1

        body0 = ""
        try:
            body0 = page.inner_text("body", timeout=5000)
        except Exception:
            pass
        apply_url = apply_entry_url.split("?")[0]
        if "BMO0101" in (page.url or "") or (
            apply_url in (page.url or "") and _is_apply_entry_screen(page.url or "", body0)
        ):
            log["apply_entry"] = _fill_apply_entry_bmo0101(page, cfg)
            page.wait_for_timeout(2500)
            try:
                body0 = page.inner_text("body", timeout=5000)
            except Exception:
                pass
        if not _on_apply_wizard(page.url or "", body0):
            log["recover"] = _recover_wizard_from_history(
                page, history_url, keywords, apply_entry_url=apply_entry_url
            )
            if not log["recover"].get("ok"):
                log["hint"] = "PMS 사업신청내역에서 AI 인재 행 → 수정하기 후 --pms-url 로 재실행"
                OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                return 1

        log["terms"] = _accept_terms_and_advance(page)
        if "BMO0801" not in (page.url or ""):
            for _ in range(4):
                if "BMO0801" in (page.url or ""):
                    break
                _wizard_next_only(page)
                page.wait_for_timeout(2000)
        log["company"] = _fill_company_step(page, cfg)
        log["advance"] = _advance_until_textareas(page)
        log["probe_after_steps"] = _probe_page(page)

        log["textareas"] = _fill_textareas(page, chunks)

        if not args.skip_upload:
            for _ in range(12):
                _dismiss_alerts(page)
                page.wait_for_timeout(250)
            for _ in range(8):
                has_files = page.locator('input[type="file"]').count() > 0
                has_plan_row = page.locator("tr").filter(has_text="사업계획").count() > 0
                if has_files or has_plan_row:
                    break
                _pms_click_js(page, "mf_wfm_contents_btn_save")
                _wizard_next_only(page)
                page.wait_for_timeout(2000)
                _dismiss_alerts(page)
            log["upload_step_url"] = page.url

            uploads: dict[str, Any] = {}
            if not plan_pdf or not plan_pdf.is_file():
                uploads = {
                    "error": "filled_plan_pdf_missing",
                    "hint": "py scripts/fill_kstartup_startup_package_ai_doyak_docx_v1.py && verify",
                    "fill_script": filled.get("fill_script"),
                }
            elif plan_pdf.suffix.lower() == ".docx" and "filled" not in plan_pdf.name.lower():
                uploads = {
                    "error": "blank_template_upload_blocked",
                    "path": str(plan_pdf),
                    "hint": "use filled PDF from reports/kstartup_startup_package_ai_filled/",
                }
            else:
                for hint in ("사업계획", "별첨1", "계획서", "사업계획서"):
                    uploads[hint] = _upload_file_row(page, hint, plan_pdf)
                    if uploads[hint].get("ok"):
                        break
                if not any(u.get("ok") for u in uploads.values()):
                    uploads["first_file_input"] = _upload_first_file_input(page, plan_pdf)
                if ai_pdf and ai_pdf.is_file():
                    for hint in ("AI 인재", "인재 활용", "2p"):
                        uploads[f"ai_{hint}"] = _upload_file_row(page, hint, ai_pdf)
            log["uploads"] = uploads
            log["plan_source"] = log_plan_source

        log["temp_save"] = _temp_save(page)
        try:
            shot = ROOT / "reports/kstartup_startup_package_ai_autofill_latest.png"
            page.screenshot(path=str(shot), full_page=False)
            log["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
        except Exception:
            pass

        ok = bool(
            log.get("temp_save")
            or log.get("textareas", {}).get("count", 0) > 0
            or log.get("advance", {}).get("ok")
            or log.get("advance", {}).get("step4", {}).get("ok")
        )
        log["exit_ok"] = ok
        OUT.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(log, ensure_ascii=False, indent=2))
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
