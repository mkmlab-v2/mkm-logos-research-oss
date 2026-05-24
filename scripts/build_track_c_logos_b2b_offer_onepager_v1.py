#!/usr/bin/env python3
"""Build Track C Logos Deep Risk Narrative B2B one-pager (artifact-path grounded)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _exists(root: Path, rel: str) -> bool:
    return (root / rel).is_file()


def _build_md(*, generated_at: str, evidence: list[tuple[str, bool]]) -> str:
    ev_lines = "\n".join(
        f"- `{p}` — {'present' if ok else 'MISSING (regenerate chain before customer send)'}"
        for p, ok in evidence
    )
    all_ok = all(ok for _, ok in evidence)
    evidence_status = "ALL_PRESENT" if all_ok else "GAPS_REVIEW_BEFORE_SEND"
    return f"""# [MKM] Macro-Risk Intelligence Brief — Deep Narrative Module

**Macro-Risk Intelligence Brief · Logos / Classical Corpus Deep Narrative (Track C)**  
**2026 H2 · B2B subscription module (draft)**

- **generated_at_utc:** `{generated_at}`
- **artifact_evidence_status:** `{evidence_status}`
- **aligned_with:** `TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.2 · §3.8 · §8 · §9 · §9A · `PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md`
- **status:** `DRAFT_AUTO` — **legal review required before external send**

---

## 1. Executive Summary

This brief analyzes **unstructured macro-risk** that conventional financial indicators may not fully capture. MKM combines **high-density classical and philosophical text corpora** (marketed externally as the **Logos / classical corpus stress-test bed**) with **macro and regime context** to produce **artifact-backed risk narratives** for operator review.

This is **not** prophecy, religious instruction, or trade advice. It is **decision-support intelligence** with reproducible JSON artifacts and audit-oriented logs.

**한국어 요지:** 전통 지표만으로 포착하기 어려운 **비정형 거시 리스크**를, **고난도 비정형 텍스트 스트레스 테스트 베드(Logos/고전 코퍼스)** 와 **거시·레짐(Field)** 맥락으로 구조화한 **리스크 내러티브**입니다. 예언·종교·매매 지시가 아닙니다.

---

## 2. Intelligence Mechanism — Multi-Lens (Fact-Lock)

MKM does **not** rely on a single indicator. Reporting order is fixed:

| Layer | Role |
|-------|------|
| **Field (ingestion)** | Macro/regime context, disclosure-grade text streams, stress-test inputs — **contract-defined refresh cadence** (not “real-time” unless SLA states it). |
| **Lens (structural analysis)** | **사상** — short-horizon intensity · **명리** — medium-horizon direction · **Logos / classical corpus** — deep narrative, structural tension, citation discipline — **`[NON_GATING]`** |
| **Conflict resolver** | Cross-lens disagreement surfaced explicitly (no silent override). |
| **Final (narrative output)** | Operator posture labels (e.g. HOLD / REDUCE / WATCH) — **not buy/sell instructions**. |

**대외 용어:** Customer-facing copy may say **“Logos / ancient classical corpus”** instead of religious labels; internal SSOT lens name remains **성경/Logos** per `AGENTS.md`.

**금지 서술:** “The engine predicts markets,” “matches historical cycles with certainty,” “transparent full AI reasoning chain,” or standalone **Logos Archetype Engine** as a trade signal product.

---

## 3. Core Deliverables (subscription module)

1. **Logos Insight Bundle** (`logos_insight_bundle_v1`) — structured non-deterministic text analysis: tension axes, citation pack, `[NON_GATING]` narrative slots. Artifact: `logos_insight_bundle_v1_latest.json`.
2. **Commander Deep Report** (`logos_track_b_commander_deep_report_v1`) — macro-risk structure for human review. Artifacts: `logos_track_b_commander_deep_report_latest.json` · `reports/logos_track_b_commander_deep_report_latest.md`.
3. **Stress-test narratives** — conflict / extreme-ambiguity scenarios for board and risk committees (scenario copy, not forecasts).
4. **Optional ops slice** — read-only Track C dashboard fields (`mkm_trackc_ops_dashboard_latest.json`), Trust Visualization / `non_gating` markers.

**Cadence:** Monthly/quarterly brief per contract — internal chains may run daily; **customer SLA is contract-defined**, not implied “daily/weekly” unless written.

**Bundle recommendation:** Sell as **premium module** atop `track_c_b2b_macro_alert_offer_onepager` (§3.8 macro early-warning subscription), not as a standalone “holy text predicts markets” SKU.

---

## 4. System Integrity & Governance

- All outputs are **decision-support only** — no buy/sell instructions, no return guarantees.
- **Artifact-backed governance:** timestamps, JSON paths, append-only logs — not public disclosure of proprietary weights or full inference graphs (`TRACK_C` §9A).
- **Governance gates** (WATCH/HOLD-style **operator posture**, not trade triggers) may flag **review / defer** states when policy thresholds are met.
- **`[NON_GATING]` isolation:** This layer is **not** wired to live execution (**A-track**). Research lanes (**B-track `[HYPO]`**) do not auto-promote to client trading.

---

## 5. Legal Disclaimer (§9 — required)

> MKM provides a governance-driven risk warning and scenario posture service that integrates multi-lens analytics. The service supports exposure-control decisions with reproducible artifacts and verification logs. It is not investment advice, does not provide buy/sell instructions, and does not guarantee returns.

**한국어:** 본 문서는 정보 제공 목적이며, 투자자문·매수/매도 권유·수익 보장을 포함하지 않습니다. 최종 의사결정과 책임은 고객 운영자에게 있습니다.

---

## Appendix A — Repository evidence (internal / NDA annex)

_Regenerate before customer meetings: `py scripts/build_track_c_logos_b2b_offer_onepager_v1.py`_

{ev_lines}

**Ops chains:** `Invoke-TrackCMacroDailyFusion_v1.ps1` · `run_btrack_daily_hypothesis_chain.ps1` · `run_logos_track_b_commander_deep_report_v1.py` · `build_logos_insight_bundle_v1.py` — SSOT: `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` (Logos rows).

## Appendix B — Related commercial SSOT

- `docs/final/artifacts/track_c_b2b_macro_alert_offer_onepager_latest.md`
- `docs/final/artifacts/track_c_2026_h2_macro_risk_alert_report_mvp_v1.md`
- `docs/final/LOGOS_SYMBOLIC_INTERPRETATION_LAYER_MAP_V1.md`

## Short copy

- **Deep narrative, not trade advice.**
- **Classical-corpus stress test — artifact-backed.**
- **Logos lens: `[NON_GATING]` depth only.**

## Pricing

- Quoted as **Macro early-warning + Deep Narrative module** tier.
- License: **decision-support output** (not core-formula license).
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = _root()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    evidence_paths = [
        "docs/final/artifacts/logos_insight_bundle_v1_latest.json",
        "docs/final/artifacts/logos_track_b_commander_deep_report_latest.json",
        "reports/logos_track_b_commander_deep_report_latest.md",
        "docs/final/artifacts/logos_4d_state_v1_latest.json",
        "docs/final/artifacts/logos_independent_lens_latest.json",
        "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json",
        "docs/final/schemas/logos_insight_bundle_v1.schema.json",
    ]
    evidence = [(p, _exists(root, p)) for p in evidence_paths]
    md = _build_md(generated_at=generated_at, evidence=evidence)
    out = root / "docs/final/artifacts/track_c_logos_deep_risk_narrative_offer_onepager_v1_latest.md"

    if args.dry_run:
        print(json.dumps({"out": str(out), "evidence": evidence}, indent=2))
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    missing = [p for p, ok in evidence if not ok]
    print(f"WROTE: {out}")
    if missing:
        print(f"WARN: missing_artifacts={missing}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
