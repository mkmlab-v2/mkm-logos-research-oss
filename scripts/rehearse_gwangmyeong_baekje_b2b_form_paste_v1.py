#!/usr/bin/env python3
"""[HYPO] Local rehearsal for gwangmyeong B2B Google Form paste assistant (no submit, no Solapi)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "reports/demo/gwangmyeong_baekje_b2b_form_paste_assistant_v1.html"
SPEC = ROOT / "docs/final/artifacts/gwangmyeong_baekje_b2b_training_spec_v1.json"
FORM_URLS = ROOT / "reports/gwangmyeong_baekje_b2b_google_form_urls_v1.json"
OUT = ROOT / "reports/demo/gwangmyeong_baekje_b2b_form_paste_rehearsal_v1_latest.json"

FORBIDDEN = (
    "KAKAO_CLINIC_INTAKE_WEBHOOK",
    "환자 유치",
    "환자 소개",
    "보수교육",
    "AKOM",
    "Solapi",
    "알림톡 발송",
)

EXPECTED_BLOCKS = {
    "f1": ("FORM-01", ("성함", "연락처", "면허", "한의원", "개인정보")),
    "f2": ("FORM-02", ("주차", "Drive", "면책")),
    "f3": ("FORM-03", ("theory", "practice", "비식별")),
}


class _PreExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_pre = False
        self._cur_id: str | None = None
        self.blocks: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "pre":
            return
        aid = dict(attrs).get("id")
        if aid:
            self._in_pre = True
            self._cur_id = aid
            self.blocks.setdefault(aid, "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "pre":
            self._in_pre = False
            self._cur_id = None

    def handle_data(self, data: str) -> None:
        if self._in_pre and self._cur_id:
            self.blocks[self._cur_id] += data


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _head_ms(url: str, timeout: float = 15.0) -> dict[str, object]:
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "MKM-rehearsal/1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            return {
                "url": url,
                "ok": 200 <= resp.status < 400,
                "status": resp.status,
                "elapsed_ms": elapsed_ms,
            }
    except urllib.error.HTTPError as e:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        return {"url": url, "ok": False, "status": e.code, "elapsed_ms": elapsed_ms, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        return {"url": url, "ok": False, "status": None, "elapsed_ms": elapsed_ms, "error": str(e)}


def _run_barrier_audit() -> dict[str, object]:
    proc = subprocess.run(
        [sys.executable, "scripts/check_gwangmyeong_baekje_b2b_training_spec_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    audit_path = ROOT / "reports/gwangmyeong_baekje_b2b_barrier_audit_v1_latest.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.is_file() else {}
    return {
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0 and audit.get("ok") is True,
        "audit_status": audit.get("audit_status"),
        "send_gate": audit.get("send_gate"),
    }


def main() -> int:
    checks: list[dict[str, object]] = []
    overall = True

    barrier = _run_barrier_audit()
    checks.append({"id": "barrier_audit", "ok": barrier["ok"], "detail": barrier})
    overall &= bool(barrier["ok"])

    if not HTML.is_file():
        checks.append({"id": "html_exists", "ok": False, "detail": str(HTML)})
        overall = False
    else:
        raw = HTML.read_text(encoding="utf-8")
        checks.append({"id": "html_exists", "ok": True, "detail": str(HTML)})
        checks.append({"id": "send_gate_banner", "ok": "SEND_GATE: HOLD" in raw, "detail": "SEND_GATE: HOLD"})
        overall &= "SEND_GATE: HOLD" in raw

        hits = [w for w in FORBIDDEN if w in raw and w != "Solapi"]
        forbid_ok = not hits
        checks.append({"id": "forbidden_copy", "ok": forbid_ok, "detail": {"hits": hits}})
        overall &= forbid_ok

        parser = _PreExtractor()
        parser.feed(raw)
        for bid, (label, needles) in EXPECTED_BLOCKS.items():
            text = parser.blocks.get(bid, "")
            missing = [n for n in needles if n not in text]
            ok = bool(text.strip()) and not missing
            checks.append(
                {
                    "id": f"block_{bid}",
                    "ok": ok,
                    "detail": {"label": label, "chars": len(text), "missing": missing},
                }
            )
            overall &= ok

        copy_fn = "function copy(id)" in raw and "navigator.clipboard" in raw
        checks.append({"id": "clipboard_js", "ok": copy_fn, "detail": "copy()+clipboard API"})
        overall &= copy_fn

    form_timings: list[dict[str, object]] = []
    if FORM_URLS.is_file():
        urls_doc = json.loads(FORM_URLS.read_text(encoding="utf-8"))
        forms = urls_doc.get("forms") or {}
        f01 = forms.get("FORM-01_registration") or {}
        responder = f01.get("responder_url")
        if responder:
            timing = _head_ms(responder)
            timing["form"] = "FORM-01_registration"
            form_timings.append(timing)
            checks.append(
                {
                    "id": "form01_responder_reachable",
                    "ok": timing.get("ok"),
                    "detail": timing,
                }
            )
            overall &= bool(timing.get("ok"))

        f02 = forms.get("FORM-02_assignment") or {}
        f02_status = f02.get("status")
        if f02_status in ("draft_corrupted", "draft_recovered_unpublished"):
            checks.append(
                {
                    "id": "form02_status",
                    "ok": True,
                    "detail": (
                        f"{f02_status} — commander publish + register script expected "
                        "(not blocking rehearsal)"
                    ),
                }
            )
        f03 = forms.get("FORM-03_qa") or {}
        if f03.get("status") == "draft_corrupted":
            checks.append(
                {
                    "id": "form03_status",
                    "ok": True,
                    "detail": "draft_corrupted — paste assistant §FORM-03 manual recovery expected",
                }
            )
        elif f03.get("status") == "draft_recovered_unpublished":
            checks.append(
                {
                    "id": "form03_status",
                    "ok": True,
                    "detail": "draft_recovered_unpublished — commander publish + register expected",
                }
            )

    spec_ok = SPEC.is_file()
    checks.append({"id": "spec_ssot", "ok": spec_ok, "detail": str(SPEC)})
    overall &= spec_ok

    report = {
        "schema": "gwangmyeong_baekje_b2b_form_paste_rehearsal_v1",
        "generated_at_utc": _utc(),
        "lane": "b2b_training_hypo",
        "send_gate": "HOLD",
        "solapi_live_send": False,
        "form_submit": False,
        "reproduce": "py scripts/rehearse_gwangmyeong_baekje_b2b_form_paste_v1.py",
        "paste_assistant_html": "reports/demo/gwangmyeong_baekje_b2b_form_paste_assistant_v1.html",
        "overall_ok": overall,
        "checks": checks,
        "form_head_timings_ms": form_timings,
        "operator_notes": [
            "FORM-02: commander 게시 1클릭 → copy short+responder → register_gwangmyeong_baekje_b2b_form_publish_v1.py",
            "FORM-03: paste assistant §f3 → editor 복구 → 게시 → same register script --form FORM-03",
            "Paste assistant: Invoke-GwangmyeongB2bFormPasteRehearsal_v1.ps1 -ServeAssistant",
            "No PII submitted; HEAD-only on public responder URL.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"overall_ok": overall, "out": str(OUT.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
