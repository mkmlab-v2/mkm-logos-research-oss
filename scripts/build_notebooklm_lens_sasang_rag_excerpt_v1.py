#!/usr/bin/env python3
"""Build NL-facing Sasang lens RAG excerpt (deterministic, B-track only).

SSOT: docs/NotebookLM_sources_manifest.md — LENS_SASANG row.
Not classical canon; IJEOMA_BTRACK remains separate.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "final" / "artifacts" / "notebooklm_lens_sasang_rag_excerpt_v1.md"

INTERPRETIVE = ROOT / "docs/final/artifacts/sasang_interpretive_insight_bundle_v1_latest.json"
MONITOR = ROOT / "docs/final/artifacts/sasang_4agent_monitor_policy_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_excerpt() -> str:
    bundle = _load_json(INTERPRETIVE)
    monitor = _load_json(MONITOR)
    synth = bundle.get("synthesis_v1") or {}
    geumhwa_thr = monitor.get("geumhwa_transition_threshold")

    lines = [
        "# NotebookLM · LENS_SASANG RAG excerpt v1",
        "",
        f"**generated_at_utc:** {_utc()}",
        "**rail:** B_TRACK · **[HYPO]** · `research_only`",
        "**decision_authority:** human_only — NL output is briefing input, not implementation SSOT.",
        "",
        "## Fact-Lock (read first)",
        "",
        "- Single TOE / universal prophecy completion **claims forbidden**.",
        "- **Medical** 금화교역·보명지주·태양인 체질론 ≠ **codebook** `geumhwa_index` / SCM lexicon / monitor threshold.",
        "- Final trading action: **1st `regime_map` + ops gates** — Sasang lens is **short-term intensity assist only**.",
        "- Classical canon (동의보감·이제마 원전): use **`IJEOMA_BTRACK`** notebook — **do not merge** into this pack.",
        "- **SECONDARY_PROXY (18 fragments):** SSOT `docs/research/raw/IJEOMA_SECONDARY_PROXY_v1.json` — upload to **`IJEOMA_BTRACK`**; pointer only in this pack (`notebooklm_lens_sasang_ijoeoma_secondary_proxy_pointer_v1.md`).",
        "",
        "## Axis map (where to look)",
        "",
        "| Topic | In this pack | NOT the same as |",
        "| --- | --- | --- |",
        "| 금화교역 (philosophy) | `MKM_WORLDVIEW` §1.2·§2 — metaphor K↔M, change heart | Codebook detector alone |",
        "| 금화교역 (ops pointer) | interpretive bundle `geumhwagyoyeok` axis + `geum_hwa_detector.py` path | Clinical 金火交易 treatise |",
        "| geumhwa_transition_threshold | "
        + (f"`{geumhwa_thr}` in `sasang_4agent_monitor_policy_v1.json` — 4-agent monitor **force_hold**, not live regime engine"
           if geumhwa_thr is not None
           else "`sasang_4agent_monitor_policy_v1.json` — monitor auto-injection guard")
        + " | Portfolio LOCKED_MODE / trading NO_GO |",
        "| 보명지주 | SCM lexicon axis in interpretive bundle — **language alignment** | Cash floor / survival rule by itself |",
        "| 성정불변 | A-code matrix / worldview **pedagogy** only | Proven eternal backtest invariant |",
        "| 태양인 희귀성 | **§ Core framing below** — 火剋金 + **金器 containment** `[HYPO]`; no clinical cohort % in repo | Frequency statistics in KOSPI/BTC · `market_sasang_lens` axis score |",
        "| Emotion VA | `sasang_emotion_mapping_v1` schema — circumplex anchors | Constitution inference |",
        "",
        "## Core framing · 태양인 희귀성 (MKM pedagogical SSOT · [HYPO])",
        "",
        "**Always lead with this block when asked 「왜 태양인이 희귀한가?」** — do not answer with 「순수 火만 세서 불안정」 alone.",
        "",
        "1. **火剋金(화극금):** 오행에서 火는 金을 녹인다. 바깥으로만 타는 火는 구조·규율(金)과 만나면 **깎이거나 녹거나** 한다.",
        "2. **金器 containment (핵심):** 태양인이 되려면 火가 공기 중에 녹아 사라지거나, 위로만 새는 **기상역상(氣上逆上)** 병리로만 끝나면 안 된다. **로켓 노zzle·엔진 연소실**처럼 **내부 고열을 견디며 가두는 강한 金器(金器)** 가 있어야 **극 火가 체질로 성립**한다.",
        "3. **희귀성의 정의:** 드문 것은 「火가 많은 사람」이 아니라 **火剋金의 파괴를 뒤집어 火를 金器 안에 유지하는 조합**이다. 레포는 **임상·인구 역학 % SSOT 없음** — 교육·서사 `[HYPO]` only.",
        "4. **금화교역 연결 `[HYPO]`:** (A) 火→金 **상전이**(버블→수축) + (B) 火–金 **공존·가둠·교역**. 土 완충은 보조 축(상전이 마찰 완화)으로만 — 단일 방정식·TOE 단정 금지.",
        "5. **코드 격벽:** `geumhwa_transition_threshold`(예: 0.58) = 4-agent monitor **force_hold** 은유 상한 — **태양인 희귀성·연소실 구현 증명 아님**. `geumhwa_index`·LOCKED_MODE와 **인과 단정 금지**.",
        "",
        "**Output order when synthesizing:** Field(`regime_map`) → Lens(사상/명리/성경) → Conflict → Final Action(HOLD/WATCH). Logos `[NON_GATING]`.",
        "",
        "## Synthesis rules (from interpretive bundle v1.1)",
        "",
    ]
    for key in (
        "how_to_synthesize_ko",
        "disagreement_protocol_ko",
        "forbidden_synthesis_ko",
        "axis_order_rationale_ko",
    ):
        val = synth.get(key)
        if val:
            lines.append(f"- **{key}:** {val}")
            lines.append("")

    lines.extend(
        [
            "## NL query starters (Creative-Lock)",
            "",
            "1. **금화교역이란?** — Distinguish (A) worldview metaphor §1.2, (B) codebook/finance shard, (C) medical theory. Cite `forbidden_synthesis`. No superiority to MKM oper score.",
            "2. **태양인 희귀성** — **Must cite § Core framing:** 火剋金 → **金器 containment**(로켓/엔진 연소실 `[HYPO]`) → structural rarity. Add phase-transition (火→金) only as secondary. No clinical % · no oper score · no live trigger.",
            "3. **보명지주 vs risk** — Lexicon + survival **discipline narrative** only; point to ops gates for actual LOCKED_MODE (prophecy/risk SSOT), not Sasang vocabulary alone.",
            "4. **성정불변 vs markets** — Behavioral invariance is **hypothesis**; backtest validity = OOS/regime holdout/raw metrics, not philosophy alone.",
            "",
            "## Repro",
            "",
            "```bash",
            "py scripts/build_notebooklm_lens_sasang_rag_excerpt_v1.py",
            "py scripts/build_notebooklm_lens_source_packs_v1.py",
            "py scripts/build_ijeoma_secondary_proxy_lit_review_v1.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_excerpt(), encoding="utf-8")
    print(f"OK -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
