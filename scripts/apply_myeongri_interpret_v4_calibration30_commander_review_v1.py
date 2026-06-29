#!/usr/bin/env python3
"""Apply commander-approved calibration30 human-review verdicts (B-track, research_only)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_SAMPLE = ROOT / "reports/myeongri_interpret_v4_human_review_calibration30_latest.json"
DEFAULT_STATUS = ROOT / "reports/myeongri_interpret_harness_v3_v4_status_latest.json"
DEFAULT_RADAR = ROOT / "reports/mkm_evolution_radar_daily_v1_latest.json"

# row_index -> (verdict, comment_ko)
COMMANDER_VERDICTS: dict[int, tuple[str, str]] = {
    97: ("pass", "병오·기해·계사·기미·일간 계 정합. '日' 표기만 경미 — pass."),
    96: ("needs_edit", "'정확한 해석' 과확신 표현 — 간지는 정합, wording만 완화 필요."),
    13: ("needs_edit", "기둥 라벨·순서 혼선(기미/임신·신해). guard448 population caveat 행 — 재서술 필요."),
    17: ("pass", "정축·을사·계유·계축 4주·일간 계 정합 — pass."),
    45: ("needs_edit", "시주(신축) 누락·3주만 서술 — coerce pass 아님."),
    19: ("pass", "신유·무술·임신·신해·일간 임 정합 — pass."),
    47: ("needs_edit", "시주(기사) 누락 — 3주만 서술."),
    61: ("needs_edit", "을사 일주를 '이르면'으로 오기·영문 혼용 — 수정 필요."),
    36: ("needs_edit", "시주(을해) 누락 — 3주만 서술."),
    79: ("needs_edit", "日紀/월기 혼용·시주 누락·'확실' 과확신 — needs_edit."),
    29: ("needs_edit", "4주 미열거·근거 빈약 — coerce-only 통과 아님."),
    35: ("pass", "기미·정축·정유·신해·일간 정 정합(간미→기미 표기만 경미)."),
    32: ("pass", "기사·신미·신미·정유·일간 신 정합 — pass."),
    63: ("needs_edit", "해인/생년 등 비표준 라벨·기둥 순서 혼선 — needs_edit."),
    72: ("pass", "갑진·병자·계묘·계축·일간 계 정합 — pass."),
    87: ("pass", "계해·갑인·을해·병자·일간 을 정합, 면책 tail 양호 — pass."),
    76: ("needs_edit", "시주(을미) 누락 — 3주만 서술."),
    14: ("needs_edit", "시주(갑자) 누락 — 3주만 서술."),
    15: ("needs_edit", "시주(을유) 누락 — 3주만 서술."),
    4: ("pass", "갑인·병인·을미·임오·일간 을 정합 — pass."),
    60: ("needs_edit", "시주(경인) 누락 — 3주만 서술."),
    44: ("needs_edit", "시주(경진) 누락 — 3주만 서술."),
    85: ("pass", "무인·정사·무인·기미·일간 무 정합 — pass."),
    95: ("pass", "경자·기축·을축·정해·일간 을 정합 — pass."),
    80: ("needs_edit", "품/날/해 등 비표준 용어 — 간지는 대체로 정합, wording needs_edit."),
    94: ("pass", "갑인·기사·병자·계사·일간 병 정합 — pass."),
    92: ("needs_edit", "'확정적' 과확신 — 4주 정합하나 wording 완화 필요."),
    25: ("needs_edit", "시주(정사) 누락 — 3주만 서술."),
    5: ("pass", "을해·갑신·계사·신유·일간 계 정합 — pass."),
    28: ("pass", "정사·갑진·갑인·(시 갑자 gold) — 3주 서술이나 phase1 pass 재확인, 연구 pass."),
}

BANNED_PRICE_MED = re.compile(r"(매수|매도|투자\s*추천|진단|처방|수술\s*필)", re.I)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mark_radar_approved(radar_path: Path, candidate_id: str) -> None:
    if not radar_path.is_file():
        return
    doc = json.loads(radar_path.read_text(encoding="utf-8-sig"))
    for c in doc.get("candidates") or []:
        if str(c.get("id")) == candidate_id:
            c["approval_status"] = "approved"
            c["approved_at_utc"] = _utc_now()
            c["approved_by"] = "commander_chat_2026-06-01"
    doc["generated_at_utc"] = _utc_now()
    radar_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample-json", type=Path, default=DEFAULT_SAMPLE)
    ap.add_argument("--status-json", type=Path, default=DEFAULT_STATUS)
    ap.add_argument("--radar-json", type=Path, default=DEFAULT_RADAR)
    ap.add_argument("--skip-radar-update", action="store_true")
    args = ap.parse_args()

    if not args.sample_json.is_file():
        print(f"missing: {args.sample_json}", file=sys.stderr)
        return 2

    doc = json.loads(args.sample_json.read_text(encoding="utf-8"))
    counts = {"pass": 0, "fail": 0, "needs_edit": 0}
    missing: list[int] = []

    for s in doc.get("samples") or []:
        ri = int(s["row_index"])
        entry = COMMANDER_VERDICTS.get(ri)
        if not entry:
            missing.append(ri)
            continue
        verdict, comment = entry
        insight = str(s.get("mkm_advanced_insight") or "")
        if BANNED_PRICE_MED.search(insight):
            verdict = "fail"
            comment = f"가격·의료 트리거 의심 — fail. 원안: {comment}"
        s["reviewer_verdict"] = verdict
        s["reviewer_verdict_source"] = "commander_v1_calibration30"
        s["reviewer_verdict_reason"] = "commander_approved_b_track_research_only"
        s["reviewer_comment"] = comment
        counts[verdict] += 1

    if missing:
        print(json.dumps({"ok": False, "missing_rows": missing}, ensure_ascii=False))
        return 1

    doc["human_verdict_counts"] = counts
    doc["human_verdict_applied_at_utc"] = _utc_now()
    doc["human_verdict_source"] = "apply_myeongri_interpret_v4_calibration30_commander_review_v1.py"
    doc["commander_signed_at_utc"] = doc["human_verdict_applied_at_utc"]
    doc["human_gate_pass"] = counts["fail"] == 0
    doc["calibration_gate_pass"] = counts["fail"] == 0 and counts["needs_edit"] <= 12

    policy = doc.setdefault("calibration_policy_v1", {})
    policy["pending_reviewer_verdict_count"] = 0
    policy["commander_signed_at_utc"] = doc["commander_signed_at_utc"]
    policy["human_verdict_counts"] = counts

    args.sample_json.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if args.status_json.is_file():
        status = json.loads(args.status_json.read_text(encoding="utf-8"))
        v4 = status.setdefault("v4_variant_sft", {})
        v4["human_review_calibration30"] = {
            "report": str(args.sample_json.relative_to(ROOT)).replace("\\", "/"),
            "human_verdict_counts": counts,
            "human_gate_pass": doc["human_gate_pass"],
            "calibration_gate_pass": doc["calibration_gate_pass"],
            "commander_signed_at_utc": doc["commander_signed_at_utc"],
            "interpretation_ko": (
                f"calibration30 지휘관 승인: pass={counts['pass']} "
                f"needs_edit={counts['needs_edit']} fail={counts['fail']}; B-track 연구용."
            ),
        }
        args.status_json.write_text(
            json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    if not args.skip_radar_update:
        _mark_radar_approved(args.radar_json, "myeongri_interpret_v4_calibration30_review")

    print(
        json.dumps(
            {
                "ok": True,
                "human_verdict_counts": counts,
                "human_gate_pass": doc["human_gate_pass"],
                "calibration_gate_pass": doc["calibration_gate_pass"],
                "sample": str(args.sample_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
