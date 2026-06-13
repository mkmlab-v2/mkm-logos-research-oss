#!/usr/bin/env python3
"""Build INTERNAL stack map + commander brief (Fact-Lock metrics from disk JSON).

  py scripts/build_a2a_mkm_stack_four_layer_map_v1.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP_MD = ROOT / "docs/final/artifacts/a2a_mkm_stack_four_layer_map_v1.md"
DEFAULT_MAP_META = ROOT / "docs/final/artifacts/a2a_mkm_stack_four_layer_map_v1.json"
DEFAULT_BRIEF_MD = ROOT / "docs/final/artifacts/a2a_commander_stack_brief_corrected_v1.md"
DEFAULT_BRIEF_META = ROOT / "docs/final/artifacts/a2a_commander_stack_brief_corrected_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _pct(x: float | None, digits: int = 2) -> str:
    if x is None:
        return "n/a"
    return f"{round(x * 100, digits)}%"


def _load_facts(root: Path) -> dict[str, Any]:
    lane_bench = _read_json(root / "reports/mkm_ltm_resume_lane_token_bench_v1_latest.json")
    tp01 = _read_json(root / "docs/final/artifacts/a2a_tp01_ops_measurement_v1_latest.json")
    a2a_bench = _read_json(root / "docs/final/artifacts/a2a_dialogue_bench_v1_latest.json")
    track_a_signoff = _read_json(
        root / "docs/final/artifacts/multilens_ultra_compression_track_a_promotion_signoff_v1_latest.json"
    )
    l1_spike = _read_json(root / "docs/final/artifacts/l1_inverse_decoder_spike_test_summary_latest.json")
    ltm_graph = _read_json(root / "storage/meta/mkm_long_term_memory_graph_v1.json")

    naive = lane_bench.get("naive_baseline") or {}
    lanes = lane_bench.get("lanes") or {}
    infra = lanes.get("infra") or {}
    ms = lanes.get("ms") or {}
    tp01_token = tp01.get("token_bench") or {}
    a2a_headline = a2a_bench.get("kpi_headline") or {}
    promoted = track_a_signoff.get("promotion_gates_at_apply") or track_a_signoff.get("promoted_operational_baseline") or {}
    l1_agg = (l1_spike.get("aggregate") or {}) if l1_spike else {}

    return {
        "lane_bench_path": "reports/mkm_ltm_resume_lane_token_bench_v1_latest.json",
        "naive_tokens": naive.get("tokens"),
        "infra_inject_tokens": (infra.get("inject_pins") or {}).get("tokens"),
        "ms_inject_tokens": (ms.get("inject_pins") or {}).get("tokens"),
        "infra_savings_ratio": infra.get("savings_ratio_vs_naive_baseline"),
        "tp01_path": "docs/final/artifacts/a2a_tp01_ops_measurement_v1_latest.json",
        "tp01_full_anchor_tokens": tp01_token.get("full_anchor_tokens"),
        "tp01_inject_tokens": tp01_token.get("inject_off_tokens"),
        "tp01_anchor_ratio": tp01_token.get("reduction_ratio_vs_full_anchor"),
        "tp01_compress_savings": (tp01.get("tp01_pilot") or {}).get("savings_ratio"),
        "a2a_bench_path": "docs/final/artifacts/a2a_dialogue_bench_v1_latest.json",
        "a2a_cross_mean_savings": a2a_headline.get("cross_scenario_mean_mock_avg_savings"),
        "a2a_cross_mean_jaccard": a2a_headline.get("cross_scenario_mean_stub_jaccard"),
        "a2a_by_scenario": a2a_headline.get("avg_savings_by_scenario") or {},
        "track_a_signoff_path": "docs/final/artifacts/multilens_ultra_compression_track_a_promotion_signoff_v1_latest.json",
        "track_a_global_saving": promoted.get("global_token_saving_rate"),
        "track_a_avg_jaccard": promoted.get("avg_reconstruction_fidelity_jaccard"),
        "l1_spike_path": "docs/final/artifacts/l1_inverse_decoder_spike_test_summary_latest.json",
        "l1_avg_exact_restore": l1_agg.get("avg_exact_restore_rate"),
        "ltm_concepts": len(ltm_graph.get("concepts") or {}),
        "ltm_edges": len(ltm_graph.get("edges") or []),
    }


def build_map_markdown(facts: dict[str, Any]) -> str:
    by_sc = facts.get("a2a_by_scenario") or {}
    return f"""# MKM 4층 스택 맵 — 비전 vs 구현 (A2A 정렬용 · INTERNAL)

