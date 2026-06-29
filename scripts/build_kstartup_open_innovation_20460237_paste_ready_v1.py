#!/usr/bin/env python3
"""민관협력 오픈이노베이션 20460237 — K-Startup 일반현황 붙여넣기 팩.

SSOT: docs/final/artifacts/kstartup_oi_demand_task_intro_korea_eval_rpa_v1.json
격벽: OpenData 327 · 창업패키지 340 paste와 혼용 금지 (gate가 검증).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASTE_DIR = ROOT / "reports/kstartup_open_innovation_20460237_paste_ready"
HTML_OUT = ROOT / "reports/demo/kstartup_open_innovation_20460237_paste_assistant_v1.html"
CHECKLIST_OUT = ROOT / "docs/final/artifacts/open_innovation_2026_submission_checklist_v1_latest.json"
META_OUT = ROOT / "reports/kstartup_open_innovation_20460237_paste_build_latest.json"
DEMAND_INTRO = ROOT / "docs/final/artifacts/kstartup_oi_demand_task_intro_korea_eval_rpa_v1.json"

LOCK_VERSION = "v2.0-lock"


def _load_demand() -> dict:
    if not DEMAND_INTRO.is_file():
        raise SystemExit(f"missing demand intro SSOT: {DEMAND_INTRO}")
    return json.loads(DEMAND_INTRO.read_text(encoding="utf-8-sig"))


def build_fields(demand: dict | None = None) -> dict[str, str]:
    d = demand or _load_demand()
    company = d.get("demand_company") or "한국평가데이터"
    task_title = d.get("task_title") or "AI 기반 RPA를 활용한 수작업 업무 프로세스 자동화"
    subtitle = d.get("task_subtitle") or "기업정보 공개중지/정보정정 요청 프로세스 자동화"
    situation = d.get("situation") or ""
    problem = d.get("problem") or ""
    requirements = d.get("requirements") or []
    req_block = "\n".join(f"  {i + 1}) {r}" for i, r in enumerate(requirements))

    tsks_ctnt = (
        f"[협업과제 · {company}]\n"
        f"· 과제: {task_title}\n"
        f"· 세부: {subtitle}\n"
        f"· 현황: {situation}\n"
        f"· 문제점: {problem}\n\n"
        "[PoC 제안 — OCR·RPA·HOLD 게이트]\n"
        f"{req_block}\n\n"
        "FAX/스캔 서식 → OCR·필드 슬롯 → 추출값·근거 미연결 시 출력보류(HOLD)·감사로그 → "
        "담당자 최종 확인(Human Gold) 후만 고객관리 시스템·메일 반영. "
        "크레탑 검색·상담 메일 초안·VOC 통계는 시범 범위로 주간 리포트와 함께 검증. "
        "자동 제출·금융 심사 대체·수익 보장을 주장하지 않습니다."
    )

    tsks_short = (
        f"{company} {subtitle}: FAX→OCR→슬롯→HOLD→담당자 확인 후 반영. "
        "메일·VOC 시범. 자동 제출 없음."
    )
    if len(tsks_short) > 125:
        tsks_short = tsks_short[:122] + "…"

    return {
        "step4_tsksNm.txt": task_title,
        "step4_tsksCtnt.txt": tsks_ctnt,
        "step4_tsksCtnt_short_125.txt": tsks_short,
        "step2_majrProd.txt": "AI·RPA 업무 프로세스 자동화(OCR·슬롯·HOLD·Human Gold)",
        "step2_engNm.txt": "Moksori Network Inc.",
        "step2_hmpg.txt": "https://jema-ai.com",
        "oi_problem_3lines.txt": (
            "1) FAX 공개중지/정보정정 요청서 수기 판독·입력에 시간·오류 리스크가 큼.\n"
            "2) 크레탑 검색·상담 리포트 수기 작성으로 인력·응대 지연.\n"
            "3) 인입량·VOC 유형 등 운영 지표를 주간 단위로 분리 측정할 PoC 프레임 필요."
        ),
        "oi_poc_scope.txt": (
            "협약 8개월 PoC: (1) 현장·서식 샘플·필드 매핑 (2) OCR→슬롯→HOLD→(승인 후) 입력 연동 "
            "(3) 검색·메일 초안·VOC 리포트 시범 (4) 주간 비용·품질·운영 로그. "
            "성과는 조건·기간·범위를 함께 기록하며 절대 성과 표현은 사용하지 않습니다."
        ),
        "combo_hints.txt": (
            "지원분야: 지식서비스 · 수요기업: 한국평가데이터 · 협업과제: AI RPA\n"
            "전문기술: 정보통신 · ICT세부: 소프트웨어 (PMS 콤보는 화면 라벨에 맞게 선택)"
        ),
        "oi_tech_differentiation_v1_lock.txt": (
            "본 기술의 핵심 차별성은 검증 없는 ad-hoc AI 처리 대신, 수요기업 현업 서식·필드 규격을 "
            "사전 정형화하여 결합하는 'OCR·슬롯·출력 보류(HOLD) 가드레일' 아키텍처에 있습니다.\n\n"
            "첫째, 'FAX/스캔 서식 슬롯 매핑'을 적용합니다. 기업정보 공개중지·정보정정 요청 서식을 "
            "OCR로 데이터화하고, 고객별 관리 시스템 필드에 1:1 기계적 매핑하여 수기 입력 시간·오류를 줄입니다.\n\n"
            "둘째, '출처·필드 불확실성 HOLD 게이트'를 가동합니다. 추출값·검색 사유·메일 초안이 "
            "샘플 서식·DB 스키마·검증 로그와 연결되지 않으면 자동 반영 없이 HOLD하고 감사 로그에 적재합니다.\n\n"
            "셋째, '담당자 최종 확인(Human Gold)' 원칙을 고수합니다. 크레탑 검색·상담 메일 초안·VOC 통계는 "
            "담당자 승인 후에만 송부·반영합니다. 자동 제출·심사 대체를 주장하지 않습니다."
        ),
        "oi_risk_defense_v1_lock.txt": (
            "본 과제의 운영 리스크는 수요기업 현업 데이터·서식 변경과 OCR·RPA 파이프라인 지연으로 "
            "방어합니다.\n\n"
            "서식·필드 스키마 변경 시 매핑 버전을 분리 추적하고, 구형 서식 적용 여부를 진입 단계에서 "
            "검사해 조기 경보합니다.\n\n"
            "알고리즘 지연·추출 오류 시 무리한 자동 반영 대신 HOLD·주간 품질·비용·운영 리포트로 "
            "담당자에게 투명 제공합니다.\n\n"
            "성과 수치는 검증 로그·재현 가능한 벤치 코호트만 인용합니다. 자사 B2B 롱폼 문서 기준 "
            "spine 바이너리 청구 절감 약 22.29%, 34건 전건 바이트 일치 "
            "(SSOT: reports/path_a_spine_commercial_defense_fact_sheet_v1_latest.json) — "
            "연구용 latent·미검증 합성 샘플 지표와 합선하지 않습니다. "
            "PoC 범위 밖 자동화·수치 예언은 배제하고, 검증 로그 기반으로만 후속 고도화를 검토합니다."
        ),
    }


# Import-time FIELDS for gate import compatibility
FIELDS: dict[str, str] = build_fields()

LABELS = {
    "step4_tsksNm.txt": "STEP04 과제명 (#mf_wfm_contents_ibx_tsksNm)",
    "step4_tsksCtnt.txt": "STEP04 과제내용 (#mf_wfm_contents_ibx_tsksCtnt)",
    "step4_tsksCtnt_short_125.txt": "표준항목 요약 (~125자, ctnt)",
    "step2_majrProd.txt": "STEP02 주생산품목",
    "step2_engNm.txt": "STEP02 기업영문명",
    "step2_hmpg.txt": "STEP02 홈페이지",
    "oi_problem_3lines.txt": "OI 수요 통증 (참고·별도 칸 있을 때)",
    "oi_poc_scope.txt": "OI PoC 범위 (참고)",
    "combo_hints.txt": "콤보 선택 힌트",
    "oi_tech_differentiation_v1_lock.txt": "OI 기술적 차별성 v2.0-lock (PMS 별도 칸)",
    "oi_risk_defense_v1_lock.txt": "OI 리스크 방어 v2.0-lock (PMS 별도 칸)",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_html() -> None:
    blocks: list[str] = []
    for fname, label in LABELS.items():
        text = FIELDS[fname]
        n = len(text)
        label_with_count = f"{label} · {n}자"
        eid = "t_" + fname.replace(".", "_")
        esc = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        blocks.append(
            f'<section><h3>{label_with_count}</h3><pre id="{eid}">{esc}</pre>'
            f'<button type="button" onclick="copy(\'{eid}\')">복사</button></section>'
        )
    html = f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>OI 20460237 Paste</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>
@media print {{
  button {{ display: none; }}
  body {{ background: #fff; color: #111; }}
  section {{ break-inside: avoid; border-color: #ccc; }}
}}
:root {{
  --bg: #0a1210;
  --text: #e8ebe9;
  --muted: #9aa9a3;
  --accent: #3d9b84;
  --warn: #e8c88a;
  --line: rgba(255,255,255,0.08);
}}
* {{ box-sizing: border-box; }}
body {{
  font-family: "Pretendard Variable", Pretendard, system-ui, sans-serif;
  max-width: 780px;
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
ol {{ line-height: 1.65; padding-left: 1.2rem; }}
.warn {{ color: var(--warn); }}
.meta {{ color: var(--muted); font-size: 12px; }}
.deadline {{
  margin: 14px 0;
  padding: 10px 12px;
  border-left: 3px solid rgba(200,160,80,0.55);
  background: rgba(200,160,80,0.1);
  border-radius: 0 8px 8px 0;
  font-size: 13px;
}}
</style></head><body>
<h1>민관협력 오픈이노베이션 · 과제 <strong>20460237</strong> · 한국평가데이터 RPA</h1>
<p class="deadline">마감 <strong>6/15(일) 16:00 KST</strong> · <strong>임시저장→제출완료</strong>는 human only</p>
<p class="meta warn">격벽: OpenData 327·창업패키지 340 paste 복사 금지 · SSOT: 과제소개서 발췌 JSON</p>
<ol>
<li>PMS → 과제 <strong>20460237</strong> → <strong>수정</strong> (마감 전)</li>
<li>협업과제 = 한국평가데이터 · AI RPA 확인</li>
<li>STEP04 과제명·내용 = 본 팩 (정책자금 RAG 문구 아님)</li>
<li>붙임1 v4 HWP/PDF 첨부 후 임시저장·제출완료</li>
</ol>
<p class="meta">재빌드: <code>py scripts/build_kstartup_open_innovation_20460237_paste_ready_v1.py</code> · 게이트: <code>py scripts/check_kstartup_open_innovation_20460237_paste_gate_v1.py</code></p>
{''.join(blocks)}
<script>
function copy(id){{const t=document.getElementById(id).innerText;navigator.clipboard.writeText(t).then(()=>alert('복사됨'))}}
</script></body></html>"""
    HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    HTML_OUT.write_text(html, encoding="utf-8")


