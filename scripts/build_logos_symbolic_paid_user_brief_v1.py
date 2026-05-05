#!/usr/bin/env python3
"""Build paid-user style brief from Logos signoff packet."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _pct(v: Any) -> float:
    try:
        return float(v) * 100.0
    except Exception:
        return 0.0


def _confidence(packet: dict[str, Any]) -> int:
    checks = packet.get("checks") if isinstance(packet.get("checks"), dict) else {}
    gate = packet.get("key_metrics", {}).get("gate_metrics_snapshot", {})
    score = 40
    score += 20 if checks.get("revalidation_ok") else 0
    score += 15 if checks.get("hygiene_ok") else 0
    score += 10 if checks.get("auto_bridge_locked") else 0
    score += 10 if checks.get("gate_human_approved") else 0
    hit = _pct(gate.get("hit_rate"))
    hold = _pct(gate.get("holdout_hit_rate"))
    if hit >= 95:
        score += 5
    if hold >= 90:
        score += 5
    return max(0, min(100, int(score)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--signoff-packet", type=Path, default=ART / "logos_symbolic_release_signoff_packet_latest.json")
    ap.add_argument("--stress-test-json", type=Path, default=ART / "logos_symbolic_paid_brief_stress_test_latest.json")
    ap.add_argument("--out-json", type=Path, default=ART / "logos_symbolic_paid_user_brief_latest.json")
    ap.add_argument("--out-md", type=Path, default=ART / "logos_symbolic_paid_user_brief_latest.md")
    args = ap.parse_args()

    packet = _load(Path(args.signoff_packet).resolve())
    stress = _load(Path(args.stress_test_json).resolve())
    summary = packet.get("summary") if isinstance(packet.get("summary"), dict) else {}
    checks = packet.get("checks") if isinstance(packet.get("checks"), dict) else {}
    gate = packet.get("key_metrics", {}).get("gate_metrics_snapshot", {})

    manual_gate = str(summary.get("recommended_manual_gate") or "HOLD_RESEARCH_ONLY")
    decision = "WATCH" if manual_gate == "GO_MANUAL_A_TRACK_GATE" else "HOLD"
    confidence = _confidence(packet)

    reasons = [
        f"검증 성과: hit_rate={_pct(gate.get('hit_rate')):.2f}%, holdout_hit_rate={_pct(gate.get('holdout_hit_rate')):.2f}%",
        f"실데이터 조건 충족: non_synthetic_n_evaluated={gate.get('non_synthetic_n_evaluated')}",
        f"운영 안전장치 유지: auto_bridge_locked={checks.get('auto_bridge_locked')}",
    ]
    counter_signals = [
        "외생 충격(유가/지정학/정책 급변) 구간에서는 패턴 기반 적중률이 단기 흔들릴 수 있음",
        "source별 편차(예: external_macro_signals 상대적 약세)는 주기적 재보정 필요",
    ]
    actions = [
        "지금: 자동 브리지 OFF 유지, 수동 게이트 결과만 반영",
        "오늘 밤: 제출 번들/원페이저 최신 해시 확인",
        "내일: 재검증 지표(revalidation/hygiene) 재확인 후 결재 유지 여부 판단",
    ]
    stress_summary = None
    if stress:
        ss = stress.get("summary") if isinstance(stress.get("summary"), dict) else {}
        stress_summary = (
            f"스트레스 테스트 {stress.get('status')} "
            f"(시나리오 {ss.get('scenario_count', 0)}건, fail {ss.get('fail_count', 0)}건)"
        )

    payload = {
        "schema": "logos_symbolic_paid_user_brief_v1",
        "generated_at_utc": _now(),
        "source_packet": str(Path(args.signoff_packet).resolve()).replace("\\", "/"),
        "source_stress_test": str(Path(args.stress_test_json).resolve()).replace("\\", "/"),
        "one_line_decision": {
            "action": decision,
            "manual_gate": manual_gate,
            "message_ko": (
                "지금은 자동 집행이 아니라 수동 게이트 기반 WATCH가 최적입니다."
                if decision == "WATCH"
                else "지금은 HOLD가 안전합니다."
            ),
        },
        "top_3_reasons": reasons,
        "counter_signals_2": counter_signals,
        "confidence_score_0_100": confidence,
        "action_guide": actions,
        "stress_test_one_liner": stress_summary,
    }

    out_json = Path(args.out_json).resolve()
    out_md = Path(args.out_md).resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# Logos Paid User Brief",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- confidence_score_0_100: `{confidence}`",
        "",
        "## 오늘 결론 1줄",
        f"- `{payload['one_line_decision']['message_ko']}`",
        "",
        "## 근거 3개",
        f"- {reasons[0]}",
        f"- {reasons[1]}",
        f"- {reasons[2]}",
        "",
        "## 스트레스 테스트 요약",
        f"- {stress_summary or '스트레스 테스트 요약 없음'}",
        "",
        "## 반례 2개",
        f"- {counter_signals[0]}",
        f"- {counter_signals[1]}",
        "",
        "## 행동 가이드",
        f"- {actions[0]}",
        f"- {actions[1]}",
        f"- {actions[2]}",
        "",
    ]
    out_md.write_text("\n".join(md_lines), encoding="utf-8")
    print(str(out_json))
    print(str(out_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

