"""OpenData 327 K-Startup BMO0801 paste assistant (local HTML)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "demo" / "kstartup_opendata327_paste_assistant_v1.html"
PASTE_DIR = ROOT / "reports" / "kstartup_opendata327_paste_ready"

FIELDS = {
    "step4_tsksNm.txt": "과제명 (STEP04)",
    "step4_tsksCtnt.txt": "과제내용 (STEP04)",
    "step2_majrProd.txt": "주생산품목 (STEP02)",
    "step2_engNm.txt": "기업영문명 (STEP02)",
    "step2_hmpg.txt": "홈페이지 (STEP02)",
}

DEFAULTS = {
    "step4_tsksNm.txt": "정책자금 융자 신청서 자동 초안 생성(RAG·근거연동·출력보류)",
    "step4_tsksCtnt.txt": (
        "중진공 정책자금 신청은 규정 준수 문서로, 범용 폼 매핑이 아닌 "
        "공고·서식·예시(OpenData) 버전 인덱싱 → RAG·슬롯 생성 → "
        "근거 미연결 HOLD·재질의·감사로그 → 담당자 최종 확인 후 "
        "PDF(hwp 단계적) 산출. AI 자동 제출 없음."
    ),
    "step2_majrProd.txt": "정책자금 신청서 자동 초안 생성 AI(RAG·근거연동·출력보류 게이트)",
    "step2_engNm.txt": "Moksori Network Inc.",
    "step2_hmpg.txt": "https://jema-ai.com",
}


def main() -> int:
    PASTE_DIR.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    for fname, label in FIELDS.items():
        path = PASTE_DIR / fname
        if not path.exists():
            path.write_text(DEFAULTS[fname], encoding="utf-8")

    blocks = []
    for fname, label in FIELDS.items():
        text = (PASTE_DIR / fname).read_text(encoding="utf-8")
        esc = text.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
        blocks.append(
            f"""<section><h3>{label}</h3>
<pre id="t_{fname.replace('.','_')}">{text}</pre>
<button type="button" onclick="copy('t_{fname.replace('.','_')}')">복사</button></section>"""
        )

    html = f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>OpenData327 K-Startup Paste</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:720px;margin:24px auto;padding:0 16px;background:#0f1419;color:#e6edf3}}
h1{{font-size:1.25rem}} section{{margin:16px 0;padding:12px;border:1px solid #30363d;border-radius:8px}}
pre{{white-space:pre-wrap;background:#161b22;padding:10px;border-radius:6px;font-size:13px}}
button{{margin-top:8px;padding:8px 14px;background:#238636;color:#fff;border:0;border-radius:6px;cursor:pointer}}
ol{{line-height:1.6}} .warn{{color:#f85149}}
</style></head><body>
<h1>OpenData 327 · 과제 20460495 · PMS 붙여넣기</h1>
<p class="warn">실제 과제 <strong>20460495</strong>만 · 모의공고(20460558) 아님 · <strong>임시저장</strong>만</p>
<ol>
<li>Chrome: 사업신청내역 → 20460495 → 수정하기</li>
<li>STEP02: 인증완료 · 대표자 이기륜 · 아래 STEP02 복사</li>
<li>STEP04 일반현황: 과제명·과제내용 · 지원분야 <strong>지식서비스</strong> · 지역 <strong>경기</strong></li>
<li>콤보: 전문기술 <strong>정보통신</strong> · 세부 <strong>소프트웨어</strong></li>
</ol>
{''.join(blocks)}
<script>
function copy(id){{const t=document.getElementById(id).innerText;navigator.clipboard.writeText(t).then(()=>alert('복사됨'))}}
</script></body></html>"""
    OUT.write_text(html, encoding="utf-8")
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
