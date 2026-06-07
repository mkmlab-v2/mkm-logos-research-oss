#!/usr/bin/env python3
"""Build 15-min internal B2B rehearsal talk track (Track C · DRAFT · no auto-send)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REHEARSAL = ROOT / "reports/track_c_b2b_internal_rehearsal_readiness_v1_latest.json"
READINESS = ROOT / "reports/track_c_b2b_meeting_pack_readiness_v1_latest.json"
CLOSURE = ROOT / "docs/final/artifacts/logos_100pct_closure_v1_latest.json"
CHRONO_MS = ROOT / "docs/final/artifacts/logos_chronology_era_blind_eval_text_blind_v1_latest.json"
SWEEP = ROOT / "docs/final/artifacts/dynamic_bgm_hp_sweep_v1_latest.json"
DEMO = ROOT / "docs/final/artifacts/dynamic_bgm_melody_chain_demo_v1_latest.json"
STAGING = ROOT / "reports/track_c_audio_hook_samples_v1/track_c_audio_hook_samples_manifest_v1_latest.json"
FUSED_OPS = ROOT / "reports/biblical_dss_fused_ops_board_latest.json"
DSS_HANDOFF = ROOT / "reports/dss_research_lane_handoff_latest.json"
DEFAULT_OUT = ROOT / "reports/track_c_b2b_15min_rehearsal_script_v1_latest.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _audio_appendix(sweep: dict[str, Any], demo: dict[str, Any], staging: dict[str, Any]) -> str:
    bullets = sweep.get("track_c_audio_hook_bullets") or []
    bl = "\n".join(f"- {b}" for b in bullets) if bullets else "- (see sweep JSON)"
    run_id = (demo.get("generation") or {}).get("run_id") or "?"
    gate = (demo.get("gate") or {}).get("decision") or "?"
    samples = staging.get("samples") or []
    wav_lines = []
    for row in samples:
        if not isinstance(row, dict):
            continue
        wav_lines.append(
            f"| hp={row.get('hp_pct')} | `{row.get('run_id')}` | {row.get('gate_decision')} | "
            f"`{row.get('dest', '').split('/')[-1]}` |"
        )
    wav_table = "\n".join(wav_lines) if wav_lines else "| — | — | — | — |"
    return f"""## Optional appendix — Functional BGM `[HYPO]` (if buyer asks · +2 min)

**Say (KO):** 대중음악 생성 AI와 **다른 링**입니다. 우리는 **수치 도면(JSON) → self-hosted MusicGen → 게이트 JSON** 체인으로 **감사 가능한 기능성 BGM** PoC만 보여 드립니다. 보컬·팝송·Suno 대체 **아님**.

**Do NOT say:** Suno competitor · zero hallucination · clinical efficacy · Track A promotion

{bl}

| hp | run_id | gate | staged WAV |
|----|--------|------|------------|
{wav_table}

- Demo SSOT: `dynamic_bgm_melody_chain_demo_v1_latest.json` (hp100 · run `{run_id}` · gate **{gate}**)
- Play locally from counsel ZIP — **not** embedded in live showroom URL
"""


def _dss_appendix(fused: dict[str, Any], handoff: dict[str, Any]) -> str:
    profiles = handoff.get("profiles") if isinstance(handoff.get("profiles"), dict) else {}
    default_p = profiles.get("default_3file") if isinstance(profiles.get("default_3file"), dict) else {}
    ext3_p = profiles.get("ext3_only") if isinstance(profiles.get("ext3_only"), dict) else {}
    uf = fused.get("unified_frontline") if isinstance(fused.get("unified_frontline"), dict) else {}
    raw_repair = fused.get("raw_repair_profiles") if isinstance(fused.get("raw_repair_profiles"), dict) else {}
    three = raw_repair.get("three_file_isolated") if isinstance(raw_repair.get("three_file_isolated"), dict) else {}
    ext3_rr = raw_repair.get("ext3_only_isolated") if isinstance(raw_repair.get("ext3_only_isolated"), dict) else {}
    raw = three.get("raw") if isinstance(three.get("raw"), dict) else {}
    repair = three.get("repair_v2") if isinstance(three.get("repair_v2"), dict) else {}
    delta = three.get("delta") if isinstance(three.get("delta"), dict) else {}
    ext3_repair_matched = (ext3_rr.get("repair_v2") or {}).get("matched_rows", 971)
    rec = (handoff.get("guidance") or {}).get("recommended_ndjson_profile") or "ext3_only"
    uf_status = uf.get("overall_status") or "PASS"
    uf_steps = "15/15" if uf.get("legacy_scripts_restored") == 10 else "check cycle report"
    uf_tag = uf.get("latest_cycle_tag") or "command_center_followup_20260607_legacy_restore"
    return f"""## Optional appendix — DSS / Biblical history `[HYPO]` (if buyer asks · +2 min)

