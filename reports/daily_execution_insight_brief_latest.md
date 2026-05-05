# Daily execution insight — 1-page brief (generated)

**AUTO:** `scripts/build_daily_execution_insight_brief_v1.py` — Fact-Lock sources only; not LLM prose.

## 0) Meta

| `brief_date_utc` | 2026-05-02 |
| `workspace_anchor` | BTC spot / operator anchor — set via CLI if needed |
| `mode` | `OBSERVATION_ONLY` |

## 1) Execution facts (disk)

### 1a) Dual regime (snippet only — no full `interpretation` in brief)

- **Thin row:** `C:/workspace/docs/final/artifacts/multilens_eval_v2_thin_report_latest.json` row `calendar_date=2023-03-10`

**`interpretation_snippet`:**

```
dual_regime: gate_profile=balanced; PSI=0.60 (warn>0.60, crisis>0.80); bible_risk=0.33; stress=0.44; cap=0.89; state_clamp=on;state_id=2;state_cap_noop=1.0000
```

**Snapshot (one line):** `risk_multiplier_cap` = 0.8899 · `market_shock_confirmed` = False · `veto_triggered` = False

### 1b) Independent lens fusion stub (`conflict_summary`)

- **Source:** `C:/workspace/docs/final/artifacts/independent_lens_fusion_stub_latest.json`

- **`minority_lens_ids`:** `["logos"]`
- **`logos_evidence_verse_ids`:** `["sample-001", "sample-002", "sample-003"]`

**`conflict_narrative_guarded`:**

```
Lens direction alignment: majority_sign=bull, agreement_rate=0.666667, conflict_count=1. Minority vs majority: logos differ from majority_sign=bull. Breakdown: myeongni: sign=bull, score=0.080000, conf=0.685520; sasang: sign=bull, score=0.170000, conf=0.711500; logos: sign=bear, score=-0.323333, conf=0.200000. Logos evidence verse_id anchors (batch-bound): sample-001, sample-002, sample-003. Logos hash-tagged snippet (clipped): [#sample-001] [#sample-002] [#sample-003]
```

## 2) Hypothesis / insight ([HYPO] — not A-track trigger)

| item | memo |
|------|------|
| hypothesis one-liner | *(operator)* |
| next check script / artifact | *(operator)* |

## 3) Final action (gate vocabulary only)

| field | value |
|-------|-------|
| `final_action_label` | *(operator)* |
| `evidence_paths` | `C:/workspace/docs/final/artifacts/multilens_eval_v2_thin_report_latest.json`; `C:/workspace/docs/final/artifacts/independent_lens_fusion_stub_latest.json` |

---

_thin_ok=True calendar_pick=2023-03-10 fusion_ok=True_
