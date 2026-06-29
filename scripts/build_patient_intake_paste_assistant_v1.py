#!/usr/bin/env python3
"""Reception desk paste assistant — SMS / Kakao copy blocks for /intake PoC."""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "docs/final/artifacts/patient_intake_notification_templates_v1.json"
GATE = ROOT / "docs/final/artifacts/patient_intake_send_gate_v1_latest.json"
WELLNESS = ROOT / "docs/final/artifacts/patient_wellness_entry_copy_v1_latest.md"
OUT = ROOT / "reports/demo/patient_intake_paste_assistant_v1.html"


def _render(body: str, variables: dict[str, str]) -> str:
    out = body
    for key, value in variables.items():
        out = out.replace("{" + key + "}", value)
    return out


def _extract_codeblock(md: str, heading: str) -> str:
    marker = f"### {heading}"
    if marker not in md:
        return ""
    chunk = md.split(marker, 1)[1]
    if "```" not in chunk:
        return ""
    return chunk.split("```", 2)[1].strip()


def main() -> int:
    if not TPL.is_file():
        raise SystemExit(f"missing {TPL}")

    tpl_doc = json.loads(TPL.read_text(encoding="utf-8"))
    gate_doc = json.loads(GATE.read_text(encoding="utf-8")) if GATE.is_file() else {}
    wellness_md = WELLNESS.read_text(encoding="utf-8") if WELLNESS.is_file() else ""

    intake_url = str(tpl_doc.get("intake_url_default") or "https://jema-ai.com/intake")
    vars_ = {"intake_url": intake_url, "clinic_name": "한의원", "intake_pin": "ABC-123"}

    sections: list[tuple[str, str]] = []
    for key, tpl in (tpl_doc.get("templates") or {}).items():
        title = {
            "reservation_sms": "예약 확정 SMS (사전 문진 링크)",
            "intake_pin_sms": "문진 제출 후 PIN SMS",
            "kakao_link_block": "카카오 채널 링크 블록",
        }.get(key, key)
        sections.append((title, _render(str(tpl.get("body") or ""), vars_)))

    intro = _extract_codeblock(wellness_md, "intro_kakao")
    if intro:
        sections.insert(0, ("카카오 채널 인트로", intro))

    send_gate = gate_doc.get("send_gate", "HOLD")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    parts = [
        "<!DOCTYPE html><html lang='ko'><head><meta charset='utf-8'/>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'/>",
        "<title>사전 문진 붙여넣기 · 접수 데스크</title>",
        "<link rel='stylesheet' href='https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css'>",
        "<style>",
        "body{font-family:Pretendard,system-ui,sans-serif;background:#0a1210;color:#e8ebe9;max-width:760px;margin:24px auto;padding:0 16px 32px;line-height:1.6}",
        "h1{font-size:1.2rem} .meta{color:#9fb0a8;font-size:.85rem}",
        ".warn{color:#e8c88a;font-size:.85rem}",
        "section{margin:14px 0;padding:14px;border:1px solid rgba(255,255,255,.1);border-radius:10px;background:#151c19}",
        "pre{white-space:pre-wrap;background:#0a0f0d;padding:12px;border-radius:8px;font-size:13px;margin:8px 0 0}",
        "button{padding:8px 14px;background:#3d9b84;color:#041210;border:0;border-radius:8px;font-weight:600;cursor:pointer}",
        "</style></head><body>",
        "<h1>한의원 사전 문진 · 붙여넣기 보조</h1>",
        f"<p class='meta'>생성: {html.escape(ts)} · intake SSOT: /intake</p>",
        f"<p class='warn'>SEND_GATE: {html.escape(str(send_gate))} · 대외 대량 발송 전 법무 확인 · 내부 PoC는 수동 복사·테스트망만</p>",
    ]

    for i, (title, body) in enumerate(sections):
        sid = f"s{i}"
        parts.append(f"<section><h2>{html.escape(title)}</h2>")
        parts.append(f"<button type='button' data-copy='{sid}'>클립보드 복사</button>")
        parts.append(f"<pre id='{sid}'>{html.escape(body)}</pre></section>")

    parts.append(
        "<script>document.querySelectorAll('[data-copy]').forEach(btn=>{"
        "btn.onclick=()=>navigator.clipboard.writeText(document.getElementById(btn.dataset.copy).textContent)"
        ".then(()=>alert('복사됨'));});</script></body></html>"
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(parts), encoding="utf-8")
    public_copy = ROOT / "projects/no1kmedi/public/demo/patient_intake_paste_assistant_v1.html"
    public_copy.parent.mkdir(parents=True, exist_ok=True)
    public_copy.write_text(OUT.read_text(encoding="utf-8"), encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(OUT), "public_copy": str(public_copy), "sections": len(sections), "send_gate": send_gate}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