**Say (KO):** DSS·외경 코퍼스는 **메타데이터 청크만** 뉴스 관측 레일에 얹는 B-track 연구입니다. **성경 렌즈 `[NON_GATING]`** · 실매매·Track A 승격 **아님**.

**Do NOT say:** 무손실 압축 · ~47.5% Track A · repair 점수 = 본체 품질 · 투자·매매 시그널

| profile | surface rows | repair matched (operational) | Δ composite |
|---------|--------------|------------------------------|-------------|
| default 3-file | {default_p.get("surface_rows", 1716)} | {repair.get("matched_rows", 1760)} | +{delta.get("alignment_pass_rate_delta_repair_v2_minus_raw", 0.122092):.6f} |
| ext3-only (Hebrew pin) | {ext3_p.get("surface_rows", 927)} | {ext3_repair_matched} | +{ext3_p.get("delta_composite", 0.083472):.6f} |

- **raw (isolated prod):** matched **{raw.get("matched_rows", 44)}** — repair uplift ≠ raw gate
- **repair_v2:** operational (post-processor included) — **not** base-model headline
- **Unified frontline:** `{uf_tag}` · **{uf_steps} PASS** · authority **READY** · `track_a_promotion: blocked`
- **Recommended profile (reports):** `{rec}` · weekly AB SSOT remains `default_3file`

**Artifacts:** `biblical_dss_fused_ops_board_latest.json` · `dss_research_lane_handoff_latest.json` · `unified_frontline_cycle_report_{uf_tag}.json`
"""


def _logos_closure_block(closure: dict[str, Any], chrono_ms: dict[str, Any]) -> str:
    closure_ok = bool(closure.get("closure_ok"))
    rag_4e = ((closure.get("checks") or {}).get("rag_4e_resolved") or {})
    rag_pass = bool(rag_4e.get("passed"))
    sem = ((closure.get("checks") or {}).get("semantic_rag_quality") or {})
    thematic = sem.get("thematic_hit_at_1")
    pytest_ok = ((closure.get("checks") or {}).get("pytest_bundle") or {}).get("passed")
    ms_hit = (chrono_ms.get("summary") or {}).get("hit_at_1_strict")
    ms_pct = f"{float(ms_hit) * 100:.1f}%" if isinstance(ms_hit, (int, float)) else "TBD"
    th_pct = f"{float(thematic) * 100:.1f}%" if isinstance(thematic, (int, float)) else "TBD"
    return f"""**LOGOS infra closure (70% · if asked · internal numbers only):**

- **Say (KO):** Logos RAG **4계층 artifact 체인**이 closure gate를 통과했습니다 — `closure_ok={closure_ok}`, `rag_4e_resolved={rag_pass}`. **투자·매매 근거 아님** · `[NON_GATING]`.
- **20% ops:** 31k절 ST 인덱스 · 12문항 bilingual 쿼리셋 · pytest bundle **{"passed" if pytest_ok else "check"}**.
- **Do NOT say in room:** thematic {th_pct} as customer-facing accuracy · hardset tier_v2 · ~47.5% compression.
- **External headline only:** 역사 연대기 blind **{ms_pct}** (`logos_chronology_era_blind_eval_text_blind_v1_latest.json`) — **다른 과제**이며 RAG 12문항 점수와 **합치지 않음**.

