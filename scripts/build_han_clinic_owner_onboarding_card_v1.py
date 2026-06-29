#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build copy-paste HTML card for han clinic owner onboarding (Track C)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports" / "han_clinic_owner_onboarding"
OUT_HTML = ROOT / "reports" / "demo" / "han_clinic_owner_onboarding_card_v1.html"

BLOCKS: dict[str, str] = {
    "intro_kakao_280": (
        "MKM 한의원 보조 안내\n\n"
        "MKM은 사주로 병을 맞추는 AI가 아닙니다.\n"
        "① 진찰·변증·사상체질(코호트 근거) ② 출생·환경 역학(참고 변수) "
        "③ 만세력은 일정·페이싱 [HYPO] 사이드바만.\n"
        "임상 최종 판단은 원장님 4진·변증이 우선입니다."
    ),
    "dual_entry_kakao": (
        "【원장 0→1 · Dual-Entry · 2026-06-24】\n"
        "Entry A(기본): app.jema-ai.com/clinician · clinic.no1kmedi.com\n"
        "→ Git·터미널·IDE 불필요. SOAP·CDSS·care bundle. 원장 Human Gold 최종.\n"
        "Entry B(선택·research_only): 커스텀 실험만. PHI 금지·cohort_id 샌드박스.\n"
        "Replit 등 클라우드 IDE·외부호스팅: PHI·PII·결제정보 업로드 금지(법적·감사 리스크).\n"
        "→ 벤치 exit 0 ≠ 송출(SEND). SEND_GATE: HOLD."
    ),
    "entry_b_wedge_kakao": (
        "【Entry B · 파워유저 wedge · research_only】\n"
        "Replit·클라우드 IDE = 실험 샌드박스일 뿐, PHI·결제 호스팅 등급 아님.\n"
        "환자 차트·PII·결제정보 업로드 금지 — 법적·감사 리스크.\n"
        "대안: 로컬 Ollama + 익명 cohort_id·fixture만 · SEND_GATE: HOLD.\n"
        "체인: py scripts/run_han_clinic_owner_entry_b_onboarding_chain_v1.py"
    ),
    "axis_a_koges_3pmid": (
        "【A · 진찰 사상 · KoGES — L0/L1】\n"
        "· PMID 25411620 (n=2,460) TE vs SE 당뇨 RR=1.696, p=0.003\n"
        "· PMID 28865470 (n=3,529) MetS 예측 AUC=0.8173\n"
        "· PMID 19745018 (n=1,443) TE 당뇨 OR=3.96\n"
        "→ 코호트·체질별 위험 「참고」만. AI 진단·체질 확정 표현 금지."
    ),
    "axis_b_epi_3pmid": (
        "【B · 출생 역학 covariate — L2 · 사주≠】\n"
        "· PMID 31498065 (HIRA n≈1,724만) 출생월↔8종 류마티스 질환\n"
        "· PMID 27709859 (631만 출생) 조산 계절성\n"
        "· PMID 28064359 (46만) 출생 계절↔T2DM HR~1.08\n"
        "→ Gregorian 월·환경 변수. 만세력·오행과 동일시 금지."
    ),
    "axis_c_sidebar_disclaimer": (
        "【L3 · 만세력·사주 — 사이드바 [HYPO] only】\n"
        "PubMed 사주8자→질병 대규모 실증: 0건.\n"
        "Yang 2015 PMID 25837175 = 성격·대인(n=148)만 — 건강·처방 근거 금지.\n"
        "환자·원장 확인 전 참고용. 진단·체질·처방 게이트 없음."
    ),
    "forbidden_3lines": (
        "【대외 금지 3줄】\n"
        "1) 사주·AI로 체질·질병 진단/처방\n"
        "2) KoGES 사상 + 사주 오행 합성(「과학적 사주 체질 AI」)\n"
        "3) 근거 없는 ○○% 임상 정확도"
    ),
    "disclaimer_footer": (
        "면책: 본 도구·자료는 의료 진단·치료·처방을 대체하지 않습니다. "
        "불편 시 의료기관을 방문하십시오. "
        "SSOT: docs/final/artifacts/han_clinic_three_axis_evidence_index_v1_latest.md"
    ),
    "cta_pilot_1line": (
        "PoC 관심 시: 4진·체질 입력 형식·감사로그 샘플만 공유 가능합니다. "
        "실매매·자동 처방·사주 단정 기능은 제공하지 않습니다. [HYPO/research_only]"
    ),
    "loi_mmp_kakao_presell": (
        "【MKM · 신입 직무 Q&A 베타 · LOI pre-sell】\n"
        "(법무 검토 전 · ready_for_external_send: false)\n\n"
        "신입·실장 고시·원내 매뉴얼 Q&A — 근거 없으면 HOLD.\n"
        "진단·처방·청구 대체 아님 · EMR 무관.\n"
        "월 ₩79k(안) 또는 4주 무료 후 유료 — LOI 확정 전\n\n"
        "※ 임상 CDSS는 app.jema-ai.com/clinician (별 SKU)\n"
        "SSOT: reports/clinic_km_mmp_loi_one_pager_v1.md · SEND_GATE: HOLD"
    ),
}


