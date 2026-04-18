#!/usr/bin/env python3
"""Build slide-ready briefing bullets (KO/EN) from snapshot + bridge-by-mode artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_SNAPSHOT = ART / "DEFENSE_BENCH_SNAPSHOT_TABLE_V1.json"
DEFAULT_BY_MODE = ART / "MULTILENS_BRIDGE_POLICY_AB_BY_MODE_V1.json"
DEFAULT_OUT = ART / "DEFENSE_BENCH_BRIEFING_BULLETS_V1.json"


def _load(p: Path) -> dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build DEFENSE_BENCH_BRIEFING_BULLETS_V1.json")
    ap.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    ap.add_argument("--by-mode", type=Path, default=DEFAULT_BY_MODE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    snap = _load(args.snapshot)
    bym = _load(args.by_mode) if args.by_mode.is_file() else {}

    rows = {r["lane"]: r for r in snap.get("rows") or []}
    ta = rows.get("track_a_universal") or {}
    hy = rows.get("defense_hybrid_uav_synthetic") or {}
    modes = (bym.get("modes") or {}) if bym else {}
    uni = modes.get("universal") or {}
    u_off = (uni.get("bridge_off") or {}).get("compression_metrics_summary") or {}
    u_on = (uni.get("bridge_on") or {}).get("compression_metrics_summary") or {}
    ul = modes.get("ultra_literal") or {}
    ul_off = (ul.get("bridge_off") or {}).get("compression_metrics_summary") or {}
    ul_on = (ul.get("bridge_on") or {}).get("compression_metrics_summary") or {}

    def _pct(x: Any) -> str:
        if x is None:
            return "—"
        return f"{float(x) * 100:.1f}%"

    bullets_ko = [
        f"Track A(범용, V2 고정 입력): 글로벌 토큰 절감 {_pct(ta.get('global_token_saving_rate'))}, 평균 Jaccard {float(ta.get('avg_reconstruction_fidelity_jaccard') or 0):.3f} — `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`.",
        f"합성 UAV 하이브리드: 필수 필드 완전성 {hy.get('critical_field_integrity')}, 평균 페이로드 압축비율(바이트) {_pct(hy.get('mean_payload_compression_ratio'))}, 같은 벤치의 토큰 절감 {_pct(hy.get('global_token_saving_rate'))} — 바이트와 토큰을 한 문장에 섞지 말 것.",
        (
            f"브리지 정책 A/B(universal): OFF 절감 {_pct(u_off.get('global_token_saving_rate'))}·Jaccard {float(u_off.get('avg_reconstruction_fidelity_jaccard') or 0):.3f} "
            f"vs ON 절감 {_pct(u_on.get('global_token_saving_rate'))}·Jaccard {float(u_on.get('avg_reconstruction_fidelity_jaccard') or 0):.3f} — 동일 입력에서 트레이드오프 관측."
            if u_off and u_on
            else "브리지 모드별 요약: `MULTILENS_BRIDGE_POLICY_AB_BY_MODE_V1.json` 참조."
        ),
        (
            f"동일 벤치 ultra-literal: 브리지 OFF/ON 절감 {_pct(ul_off.get('global_token_saving_rate'))} / {_pct(ul_on.get('global_token_saving_rate'))}, Jaccard 동일 대 — 초저캡 레인에서는 브리지 효과가 작게 보일 수 있음."
            if ul_off and ul_on
            else "ultra-literal 브리지 페어: `MULTILENS_BRIDGE_POLICY_AB_V1.json`."
        ),
        "대외 수치는 `defense_code_pack_v1.json`·위 artifact 경로를 인용하고, NotebookLM·내부 브리핑 서사와 혼동 금지.",
    ]

    bullets_en = [
        f"Track A universal (V2 fixed input): global token saving {_pct(ta.get('global_token_saving_rate'))}, mean Jaccard {float(ta.get('avg_reconstruction_fidelity_jaccard') or 0):.3f} — cite MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json.",
        f"Synthetic UAV hybrid: critical field integrity {hy.get('critical_field_integrity')}, mean payload compression (bytes) {_pct(hy.get('mean_payload_compression_ratio'))}, token saving (same bench) {_pct(hy.get('global_token_saving_rate'))} — do not mix byte and token claims in one sentence.",
        (
            f"Bridge A/B (universal): OFF saving {_pct(u_off.get('global_token_saving_rate'))}, Jaccard {float(u_off.get('avg_reconstruction_fidelity_jaccard') or 0):.3f} "
            f"vs ON saving {_pct(u_on.get('global_token_saving_rate'))}, Jaccard {float(u_on.get('avg_reconstruction_fidelity_jaccard') or 0):.3f} — tradeoff on the same input."
            if u_off and u_on
            else "See MULTILENS_BRIDGE_POLICY_AB_BY_MODE_V1.json for per-mode pairs."
        ),
        (
            f"Same bench ultra-literal: bridge OFF/ON saving {_pct(ul_off.get('global_token_saving_rate'))} / {_pct(ul_on.get('global_token_saving_rate'))} — small gap under tight caps."
            if ul_off and ul_on
            else "Ultra-literal pair: MULTILENS_BRIDGE_POLICY_AB_V1.json."
        ),
        "External-facing numbers must cite defense_code_pack_v1.json and artifact paths; do not equate with NotebookLM narratives.",
    ]

    doc = {
        "schema": "defense_bench_briefing_bullets_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": {
            "snapshot": str(args.snapshot.relative_to(ROOT)).replace("\\", "/"),
            "bridge_by_mode": str(args.by_mode.relative_to(ROOT)).replace("\\", "/")
            if args.by_mode.is_file()
            else None,
        },
        "briefing_bullets_ko": bullets_ko,
        "briefing_bullets_en": bullets_en,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