**INTERNAL ONLY · `[HYPO]` integration map** — 대외·Track A 헤드라인 금지.  
**목적:** 「원본 보존 + 훑기 + AI간 통신 + 메타/융합」이 **한 A2A가 아니라 4층**임을 Fact-Lock으로 고정.

---

## 한 장 요약

| 층 | 비전 | SSOT 아티팩트 | 실측 (디스크) | 합선 금지 |
|----|------|---------------|---------------|-----------|
| **L0 원본** | 디스크 SSOT + pointer | LTM `{facts['ltm_concepts']}` concepts / `{facts['ltm_edges']}` edges · tp03 path+fingerprint | `storage/meta/mkm_long_term_memory_graph_v1.json` | pointer ≠ 무손실 |
| **L1 훑기** | inject pins | **primary:** naive **{facts['naive_tokens']}** → infra **{facts['infra_inject_tokens']}** / ms **{facts['ms_inject_tokens']}** ({_pct(facts['infra_savings_ratio'])}) | `{facts['lane_bench_path']}` | Track A 47%와 합치지 않음 |
| **L1 보조** | ops index top-3 | full anchor **{facts['tp01_full_anchor_tokens']}** → **{facts['tp01_inject_tokens']}** tok ({_pct(facts['tp01_anchor_ratio'])}) | `{facts['tp01_path']}` | 레인 bench와 **비교축 다름** |
| **L2 A2A** | Trust Packet wire | cross-scenario savings **{_pct(facts['a2a_cross_mean_savings'])}** · stub j **{facts['a2a_cross_mean_jaccard']}** | `{facts['a2a_bench_path']}` | **≠ Track A 40-case** |
| **L2a Track A** | 상용 동결 벤치 (**별 축**) | global **{_pct(facts['track_a_global_saving'])}** · J **{round(facts['track_a_avg_jaccard'] or 0, 3)}** | `{facts['track_a_signoff_path']}` | A2A smoke에 붙이지 않음 |
| **L3 메타·융합** | envelope + Track C | `mkm_meta_layer_turn_envelope_v1` · `Invoke-TrackCMacroDailyFusion_v1.ps1` | schema + dashboard JSON | A2A Trust Packet ≠ meta envelope |

**흐름:** `L0 → L1 skim (≥32 tok) → L2 compress/wire` · L3 **평행** · **Track A = 별 KPI 축**.

---

## L1 — 두 비교 축 (둘 다 FACT, 질문이 다름)

| 축 | baseline | inject | SSOT |
|----|----------|--------|------|
| **레인 재개 (primary)** | MISSION+CENTRAL **{facts['naive_tokens']}** tok | infra **{facts['infra_inject_tokens']}** / ms **{facts['ms_inject_tokens']}** | `{facts['lane_bench_path']}` |
| **ops index top-3 (tp01)** | full anchor **{facts['tp01_full_anchor_tokens']}** tok | **{facts['tp01_inject_tokens']}** tok · wire compress **{_pct(facts['tp01_compress_savings'])}** | `{facts['tp01_path']}` |

---

## L2 — A2A vs Track A (FAIL-COMP-004)

