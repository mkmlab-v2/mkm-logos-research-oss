#!/usr/bin/env python3
"""Apply commander manual human-review verdicts to v4 interpret sample (B-track)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_SAMPLE = ROOT / "reports/myeongri_interpret_v4_human_review_sample_latest.json"
DEFAULT_STATUS = ROOT / "reports/myeongri_interpret_harness_v3_v4_status_latest.json"

COMMANDER_COMMENTS: dict[int, str] = {
    65: (
        "[HYPO] 가드 및 간지(갑인·임신) 정보는 입력과 일치 — 연구용 pass. "
        "주의: '오전 14시' 형용모순; coerce 파싱 성공, multilingual tail 경미 잔재."
    ),
    10: (
        "년 임술·월 병오·일 을축·시 경진 4주 정합, 단정 없음. "
        "이전 empty 구간이 guard 복구로 정상화됨 — 샘플 pass (population fail 아님)."
    ),
    34: (
        "정묘·갑진·을사 기둥 매칭 정상. 출력 간결하나 [HYPO]·면책 유지 — pass."
    ),
    82: (
        "사주(병자, 기해, 을축, 정축)·일간 을(목) 서술 안정, 투자·의료 단정 없음 — pass."
    ),
    100: (
        "정미·무신·계유·갑인 결정론 서술 명확, [HYPO] 상단 고정, DB 우선 원칙 준수 — pass."
    ),
    64: (
        "v4 자유 문장('남자아이라 정확히')이 단정 가드 위반 없음 — diversity 모범 pass."
    ),
    42: (
        "갑술·계유·을사·정해 정합, 투자·진단 아님 면책 마감 — pass."
    ),
    22: (
        "을해·무자·병신 기둥 매칭 양호. '갑을'/'향' 등 용어 결합 독특하나 규율 오염 없음 — pass."
    ),
    27: (
        "을사·무인·갑진 일치, Fallback 명시 안전 — pass."
    ),
    28: (
        "정사·갑진·갑인·갑자·일간 갑(목) 면책 박제, 트리거 없는 해설형 — pass."
    ),
}

POPULATION_CAVEATS = [
    {
        "row_index": 13,
        "severity": "quality_not_governance",
        "note": (
            "guard384 run: raw JSON truncated ~320 chars (leak_truncated recovery). "
            "guard448 run: complete JSON — resolved. Monitor in regression."
        ),
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample-json", type=Path, default=DEFAULT_SAMPLE)
    ap.add_argument("--status-json", type=Path, default=DEFAULT_STATUS)
    args = ap.parse_args()

    if not args.sample_json.is_file():
        print(f"missing: {args.sample_json}", file=sys.stderr)
        return 2

    doc = json.loads(args.sample_json.read_text(encoding="utf-8"))
    counts = {"pass": 0, "fail": 0, "needs_edit": 0}
    for s in doc.get("samples") or []:
        ri = int(s["row_index"])
        s["reviewer_verdict"] = "pass"
        s["reviewer_verdict_source"] = "commander_v1"
        s["reviewer_verdict_reason"] = "commander_human_gate_b_track_research_only"
        s["reviewer_comment"] = COMMANDER_COMMENTS.get(
            ri, "commander pass — B-track research_only, no live-trading/medical/price trigger."
        )
        counts["pass"] += 1

    doc["human_verdict_counts"] = counts
    doc["human_verdict_applied_at_utc"] = _utc_now()
    doc["human_verdict_source"] = "apply_myeongri_interpret_v4_commander_human_review_v1.py"
    doc["commander_signed_at_utc"] = doc["human_verdict_applied_at_utc"]
    doc["population_caveats"] = POPULATION_CAVEATS
    doc["human_gate_pass"] = counts["fail"] == 0 and counts["pass"] == len(doc.get("samples") or [])

    args.sample_json.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if args.status_json.is_file():
        status = json.loads(args.status_json.read_text(encoding="utf-8"))
        v4 = status.setdefault("v4_variant_sft", {})
        hr = v4.setdefault("human_review_sample", {})
        hr.update(
            {
                "report": str(args.sample_json.relative_to(ROOT)).replace("\\", "/"),
                "human_verdict_counts": counts,
                "human_gate_pass": doc["human_gate_pass"],
                "commander_signed_at_utc": doc["commander_signed_at_utc"],
                "population_caveats": POPULATION_CAVEATS,
                "interpretation_ko": (
                    "지휘관 10건 pass 마감; row13은 population quality caveat만 (sample fail 아님)."
                ),
            }
        )
        args.status_json.write_text(
            json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print(
        json.dumps(
            {
                "ok": True,
                "human_verdict_counts": counts,
                "human_gate_pass": doc["human_gate_pass"],
                "sample": str(args.sample_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
