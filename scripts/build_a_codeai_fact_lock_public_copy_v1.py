#!/usr/bin/env python3
"""Build Fact-Lock public copy for a-codeai.com from readiness + compression lane artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
READINESS_DEFAULT = ART / "pointerguard_ops_readiness_latest.json"
SCORECARD_DEFAULT = ART / "pointerguard_two_tier_perf_scorecard_latest.json"
TRACK_A_DEFAULT = ART / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
CONTRIBUTOR_DEFAULT = ART / "compression_contributor_promotion_candidate_v1_latest.json"
OUT_DEFAULT = ART / "a_codeai_fact_lock_public_copy_latest.json"

APPLY_URL = "https://app.jema-ai.com/enterprise/apply"
REPRODUCE_URL = "https://github.com/mkmlab-v2/a-codeai-compression-reproduce"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pct(rate: float | None, digits: int = 2) -> str:
    if rate is None:
        return "n/a"
    return f"{round(float(rate) * 100.0, digits):.{digits}f}"


def _lane_metrics(
    track_a: dict[str, Any],
    contributor: dict[str, Any],
) -> dict[str, str]:
    ta = track_a.get("compression_metrics", {}) if isinstance(track_a.get("compression_metrics"), dict) else {}
    if not ta and isinstance(track_a.get("aggregate"), dict):
        ta = track_a["aggregate"]
    cm = contributor.get("metrics", {}) if isinstance(contributor.get("metrics"), dict) else {}
    raw = cm.get("raw", {}) if isinstance(cm.get("raw"), dict) else {}
    cases_passed = int(cm.get("cases_passed", 0) or 0)
    row_count = int(cm.get("row_count", 0) or raw.get("rows", 0) or 0)
    return {
        "track_a_saving_pct": _pct(ta.get("global_token_saving_rate"), 2),
        "track_a_min_jaccard": f"{float(ta.get('min_reconstruction_fidelity_jaccard', 0) or 0):.3f}",
        "contributor_saving_pct": _pct(cm.get("mean_token_saving_rate_proxy"), 1),
        "contributor_raw_alignment_pct": _pct(raw.get("alignment_pass_rate"), 1),
        "contributor_pass_fraction": f"{cases_passed}/{row_count}" if row_count else "n/a",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--readiness-json", type=Path, default=READINESS_DEFAULT)
    ap.add_argument("--scorecard-json", type=Path, default=SCORECARD_DEFAULT)
    ap.add_argument("--track-a-json", type=Path, default=TRACK_A_DEFAULT)
    ap.add_argument("--contributor-json", type=Path, default=CONTRIBUTOR_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    readiness_path = args.readiness_json if args.readiness_json.is_absolute() else ROOT / args.readiness_json
    scorecard_path = args.scorecard_json if args.scorecard_json.is_absolute() else ROOT / args.scorecard_json
    track_a_path = args.track_a_json if args.track_a_json.is_absolute() else ROOT / args.track_a_json
    contributor_path = args.contributor_json if args.contributor_json.is_absolute() else ROOT / args.contributor_json
    out_path = args.out if args.out.is_absolute() else ROOT / args.out

    readiness = _read_json(readiness_path) if readiness_path.exists() else {}
    scorecard = _read_json(scorecard_path) if scorecard_path.exists() else {}
    track_a = _read_json(track_a_path) if track_a_path.exists() else {}
    contributor = _read_json(contributor_path) if contributor_path.exists() else {}

    readiness_all_ok = bool(readiness.get("all_ok", False))
    executive_read = str(scorecard.get("executive_read", {}).get("decision", "CONTROLLED_BETA_ONLY"))
    lanes = _lane_metrics(track_a, contributor)

    hero = "A-CODEAI Open Bench (Controlled Beta + Waitlist)"
    subtitle = (
        "Measured compression gains are published with reproducible evidence, "
        "while SEND_GATE remains HOLD and onboarding stays waitlist-first."
    )
    status_line = (
        "Current status: controlled beta waitlist; SEND_GATE=HOLD."
        if readiness_all_ok
        else "Current status: readiness gate is not green; public claims are restricted; SEND_GATE=HOLD."
    )

    bullets = [
        "Fact-Lock only: every headline is backed by reproducible artifacts and CI checks.",
        (
            f"Track A active codec benchmark is {lanes['track_a_saving_pct']}% token saving "
            f"with min jaccard {lanes['track_a_min_jaccard']} (separate lane)."
        ),
        (
            f"Contributor open-bench lane reports {lanes['contributor_saving_pct']}% saving with "
            f"raw alignment pass {lanes['contributor_raw_alignment_pct']}% "
            f"({lanes['contributor_pass_fraction']})."
        ),
        "Public benchmark uses synthetic/anonymized scope only; no customer corpus or secrets are exposed.",
        "SEND_GATE remains HOLD: no broad outbound campaign or customer-case headline rollout.",
    ]

    claims = [
        {
            "title": "What we claim",
            "items": [
                "Conditional cost and latency improvement in validated operating zones.",
                "Automatic safety fallback (HOLD/track_a_primary) when readiness or health checks fail.",
                "Operational transparency via timestamped benchmark, readiness, and signoff artifacts.",
                "Waitlist-first onboarding for scoped B2B pilots.",
            ],
        },
        {
            "title": "What we do not claim",
            "items": [
                "No unconditional global performance guarantee.",
                "No claim that all workloads receive equal benefit.",
                "No exposure of private corpora, secrets, or internal codebook internals.",
                "No mixing of Track A active metrics and contributor benchmark metrics into one headline.",
            ],
        },
    ]

    cta = {
        "label": "Join Waitlist for Controlled Beta",
        "note": (
            "Pilot onboarding is waitlist-first and limited to scoped B2B workloads with "
            "monitoring, guardrail acceptance, and SEND_GATE HOLD compliance."
        ),
        "apply_href": APPLY_URL,
        "reproduce_href": REPRODUCE_URL,
    }

    copy_ko = {
        "hero": "A-CODEAI Open Bench (Controlled Beta + 대기명단)",
        "subtitle": (
            "측정된 압축 성능은 재현 가능한 근거와 함께 공개하며, SEND_GATE는 HOLD를 유지하고 "
            "온보딩은 대기명단 우선으로 운영합니다."
        ),
        "status_line": (
            "상태: Controlled beta waitlist · SEND_GATE=HOLD"
            if readiness_all_ok
            else "상태: readiness 미충족 — 공개 주장 제한 · SEND_GATE=HOLD"
        ),
        "bullets": [
            "Fact-Lock: 모든 헤드라인은 재현 가능한 아티팩트와 CI 검증에 기반합니다.",
            (
                f"Track A active 코덱 벤치: 토큰 절감 {lanes['track_a_saving_pct']}%, "
                f"최소 jaccard {lanes['track_a_min_jaccard']} (분리 레인)."
            ),
            (
                f"Contributor open-bench 레인: 절감 {lanes['contributor_saving_pct']}%, "
                f"raw alignment pass {lanes['contributor_raw_alignment_pct']}% "
                f"({lanes['contributor_pass_fraction']})."
            ),
            "공개 벤치는 합성·익명 범위만 사용하며 고객 코퍼스·비밀은 노출하지 않습니다.",
            "SEND_GATE HOLD: 대량 아웃바운드·고객사례 헤드라인 롤아웃 없음.",
        ],
        "claims": [
            "검증된 운영 구간에서만 조건부 비용·지연 개선을 주장합니다.",
            "readiness/health 미충족 시 HOLD/track_a_primary로 자동 강등됩니다.",
            "벤치·readiness·signoff 아티팩트를 타임스탬프와 함께 공개합니다.",
            "Controlled beta 온보딩은 범위 한정 B2B 파일럿 대기명단으로만 진행합니다.",
        ],
        "non_claims": [
            "무조건적 전역 성능 보장을 주장하지 않습니다.",
            "모든 워크로드에 동일한 이득이 있다고 주장하지 않습니다.",
            "비공개 코퍼스·비밀·내부 코드북을 노출하지 않습니다.",
            "Track A active 지표와 contributor 벤치 지표를 하나의 헤드라인으로 합치지 않습니다.",
        ],
        "cta": {
            "label": "Controlled Beta 대기명단 신청",
            "note": (
                "온보딩은 waitlist-first이며, 모니터링·가드레일 수락 및 SEND_GATE HOLD 준수 "
                "범위에서만 진행합니다."
            ),
            "apply_href": APPLY_URL,
            "reproduce_href": REPRODUCE_URL,
        },
    }

    out_doc = {
        "schema": "a_codeai_fact_lock_public_copy_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "readiness_json": str(readiness_path),
            "scorecard_json": str(scorecard_path),
            "track_a_json": str(track_a_path),
            "contributor_json": str(contributor_path),
        },
        "status": {
            "readiness_all_ok": readiness_all_ok,
            "executive_read_decision": executive_read,
            "send_gate": "HOLD",
        },
        "lane_metrics": lanes,
        "copy": {
            "hero": hero,
            "subtitle": subtitle,
            "status_line": status_line,
            "bullets": bullets,
            "claims": claims,
            "cta": cta,
        },
        "copy_ko": copy_ko,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "out": str(out_path), "readiness_all_ok": readiness_all_ok, "lanes": lanes},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