def _html_block(block_id: str, title: str, text: str) -> str:
    safe_id = block_id.replace("-", "_")
    return (
        f'<section><h3>{title}</h3>'
        f'<pre id="t_{safe_id}">{text}</pre>'
        f'<button type="button" onclick="copy(\'t_{safe_id}\')">복사</button></section>'
    )


def build_html() -> str:
    sections = [
        ("intro_kakao_280", "카톡 인트로 (280자 내)", BLOCKS["intro_kakao_280"]),
        ("dual_entry_kakao", "Dual-Entry · 원장 0→1 (카톡)", BLOCKS["dual_entry_kakao"]),
        ("entry_b_wedge_kakao", "Entry B wedge · 클라우드 IDE (카톡)", BLOCKS["entry_b_wedge_kakao"]),
        ("axis_a_koges_3pmid", "A · KoGES 3 PMID", BLOCKS["axis_a_koges_3pmid"]),
        ("axis_b_epi_3pmid", "B · 출생 역학 3 PMID", BLOCKS["axis_b_epi_3pmid"]),
        ("axis_c_sidebar_disclaimer", "L3 · 사이드바 면책", BLOCKS["axis_c_sidebar_disclaimer"]),
        ("forbidden_3lines", "금지 3줄", BLOCKS["forbidden_3lines"]),
        ("disclaimer_footer", "면책 푸터", BLOCKS["disclaimer_footer"]),
        ("cta_pilot_1line", "PoC CTA 1줄", BLOCKS["cta_pilot_1line"]),
        ("loi_mmp_kakao_presell", "LOI MMP pre-sell (카톡)", BLOCKS["loi_mmp_kakao_presell"]),
    ]
    body_sections = "\n".join(_html_block(i, t, c) for i, t, c in sections)
    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>MKM 한의원 원장 온보딩</title>
<style>
@media print {{
  button {{ display: none; }}
  body {{ background: #fff; color: #000; max-width: 100%; }}
  section {{ break-inside: avoid; border-color: #ccc; }}
}}
body{{font-family:system-ui,sans-serif;max-width:720px;margin:24px auto;padding:0 16px;background:#0f1419;color:#e6edf3}}
h1{{font-size:1.2rem}} section{{margin:14px 0;padding:12px;border:1px solid #30363d;border-radius:8px}}
pre{{white-space:pre-wrap;background:#161b22;padding:10px;border-radius:6px;font-size:13px;line-height:1.5}}
button{{margin-top:8px;padding:8px 14px;background:#238636;color:#fff;border:0;border-radius:6px;cursor:pointer}}
.meta{{color:#8b949e;font-size:12px}} .ok{{color:#3fb950}} .warn{{color:#f85149}}
</style></head><body>
<h1>MKM 한의원 · 원장 온보딩 카드 (v1)</h1>
<p class="ok">Track C · A/B PMID 중심 · L3 사주=사이드바 [HYPO] only</p>
<p class="warn">법무·의료광고 검토 전 배포 금지 · Human Gold = 원장 4진·변증</p>
<p class="meta">SSOT: han_clinic_three_axis_evidence_index_v1_latest.md · 1p: han_clinic_owner_onboarding_brief_v1_latest.md</p>
<p class="meta">재빌드: <code>py scripts/build_han_clinic_owner_onboarding_card_v1.py</code></p>
{body_sections}
<script>
function copy(id){{const t=document.getElementById(id).innerText;navigator.clipboard.writeText(t).then(()=>alert('복사됨'))}}
</script></body></html>
"""


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    for name, text in BLOCKS.items():
        (OUT_DIR / f"{name}.txt").write_text(text + "\n", encoding="utf-8")
    OUT_HTML.write_text(build_html(), encoding="utf-8")
    print(f"OK: {OUT_HTML}")
    print(f"OK: {OUT_DIR} ({len(BLOCKS)} txt)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
