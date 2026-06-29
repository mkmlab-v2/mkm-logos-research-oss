#!/usr/bin/env python3
"""Local HTML assistant for 창업패키지 AI paste fields."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASTE_DIR = ROOT / "reports/kstartup_startup_package_ai_paste_ready"
OUT = ROOT / "reports/demo/kstartup_startup_package_ai_paste_assistant_v1.html"
META = ROOT / "reports/kstartup_startup_package_ai_paste_ready_latest.json"

LABELS = {
    "plan_01_summary_paste.txt": "1. 사업개요",
    "plan_02_market_problem_paste.txt": "2. 시장·문제인식",
    "plan_03_tech_roadmap_paste.txt": "3. 기술·추진계획",
    "plan_04_growth_funding_paste.txt": "4. 성장·자금",
    "plan_05_team_paste.txt": "5. 팀 역량",
    "plan_06_ai_talent_2p_paste.txt": "6. AI 인재 2p",
}


def main() -> int:
    if not META.is_file():
        raise SystemExit("Run build_kstartup_startup_package_ai_paste_ready_v1.py first")
    blocks: list[str] = []
    for fname, label in LABELS.items():
        path = PASTE_DIR / fname
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        tid = fname.replace(".", "_")
        esc = text.replace("&", "&amp;").replace("<", "&lt;")
        blocks.append(
            f'<section><h3>{label}</h3><pre id="{tid}">{esc}</pre>'
            f'<button type="button" onclick="copy(\'{tid}\')">복사</button></section>'
        )

    html = f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>창업패키지 AI 인재 실증형 Paste</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:760px;margin:24px auto;padding:0 16px;background:#0f1419;color:#e6edf3}}
h1{{font-size:1.25rem}} section{{margin:16px 0;padding:12px;border:1px solid #30363d;border-radius:8px}}
pre{{white-space:pre-wrap;background:#161b22;padding:10px;border-radius:6px;font-size:13px;max-height:320px;overflow:auto}}
button{{margin-top:8px;padding:8px 14px;background:#238636;color:#fff;border:0;border-radius:6px;cursor:pointer}}
.warn{{color:#f85149}} ol{{line-height:1.7}}
</style></head><body>
<h1>2026 창업패키지 · AI 인재 실증형 · 붙여넣기</h1>
<p class="warn">마감 2026-06-12 18:00 · 도약 · AI·빅데이터 · <strong>임시저장 후 육안</strong> · 제출완료는 대표자</p>
<ol>
<li><a href="https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do" target="_blank">모집중 공고</a> → AI 인재 실증형</li>
<li>트랙 도약 · 주관기관 1곳 · 별첨1 + AI 2p</li>
<li>AI 수료 인재 60일 채용 계획 필수</li>
</ol>
{"".join(blocks)}
<script>
function copy(id){{const t=document.getElementById(id).innerText;navigator.clipboard.writeText(t);}}
</script>
</body></html>"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(str(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
