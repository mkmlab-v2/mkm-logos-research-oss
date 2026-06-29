"""BMO0902 첨부 업로드 보조 HTML (OpenData 327 · 20460495)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "demo" / "kstartup_opendata327_bmo0902_upload_assistant_v1.html"

PLAN = ROOT / "reports/moksori_ai_opendata327_task1_business_plan_v1.pdf"
MERGED = ROOT / "reports/opendata_327_submission_bcd_merged_v1.pdf"


def main() -> int:
    plan = str(PLAN) if PLAN.is_file() else "(없음 — Run-OpenData327SubmissionPrep_v1.ps1)"
    merged = str(MERGED) if MERGED.is_file() else plan
    html = f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>OpenData327 BMO0902 업로드</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:760px;margin:24px auto;padding:0 16px;background:#0f1419;color:#e6edf3}}
h1{{font-size:1.2rem}} .warn{{color:#f85149}} code{{background:#161b22;padding:2px 6px;border-radius:4px}}
button{{padding:8px 14px;background:#238636;color:#fff;border:0;border-radius:6px;cursor:pointer;margin:4px 4px 0 0}}
ol{{line-height:1.7}} li{{margin:8px 0}}
</style></head><body>
<h1>OpenData 327 · BMO0902 첨부 (과제 20460495)</h1>
<p class="warn">제출완료 버튼은 누르지 마세요. 임시저장만.</p>
<ol>
<li>실공고 <strong>20460495</strong> · 모의공고 배너 없음 확인</li>
<li><strong>T1069 사업계획서</strong> → 파일추가 → 아래 PDF</li>
<li><strong>T1279 사업자등록증</strong> → 파일추가 → 지휘관 보유 PDF</li>
<li>임시저장</li>
</ol>
<p><strong>사업계획서 (1차):</strong><br><code id="p1">{plan}</code>
<button type="button" onclick="copy('p1')">경로 복사</button></p>
<p><strong>병합본 (표지 A 넣은 후):</strong><br><code id="p2">{merged}</code>
<button type="button" onclick="copy('p2')">경로 복사</button></p>
<p>자동 업로드(CDP): Chrome <strong>전부 종료</strong> 후<br>
<code>powershell -File scripts/Run-KstartupOpenData327Bmo0902Autofill_v1.ps1 -UseDefaultProfile</code></p>
<script>
function copy(id){{navigator.clipboard.writeText(document.getElementById(id).innerText).then(()=>alert('복사됨'))}}
</script></body></html>"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