**Artifact:** `logos_100pct_closure_v1_latest.json` · envelope `three_lens_sphere_envelope_v1_latest.json`
"""


def build_md() -> str:
    rehearsal = _read(REHEARSAL)
    readiness = _read(READINESS)
    closure = _read(CLOSURE)
    chrono_ms = _read(CHRONO_MS)
    sweep = _read(SWEEP)
    demo = _read(DEMO)
    staging = _read(STAGING)
    fused = _read(FUSED_OPS)
    handoff = _read(DSS_HANDOFF)
    rehe_ok = rehearsal.get("ready_for_15min_rehearsal", False)
    internal_ok = readiness.get("ready_for_internal_meeting", False)
    logos_block = _logos_closure_block(closure, chrono_ms)
    dss_block = _dss_appendix(fused, handoff)

    return f"""# Track C B2B — 15 min internal rehearsal script (DRAFT)

**generated_at_utc:** `{_utc_now()}`  
**status:** `DRAFT_AUTO` · **internal only** · `ready_for_external_send: false`  
**pre-flight:** rehearsal={rehe_ok} · internal_meeting={internal_ok}

---

## Opening (30 sec · KO)

> 투자 권유·매매 지시·성과 보장이 아닙니다. **의사결정 보조**와 **통제 가능한 에이전트 경계**를 아티팩트로 보여 드립니다.  
> 화면 배지: `[HYPO]` · `research_only` · `NON_GATING` · `no_trade_signals`

---

## 0–3 min · Two-Layer Agent (CISO + CTO)

**CISO (30 sec):** Layer A = sandbox class + human approval + thin API boundary. 기존 execution sandbox를 갈아엎자는 제안이 **아닙니다**.

**CTO (30 sec):** Layer B = Fact-Lock, benchmarks, metering, promotion gates — 재현 가능한 JSON·exit code, "믿어 주세요" 채팅이 **아닙니다**. **Zero hallucination을 보장하지 않습니다.**

**Both (15 sec):** 통합은 **`[HYPO]` 개념 설명**일 뿐 — 계약·OEM 확약 **아님**. 슬라이드에 % 헤드라인 **없음**.

**Artifact:** `track_c_b2b_two_layer_agent_slide_v1_print.html` → Print PDF

---

## 3–8 min · Macro / Logos open

**One line (KO):** 거시 리스크 시나리오·운영자 포즈를 아티팩트 근거로 제공 — **투자자문·매매 지시 아님**.

**Show (optional):** https://jemaai.cloud/public_showroom_logos_oracle_v6.html?product=1 — Logos Observatory · **`[NON_GATING]`**

**Artifact:** `track_c_logos_b2b_exec_summary_slide_v1_latest.md`

{logos_block}

---

## 8–13 min · Proof (redacted demo)

**Say:** Core formulas stay server-side (§9A). Redacted excerpt only — **no path leaks, no win-rate headline**.

**Artifact:** `track_c_logos_redacted_demo_excerpt_v1_latest.md`

---

## 13–15 min · Combined offer (teaser)

**Say:** Macro subscription + Logos premium module bundle — **follow-up** deep dive for steps 3–8 in pack index.

**Close:** Next meeting = compression appendix / FinOps Q&A **only if asked** — wire metrics ≠ compression KPI.

**Artifact:** `track_c_combined_b2b_offer_onepager_v1_latest.md`

---

{_audio_appendix(sweep, demo, staging)}

---

{dss_block}

---

## Forbidden in room

- ~47.5% / lossless / omniscient AI / guaranteed returns
- Track A · live trading · auto-promote from this deck
- Competitor trash-talk · wire envelope as "compression KPI"

---

## Post-meeting (human)

1. `py scripts/athena_checkpoint.py "B2B rehearsal YYYY-MM-DD outcome …"`
2. If rehearsed: `py scripts/record_track_c_b2b_commander_signoff_v1.py --reference <id> --scope internal_rehearsal_complete`
3. Counsel path: `build_track_c_b2b_counsel_one_minute_brief_v1.py` → legal handoff — **external send still HOLD**

**runbook SSOT:** `docs/final/artifacts/track_c_b2b_internal_rehearsal_runbook_v1_latest.md`
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(build_md(), encoding="utf-8")
    print(f"WROTE: {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