| 축 | 지표 | SSOT |
|----|------|------|
| **RQ-019 A2A dialogue** | mean **{_pct(facts['a2a_cross_mean_savings'])}** (trading {_pct(by_sc.get('trading'))} / health {_pct(by_sc.get('health'))} / lexicon {_pct(by_sc.get('lexicon_dense'))}) | `{facts['a2a_bench_path']}` |
| **Track A promoted** | **{_pct(facts['track_a_global_saving'])}** / J **{round(facts['track_a_avg_jaccard'] or 0, 3)}** | `{facts['track_a_signoff_path']}` |
| **L1 human decode (research)** | exact **{_pct(facts['l1_avg_exact_restore'])}** | `{facts['l1_spike_path']}` |

OpenAPI SSOT: **`docs/final/openapi_token_compression_v2_draft.yaml`** (v1 yaml ≠ A2A wire).

---

## 재현

```powershell
py scripts/build_a2a_mkm_stack_four_layer_map_v1.py
powershell -File scripts\\Run-A2aWeeklyReproBundle_v1.ps1
powershell -File scripts\\Run-A2aL1L2ChainPilot_v1.ps1 -AllLanes -AppendLog
```

---

*Generated {_utc_now()} · `build_a2a_mkm_stack_four_layer_map_v1.py`*
"""


def build_brief_markdown(facts: dict[str, Any]) -> str:
    by_sc = facts.get("a2a_by_scenario") or {}
    return f"""# 지휘부 스택 보정 브리핑 (Fact-Lock · INTERNAL)

**pre-legal-send** · NL/Gemini 초안의 왜곡 지표를 디스크 SSOT로 보정한 버전.  
**생성:** `build_a2a_mkm_stack_four_layer_map_v1.py` · {_utc_now()}

---

## 1. 지표 보정 요약

### L1 훑기 (primary — 레인 재개)

- naive baseline (MISSION+CENTRAL): **{facts['naive_tokens']}** tokens (`tiktoken:cl100k_base`)
- inject pins: **infra {facts['infra_inject_tokens']}** · **ms {facts['ms_inject_tokens']}** tokens
- 절감: **{_pct(facts['infra_savings_ratio'])}** vs naive
- SSOT: `{facts['lane_bench_path']}` · 스크립트: `scripts/bench_mkm_ltm_resume_lane_token_v1.py`

### L1 보조 (tp01 ops index top-3)

- full anchor **{facts['tp01_full_anchor_tokens']}** → inject **{facts['tp01_inject_tokens']}** ({_pct(facts['tp01_anchor_ratio'])})
- A2A wire compress on inject: **{_pct(facts['tp01_compress_savings'])}**
- SSOT: `{facts['tp01_path']}`

### L1 human decoder (research_only)

- avg exact restore: **{_pct(facts['l1_avg_exact_restore'])}** — `{facts['l1_spike_path']}`
- legacy oov_literal **57.78%**는 **별 artifact** (`P0_COMMERCIALIZATION_TRACKER` 인용)

### Track A 동결 (별 축 — A2A 아님)

- promoted global saving: **{_pct(facts['track_a_global_saving'])}** · avg J: **{round(facts['track_a_avg_jaccard'] or 0, 3)}**
- SSOT: `{facts['track_a_signoff_path']}`
- sign-off 전 Hangul sweep ~48.8% 등 **active report 무단 승격 금지**

### RQ-019 A2A dialogue bench (별 축 — Track A 아님)

- cross-scenario mean savings: **{_pct(facts['a2a_cross_mean_savings'])}** · stub jaccard: **{facts['a2a_cross_mean_jaccard']}**
- by scenario: trading {_pct(by_sc.get('trading'))} · health {_pct(by_sc.get('health'))} · lexicon_dense {_pct(by_sc.get('lexicon_dense'))}
- SSOT: `{facts['a2a_bench_path']}`

---

## 2. 비전 스택 ↔ SSOT 매핑 (5행 · corrected)

