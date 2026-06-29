#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build copy-paste HTML card for patient wellness entry (Track C · non-medical)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COPY_JSON = ROOT / "projects" / "no1kmedi" / "marketing-site" / "public-copy.json"
OUT_DIR = ROOT / "reports" / "patient_wellness_entry"
OUT_HTML = ROOT / "reports" / "demo" / "patient_wellness_entry_card_v1.html"


def _load_blocks() -> dict[str, str]:
    data = json.loads(COPY_JSON.read_text(encoding="utf-8"))
    entry = data.get("patient_wellness_entry") or {}
    kakao = entry.get("kakao_blocks") or {}
    disclaimer = entry.get("disclaimer") or {}
    items = disclaimer.get("items") or []
    return {
        "intro_kakao": str(kakao.get("intro", "")).strip(),
        "link_block": str(kakao.get("links", "")).strip(),
        "one_line": (
            "질병 진단·치료·처방을 하지 않습니다. "
            "일상 리듬·성찰·페이스 조절 참고용이며, 증상·치료는 한의원 진료를 이용해 주세요."
        ),
        "forbidden_3lines": (
            "【대외 금지 3줄 · 환자면】\n"
            "1) AI·사주로 체질·질병 진단/처방\n"
            "2) KoGES 사상 + 사주 오행 합성(「과학적 사주 체질 AI」)\n"
            "3) 근거 없는 ○○% 임상·건강 정확도"
        ),
        "disclaimer_footer": (
            f"{disclaimer.get('body', '').strip()}\n"
            + "\n".join(f"· {x}" for x in items)
            + "\n\nSSOT: docs/final/artifacts/patient_wellness_entry_copy_v1_latest.md"
        ).strip(),
    }


def _html_block(block_id: str, title: str, text: str) -> str:
    safe_id = block_id.replace("-", "_")
    return (
        f'<section><h3>{title}</h3>'
        f'<pre id="t_{safe_id}">{text}</pre>'
        f'<button type="button" onclick="copy(\'t_{safe_id}\')">복사</button></section>'
    )


def build_html(blocks: dict[str, str]) -> str:
    sections = [
        ("one_line", "허브·카톡 공용 1줄", blocks["one_line"]),
        ("intro_kakao", "카카오 인트로", blocks["intro_kakao"]),
        ("link_block", "카카오 링크 블록", blocks["link_block"]),
        ("forbidden_3lines", "대외 금지 3줄", blocks["forbidden_3lines"]),
        ("disclaimer_footer", "면책 푸터", blocks["disclaimer_footer"]),
    ]
    body_sections = "\n".join(_html_block(i, t, c) for i, t, c in sections)
    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>환자 웰니스 · 카피 카드</title>
<style>
@import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
@media print {{
  button {{ display: none; }}
  body {{ background: #fff; color: #111; max-width: 100%; }}
  section {{ break-inside: avoid; border-color: #ccc; }}
}}
:root {{
  --bg: #0a1210;
  --surface: #121c19;
  --text: #e8ebe9;
  --muted: #9aa9a3;
  --accent: #3d9b84;
  --warn: #e8c88a;
  --line: rgba(255,255,255,0.08);
}}
* {{ box-sizing: border-box; }}
body {{
  font-family: "Pretendard Variable", Pretendard, system-ui, sans-serif;
  max-width: 760px;
  margin: 28px auto;
  padding: 0 18px 40px;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
}}
h1 {{ font-size: 1.35rem; letter-spacing: -0.02em; margin-bottom: 0.35rem; }}
section {{
  margin: 16px 0;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: linear-gradient(165deg, rgba(61,155,132,0.06), rgba(18,28,25,0.92));
}}
section h3 {{ margin: 0 0 10px; font-size: 0.95rem; color: #9de5d3; }}
pre {{
  white-space: pre-wrap;
  background: rgba(0,0,0,0.25);
  padding: 12px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.55;
  margin: 0;
  border: 1px solid rgba(255,255,255,0.06);
}}
button {{
  margin-top: 10px;
  padding: 9px 16px;
  background: linear-gradient(180deg, #4fb69d, #3d9b84);
  color: #041210;
  font-weight: 600;
  border: 0;
  border-radius: 8px;
  cursor: pointer;
}}
.meta {{ color: var(--muted); font-size: 12px; }}
.ok {{ color: #9de5d3; }}
.warn {{ color: var(--warn); }}
.hold {{
  margin: 14px 0;
  padding: 10px 12px;
  border-left: 3px solid rgba(200,160,80,0.55);
  background: rgba(200,160,80,0.1);
  border-radius: 0 8px 8px 0;
  font-size: 13px;
}}
</style></head><body>
<h1>환자 웰니스 · 카카오 카피 카드 (v1)</h1>
<p class="ok">Track C · 비진단 · L3 wellness only · mkmlife rhythm</p>
<p class="warn">SEND_GATE: HOLD · 법무·의료광고 검토 전 배포 금지</p>
<p class="hold">ready_for_external_send: false — 채널·허브 대외 게시 전 검토 필수</p>
<p class="meta">SSOT: patient_wellness_entry_copy_v1_latest.md · route: /wellness · source: public-copy.json</p>
<p class="meta">재빌드: <code>py scripts/build_patient_wellness_entry_card_v1.py</code></p>
{body_sections}
<script>
function copy(id){{const t=document.getElementById(id).innerText;navigator.clipboard.writeText(t).then(()=>alert('복사됨'))}}
</script></body></html>
"""


def main() -> int:
    blocks = _load_blocks()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    for name, text in blocks.items():
        (OUT_DIR / f"{name}.txt").write_text(text + "\n", encoding="utf-8")
    OUT_HTML.write_text(build_html(blocks), encoding="utf-8")
    print(f"OK: {OUT_HTML}")
    print(f"OK: {OUT_DIR} ({len(blocks)} txt)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
