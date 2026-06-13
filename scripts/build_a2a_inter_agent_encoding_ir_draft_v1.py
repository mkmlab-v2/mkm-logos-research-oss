#!/usr/bin/env python3
"""Build INTERNAL A2A inter-agent encoding IR draft (70/20/10) from latest bench artifacts.

pre-legal-send · NOT PUBLIC_FACING approved. Numbers from JSON only.

  py scripts/build_a2a_inter_agent_encoding_ir_draft_v1.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/a2a_inter_agent_encoding_ir_draft_v1.md"
DEFAULT_META = ROOT / "docs/final/artifacts/a2a_inter_agent_encoding_ir_draft_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _pct(x: float | None, *, digits: int = 2) -> str:
    if x is None:
        return "n/a"
    return f"{round(x * 100, digits)}%"


def build_ir_markdown(root: Path) -> tuple[str, dict[str, Any]]:
    bench = _read_json(root / "docs/final/artifacts/a2a_dialogue_bench_v1_latest.json")
    tp01 = _read_json(root / "docs/final/artifacts/a2a_tp01_ops_measurement_v1_latest.json")
    tp02 = _read_json(root / "docs/final/artifacts/a2a_tp02_lexicon_dense_bench_v1_latest.json")
    tp03 = _read_json(root / "docs/final/artifacts/a2a_tp03_chain_ref_pilot_v1_latest.json")
    dogfood = _read_json(root / "docs/final/artifacts/a2a_dogfood_longitudinal_report_v1_latest.json")
    tier3_index = _read_json(root / "docs/final/artifacts/a2a_tier3_cursor_wire_handoff_lane_index_v1_latest.json")
    status = _read_json(root / "docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json")
    headline = bench.get("kpi_headline") or {}
    by_scenario = headline.get("avg_savings_by_scenario") or {}
    tp01_pilot = tp01.get("tp01_pilot") or {}
    tp01_token = tp01.get("token_bench") or {}
    build_ms = (tp01.get("resume_pack_build") or {}).get("elapsed_ms")
    tp02_mock = (tp02.get("trust_packet_mock") or {}).get("metrics") or {}
    tp03_agg = tp03.get("aggregate_pointer_vs_full") or {}
    dogfood_metrics = dogfood.get("metrics") or {}
    tier3_j = dogfood_metrics.get("tier3_expand_jaccard") or {}
    tier3_j_lane = dogfood_metrics.get("tier3_expand_jaccard_by_lane") or {}
    log_counts = dogfood.get("log_row_counts") or {}

    tier3_lane_lines = []
    for lane, row in sorted((tier3_index.get("lanes") or {}).items()):
        tier3_lane_lines.append(
            f"| {lane} | {row.get('expand_jaccard')} | {_pct(row.get('wire_savings_ratio'))} | "
            f"{row.get('loss_profile_used')} |"
        )
    tier3_lane_table = "\n".join(tier3_lane_lines) if tier3_lane_lines else "| (no lanes) | | | |"

    meta = {
        "schema": "a2a_inter_agent_encoding_ir_draft_v1",
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "legal_status": "pre-legal-send",
        "public_facing_approved": False,
        "artifact_sources": [
            "docs/final/artifacts/a2a_dialogue_bench_v1_latest.json",
            "docs/final/artifacts/a2a_tp01_ops_measurement_v1_latest.json",
            "docs/final/artifacts/a2a_tp02_lexicon_dense_bench_v1_latest.json",
            "docs/final/artifacts/a2a_tp03_chain_ref_pilot_v1_latest.json",
            "docs/final/artifacts/a2a_dogfood_longitudinal_report_v1_latest.json",
            "docs/final/artifacts/a2a_tier3_cursor_wire_handoff_lane_index_v1_latest.json",
            "docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json",
        ],
        "repro_commands": [
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\Run-A2aDialogueBenchReproBundle_v1.ps1",
            "py scripts/build_a2a_tp01_ops_measurement_v1.py --append-log",
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\Invoke-A2aTargetPointsPilotBundle_v1.ps1 -StrictExit",
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\Run-A2aDogfoodAutoChain_v1.ps1",
            "py scripts/check_a2a_cursor_dogfood_peer_brief_v1.py --strict-exit",
        ],
    }

    md = f"""# MKM Inter-Agent Encoding — IR draft (A2A · INTERNAL)

**INTERNAL ONLY · pre-legal-send** — 법무·`PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` 통과 전 대외 배포 금지.  
**발표 톤 (70/20/10):** 측정·재현 70% · 거버넌스·격벽 20% · Lingua Franca 힌트 10%.

---

## 면책

- **무손실·100% 복원·프로덕션 SLA·SOTA 이김** 주장 금지.
- 아래 수치는 **`[HYPO]` B-track 벤치** — Track A 동결 벤치(~47% global saving · Jaccard ~0.89) **대체 아님**.
- L1 human decoder exact restore **~58%** (`research_only`) — 운영 복원 보장 아님.
- RQ-019 **CLOSED** = 인코딩 리허설·법무 closeout **기록** — **운영 A2A 버스 완성 아님**.

---

## 70% — 측정·재현 (Fact-Lock)

### A2A dialogue bench (3 scenarios · 4 turns)