| Layer | 비전 | 스크립트 / 경로 | 팩트 · 정책 |
|-------|------|-----------------|-------------|
| **1. 원본·좌표** | SSOT 디스크 유지 · LTM 좌표 + tp03 pointer | `storage/meta/mkm_long_term_memory_graph_v1.json` · `build_a2a_tp03_chain_ref_pilot_v1.py` | LTM **{facts['ltm_concepts']}** concepts / **{facts['ltm_edges']}** edges |
| **2. 훑기** | essence + must_keep inject | `build_mkm_chat_resume_pack_v1.py` · `bench_mkm_ltm_resume_lane_token_v1.py` | **{facts['naive_tokens']}→{facts['infra_inject_tokens']}/{facts['ms_inject_tokens']}** tok ({_pct(facts['infra_savings_ratio'])}) |
| **3. A2A wire** | Trust Packet agent↔agent | `Invoke-MkmInterAgentEncodingSmoke_v1.ps1` · `compression_token_api_v2_stub.py` · **`openapi_token_compression_v2_draft.yaml`** | **[FACT]** dialogue bench **{_pct(facts['a2a_cross_mean_savings'])}** / j **{facts['a2a_cross_mean_jaccard']}** · **[HYPO]** 상용 버스 · **SEND_GATE: HOLD** |
| **3a. Track A** | 상용 동결 벤치 (**합선 금지**) | `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json` · signoff latest | **[FACT]** **{_pct(facts['track_a_global_saving'])}** / J **{round(facts['track_a_avg_jaccard'] or 0, 3)}** — **A2A 행에 쓰지 않음** |
| **4. 융합** | 멀티렌즈 + macro | `Invoke-TrackCMacroDailyFusion_v1.ps1` · `integrated_governance_v1_latest.json` | Logos `[NON_GATING]` · Final Action = regime + ops gate |
| **5. 메타인지** | premise_audit · rival_hypotheses | `mkm_meta_layer_envelope_v1.py` · `test_mkm_meta_layer_envelope_v1.py` | **8** pytest · schema **`mkm_meta_layer_turn_envelope_v1`** |

---

## 3. 참모 판정 (유지)

- A2A smoke/bench = **L2 레일 무결성**만 · L1/L3/L5와 **auto-merge 금지**
- Track A 47%/J0.89를 A2A `[FACT]`에 넣는 표기 = **FAIL-COMP-004** — 본 브리핑에서 분리함

---

*SSOT companion:* `docs/final/artifacts/a2a_mkm_stack_four_layer_map_v1.md`
"""


def build_meta(facts: dict[str, Any], *, schema: str) -> dict[str, Any]:
    return {
        "schema": schema,
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "hypothesis_tier": "B",
        "legal_status": "pre-legal-send",
        "facts": facts,
        "kill_matrix": [
            "Do not label Track A 47%/J0.89 as RQ-019 A2A bench",
            "Do not use openapi v1 yaml as A2A wire SSOT",
            "Do not merge lane naive baseline with ops-index full-anchor without labeling axis",
        ],
        "repro_commands": [
            "powershell -File scripts\\Run-A2aWeeklyReproBundle_v1.ps1",
            "powershell -File scripts\\Run-A2aL1L2ChainPilot_v1.ps1 -AllLanes -AppendLog",
            "powershell -File scripts\\Run-A2aDialogueBenchReproBundle_v1.ps1",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--map-md", type=Path, default=DEFAULT_MAP_MD)
    ap.add_argument("--map-meta", type=Path, default=DEFAULT_MAP_META)
    ap.add_argument("--brief-md", type=Path, default=DEFAULT_BRIEF_MD)
    ap.add_argument("--brief-meta", type=Path, default=DEFAULT_BRIEF_META)
    args = ap.parse_args()

    facts = _load_facts(ROOT)
    map_md = build_map_markdown(facts)
    brief_md = build_brief_markdown(facts)

    for path, content in (
        (args.map_md, map_md),
        (args.brief_md, brief_md),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"WROTE: {path}")

    args.map_meta.write_text(
        json.dumps(build_meta(facts, schema="a2a_mkm_stack_four_layer_map_v1"), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    args.brief_meta.write_text(
        json.dumps(build_meta(facts, schema="a2a_commander_stack_brief_corrected_v1"), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(f"WROTE: {args.map_meta}")
    print(f"WROTE: {args.brief_meta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
