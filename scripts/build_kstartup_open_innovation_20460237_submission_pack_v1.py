#!/usr/bin/env python3
"""OI 20460237 submission pack — 사업계획서 + 과제소개서 발췌 + 체크리스트 (Downloads)."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = ROOT / "docs/final/artifacts/open_innovation_2026_submission_checklist_v1_latest.json"
DEMAND_JSON = ROOT / "docs/final/artifacts/kstartup_oi_demand_task_intro_korea_eval_rpa_v1.json"
DEMAND_TXT = ROOT / "reports/kstartup_open_innovation_20460237_demand_korea_eval_rpa_intro_v1.txt"
FILLED_HWP = ROOT / "reports/kstartup_open_innovation_20460237_filled_v4.hwp"
FILLED_HWPX = ROOT / "reports/kstartup_open_innovation_20460237_filled_v4.hwpx"
FILLED_PDF = ROOT / "reports/kstartup_open_innovation_20460237_filled_v4.pdf"
DEFAULT_OUT = ROOT / "reports/kstartup_open_innovation_20460237_submission_pack_latest.json"

DL_DIR = Path.home() / "Downloads/OI20460237_제출패키지"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _copy(src: Path, dst: Path) -> dict:
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(src, dst)
    except PermissionError:
        alt = dst.with_name(f"{dst.stem}_v3{dst.suffix}")
        shutil.copy2(src, alt)
        dst = alt
    return {
        "src": str(src),
        "dst": str(dst),
        "size_bytes": dst.stat().st_size,
        "sha256": _sha256(dst),
    }


def build_pack(
    *,
    hwp: Path,
    hwpx: Path,
    pdf: Path | None,
) -> dict:
    DL_DIR.mkdir(parents=True, exist_ok=True)
    copies: list[dict] = []

    if hwp.is_file():
        copies.append(_copy(hwp, DL_DIR / "01_붙임1_사업계획서_목소리네트워크.hwp"))
        copies.append(_copy(hwp, Path.home() / "Downloads/OI20460237_붙임1_사업계획서_목소리_제출용.hwp"))
    if hwpx.is_file():
        copies.append(_copy(hwpx, DL_DIR / "01_붙임1_사업계획서_목소리네트워크.hwpx"))
        copies.append(_copy(hwpx, Path.home() / "Downloads/OI20460237_붙임1_사업계획서_목소리_채움본.hwpx"))
    if pdf and pdf.is_file():
        copies.append(_copy(pdf, DL_DIR / "01_붙임1_사업계획서_목소리네트워크.pdf"))
        copies.append(_copy(pdf, Path.home() / "Downloads/OI20460237_붙임1_사업계획서_목소리_제출용.pdf"))

    if DEMAND_TXT.is_file():
        copies.append(_copy(DEMAND_TXT, DL_DIR / "00_참고_수요기업_과제소개서_한국평가데이터_RPA_발췌.txt"))
    if DEMAND_JSON.is_file():
        copies.append(_copy(DEMAND_JSON, DL_DIR / "00_참고_수요기업_과제소개서_한국평가데이터_RPA.json"))

    checklist_text = """OI 20460237 제출 체크리스트 (human)
================================
[온라인 — PMS]
□ 사업신청서(일반현황) 임시저장·최종 확인
□ 협업과제: 한국평가데이터 · AI 기반 RPA 수작업 자동화 (공고·PMS 일치)
□ 제출완료 버튼 (6/15 16:00 전) — 에이전트 자동 제출 없음

[첨부 — 붙임1 사업계획서]
□ 01_붙임1_사업계획서_목소리네트워크.hwp (또는 PDF) PMS 업로드 (30MB 이내)
□ Hancom: ※ 파란 안내 문구 삭제 · 생년월일·연락처·법인등록번호·인력표 확인

[증빙 — 공고·매뉴얼 기준 human]
□ 창업기업 확인서 등 (해당 시)
□ ESG 자가진단 (해당 시)
□ 공공마이데이터 동의 여부 확인