def _write_checklist() -> None:
    base: dict = {}
    if CHECKLIST_OUT.is_file():
        base = json.loads(CHECKLIST_OUT.read_text(encoding="utf-8-sig"))
    gates = dict(base.get("gates") or {})
    if (gates.get("G2_submitted") or {}).get("status") != "done":
        gates.setdefault("G0_portal_draft", {"label": "일반현황 초안 입력", "owner": "human", "status": "in_progress", "blocker": False})
    doc = {
        **base,
        "generated_at_utc": _utc(),
        "program": "민관협력 오픈이노베이션 2026",
        "pms_task_id": "20460237",
        "paste_pack_dir": "reports/kstartup_open_innovation_20460237_paste_ready",
        "paste_assistant_html": "reports/demo/kstartup_open_innovation_20460237_paste_assistant_v1.html",
        "build_script": "scripts/build_kstartup_open_innovation_20460237_paste_ready_v1.py",
        "ssot_refs": [
            "docs/final/artifacts/kstartup_oi_demand_task_intro_korea_eval_rpa_v1.json",
            "scripts/build_kstartup_open_innovation_20460237_paste_ready_v1.py",
        ],
        "paste_isolation": "OpenData327·StartupPackage340 paste 혼용 금지 — gate cross_program_forbidden",
        "verify_gate": "scripts/check_kstartup_open_innovation_20460237_paste_gate_v1.py",
        "lock_version": LOCK_VERSION,
        "lock_lengths": {
            "oi_tech_differentiation_v1_lock.txt": len(FIELDS["oi_tech_differentiation_v1_lock.txt"]),
            "oi_risk_defense_v1_lock.txt": len(FIELDS["oi_risk_defense_v1_lock.txt"]),
        },
        "gates": gates,
    }
    CHECKLIST_OUT.parent.mkdir(parents=True, exist_ok=True)
    CHECKLIST_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    global FIELDS
    FIELDS = build_fields()
    PASTE_DIR.mkdir(parents=True, exist_ok=True)
    for fname, text in FIELDS.items():
        (PASTE_DIR / fname).write_text(text, encoding="utf-8")
    _write_html()
    _write_checklist()
    meta = {
        "schema": "kstartup_open_innovation_20460237_paste_build_v1",
        "generated_at_utc": _utc(),
        "paste_dir": str(PASTE_DIR.resolve()),
        "html": str(HTML_OUT.resolve()),
        "checklist": str(CHECKLIST_OUT.resolve()),
        "field_count": len(FIELDS),
        "demand_intro_ssot": str(DEMAND_INTRO.relative_to(ROOT)).replace("\\", "/"),
        "tsksNm": FIELDS["step4_tsksNm.txt"],
        "tsksCtnt_len": len(FIELDS["step4_tsksCtnt.txt"]),
        "lock_version": LOCK_VERSION,
        "oi_tech_differentiation_len": len(FIELDS["oi_tech_differentiation_v1_lock.txt"]),
        "oi_risk_defense_len": len(FIELDS["oi_risk_defense_v1_lock.txt"]),
    }
    META_OUT.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, **meta}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