| 항목 | 값 | SSOT |
|------|-----|------|
| bench_ok | {bench.get('bench_ok')} | `a2a_dialogue_bench_v1_latest.json` |
| cross-scenario mean mock savings | {_pct(headline.get('cross_scenario_mean_mock_avg_savings'))} | 동일 |
| cross-scenario mean stub jaccard | {headline.get('cross_scenario_mean_stub_jaccard')} | 동일 |
| trading avg savings | {_pct(by_scenario.get('trading'))} | per-scenario |
| health avg savings | {_pct(by_scenario.get('health'))} | per-scenario |
| lexicon_dense avg savings | {_pct(by_scenario.get('lexicon_dense'))} | per-scenario |

**재현:** `powershell -File scripts\\Run-A2aDialogueBenchReproBundle_v1.ps1`

### tp01 ops resume handoff (Cursor multi-chat)

| 항목 | 값 |
|------|-----|
| resume pack build | {build_ms} ms (exit 0) |
| inject pins (raw) | {tp01_token.get('inject_off_tokens')} tokens |
| tp01 wire compress savings | {_pct(tp01_pilot.get('savings_ratio'))} |
| vs full anchor reduction | {_pct(tp01_token.get('reduction_ratio_vs_full_anchor'))} (inject vs full slice) |

**재현:** `py scripts/build_a2a_tp01_ops_measurement_v1.py --append-log`

### tp02 lexicon_dense bench (prophecy executor wire)

| 항목 | 값 |
|------|-----|
| bench_ok | {tp02.get('bench_ok')} |
| mock avg savings | {_pct(tp02_mock.get('avg_savings_ratio'))} |
| wire-first avg envelope savings | {_pct(((tp02.get('wire_first_envelope') or {}).get('metrics') or {}).get('avg_trust_packet_savings_ratio'))} |

**재현:** `py scripts/build_a2a_tp02_lexicon_dense_bench_v1.py --strict-exit`

### tp03 Track C chain-ref pilot (pointer only)

| 항목 | 값 |
|------|-----|
| pilot_ok | {tp03.get('pilot_ok')} |
| artifacts present | {tp03.get('artifacts_present')} / missing {tp03.get('artifacts_missing')} |
| pointer vs full body reduction | {_pct(tp03_agg.get('reduction_ratio'))} (**pointer economics — not A2A quality headline**) |

**재현:** `py scripts/build_a2a_tp03_chain_ref_pilot_v1.py --strict-exit`

### Cursor dogfood T1→T3 (Tier2 shadow + Tier3 per-lane brief)

| 항목 | 값 |
|------|-----|
| dogfood report_ok | {dogfood.get('report_ok')} |
| alerts | {dogfood.get('alerts') or []} |
| log rows (l2 / tier3) | {log_counts.get('l2_shadow', 0)} / {log_counts.get('tier3_handoff', 0)} |
| tier3 expand J (all, latest) | {tier3_j.get('latest')} |

| lane | expand J | L2 savings | loss_profile |
|------|----------:|-----------:|--------------|
{tier3_lane_table}

**재현:** `powershell -File scripts\\Run-A2aDogfoodAutoChain_v1.ps1` · peer smoke: `py scripts/check_a2a_cursor_dogfood_peer_brief_v1.py --strict-exit`

---

## 20% — 거버넌스·격벽

- Track A active signoff **변경 없음** · health relaxed cap = **B-track 후보만**.
- On-wire payload = **Trust Packet / wire envelope** — plaintext는 audit mock 전용.
- `rq_019_milestones_core_ready`: **{status.get('rq_019_milestones_core_ready')}** (encoding status JSON).
- 실매매·SEND·쇼룸 human UI wire codec **자동 합선 없음**.

---

## 10% — 방향 힌트 ([VISION] · 조건부)

- 글로벌 연구 축: **시맨틱 통신 · LLM 압축 · lexicon rail · prompt economics** — 동일 문제 계열 정렬 (`mkm_inter_agent_encoding_sota_map_v1.md`).
- MKM 포지션: **측정된 lexicon rail + domain router + Trust Packet 초안** 위에 inter-agent encoding layer 확장 중 — **finished lingua franca 아님**.

**KO (IR 한 줄):** LLM 에이전트 간 비용·지연 문제에, MKM은 **원어 기반 렉시콘·도메인 통제 압축(측정 JSON)** 위 Trust Packet 초안으로 인코딩 레이어를 확장 중입니다. 무손실 공통어·프로덕션 SLA는 **아직 주장하지 않습니다**.

---

## 금지 패턴 (Kill-Matrix)

- tp03 chain-ref **95%**를 A2A 품질 헤드라인으로 사용
- smoke exit 0 → **「상용 A2A 완성」**
- 압축 성공 → **실거래 트리거** 암시

---

*Generated {meta['generated_at_utc']} · `build_a2a_inter_agent_encoding_ir_draft_v1.py`*
"""
    return md, meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-meta", type=Path, default=DEFAULT_META)
    args = ap.parse_args()

    md, meta = build_ir_markdown(ROOT)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(md, encoding="utf-8")
    args.out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_md}")
    print(f"WROTE: {args.out_meta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