SEND_GATE: HOLD — 제출 전 지휘관 최종 검토
"""
    checklist_path = DL_DIR / "02_제출체크리스트.txt"
    checklist_path.write_text(checklist_text, encoding="utf-8")
    copies.append({"dst": str(checklist_path), "kind": "generated_checklist"})

    pack = {
        "schema": "kstartup_open_innovation_20460237_submission_pack_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "program": "민관협력 오픈이노베이션 2026",
        "pms_task_id": "20460237",
        "deadline_kst": "2026-06-15T16:00:00+09:00",
        "downloads_pack_dir": str(DL_DIR),
        "artifacts": {
            "business_plan_hwp": str(hwp.relative_to(ROOT)).replace("\\", "/") if hwp.is_file() else "",
            "business_plan_hwpx": str(hwpx.relative_to(ROOT)).replace("\\", "/") if hwpx.is_file() else "",
            "business_plan_pdf": str(pdf.relative_to(ROOT)).replace("\\", "/") if pdf and pdf.is_file() else "",
            "demand_intro_json": str(DEMAND_JSON.relative_to(ROOT)).replace("\\", "/") if DEMAND_JSON.is_file() else "",
            "checklist_ssot": str(CHECKLIST.relative_to(ROOT)).replace("\\", "/") if CHECKLIST.is_file() else "",
        },
        "copies": copies,
        "human_verify": [
            "생년월일·연락처·법인등록번호·인력표",
            "기업현황요약(table54) 매출·협업실적·사진",
            "※ 안내 문구 삭제",
            "PMS 협업과제명·수요기업명 = 과제소개서 발췌와 일치",
            "제출완료 = human only",
        ],
        "boundary_ack": "Pack is draft; selection not implied.",
        "repro": "py scripts/run_kstartup_open_innovation_20460237_submission_complete_v1.py",
    }
    return pack


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hwp", type=Path, default=FILLED_HWP)
    ap.add_argument("--hwpx", type=Path, default=FILLED_HWPX)
    ap.add_argument("--pdf", type=Path, default=FILLED_PDF)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    pdf = args.pdf if args.pdf.is_file() else None
    pack = build_pack(hwp=args.hwp.resolve() if args.hwp.is_file() else Path(), hwpx=args.hwpx.resolve(), pdf=pdf)
    pack["ok"] = bool(args.hwpx.is_file())
    args.out.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _sync_checklist(pack)
    print(json.dumps({"ok": pack["ok"], "downloads_pack_dir": pack["downloads_pack_dir"], "copies": len(pack["copies"])}, ensure_ascii=False))
    return 0 if pack["ok"] else 1


def _sync_checklist(pack: dict) -> None:
    checklist_path = ROOT / "docs/final/artifacts/open_innovation_2026_submission_checklist_v1_latest.json"
    base: dict = {}
    if checklist_path.is_file():
        base = json.loads(checklist_path.read_text(encoding="utf-8-sig"))
    gates = dict(base.get("gates") or {})
    arts = pack.get("artifacts") or {}
    gates["G3_business_plan_hwp"] = {
        "label": "붙임1 사업계획서 HWP/PDF (v4 · OI 전용 SSOT · table54)",
        "owner": "human",
        "status": "draft_ready",
        "blocker": False,
    }
    updated = {
        **base,
        "generated_at_utc": pack.get("generated_at_utc", _utc()),
        "submission_pack_dir": pack.get("downloads_pack_dir"),
        "submission_complete_meta": "reports/kstartup_open_innovation_20460237_submission_complete_latest.json",
        "demand_intro_ssot": "docs/final/artifacts/kstartup_oi_demand_task_intro_korea_eval_rpa_v1.json",
        "submission_repro": "py scripts/run_kstartup_open_innovation_20460237_submission_complete_v1.py",
        "company_summary_paste": "reports/kstartup_open_innovation_20460237_paste_ready/company_summary_table54_paste.txt",
        "collab_task": {
            "demand_company": "한국평가데이터",
            "task_name": "AI 기반 RPA를 활용한 수작업 업무 프로세스 자동화",
        },
        "artifacts": {
            **(base.get("artifacts") or {}),
            "business_plan_hwp": arts.get("business_plan_hwp", ""),
            "business_plan_hwpx": arts.get("business_plan_hwpx", ""),
            "business_plan_pdf": arts.get("business_plan_pdf", ""),
            "downloads_pack": "Downloads/OI20460237_제출패키지",
        },
        "gates": gates,
    }
    checklist_path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
