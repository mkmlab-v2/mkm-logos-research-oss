# Logos symbolic backtest — weekly ops reval (v1)

| Field | Value |
| --- | --- |
| `generated_at_utc` | `2026-05-18T12:30:00Z` |
| `research_only` | `true` |
| `hypothesis_tier` | `B` |
| `mode` | B-track · **no Track A promotion** · not a live-trading trigger |
| SSOT script | `scripts/run_logos_symbolic_event_backtest_v1.py` |

---

## Headline rules (Fact-Lock)

- **Never headline** bundle `weighted_hit_rate` **~94.9%** (`logos_symbolic_event_backtest_bundle_summary_v1.json` → `aggregate.weighted_hit_rate`: **0.94941**). That aggregate mixes runs and is dominated by `label_guided_seed` synthetic rows (~99% on 160/187 in `latest_latest`).
- **Never cite** `logos_symbolic_event_backtest_benchmark_logos_real_oos_latest.json` **100% hit rate** as **OOS proof** — holdout news is **synthetic** (`label_guided_seed` / `manual_seed`); use only with explicit synthetic-news disclaimer.
- Report **per-corpus** `n_evaluated`, `hit_rate`, and `non_synthetic_hit_rate` from the JSON named below; note **Logos vs counterfactual** when predictions tie.

---

## Reval summary (disk SSOT)

All four artifacts **present** on disk as of `generated_at_utc`.

| Artifact | `generated_at_utc` (file) | n | hit_rate | non_synthetic hit_rate | Notes |
| --- | --- | ---: | ---: | ---: | --- |
| `logos_symbolic_event_backtest_reval_hardset_latest.json` | `2026-05-18T12:01:00Z` | 27 | 0.926 | 0.926 | Logos map · hardset external BTC/macro · `neutral_score_band` **0.05** · locked_eval **4/4 (1.0)** |
| `logos_symbolic_event_backtest_clean_hardset_counterfactual_reval_latest.json` | `2026-05-18T12:01:51Z` | 27 | 0.926 | 0.926 | Counterfactual map · same news/labels · band **0.25** · **same predictions as Logos** on all 27 rows |
| `logos_symbolic_event_backtest_reval_contrastive48_latest.json` | `2026-05-18T12:01:01Z` | 48 | 0.708 | 0.708 | Logos map · `contrastive_challenge` · band **0.05** · locked_eval only |
| `logos_falsification_contrastive_slice_latest.json` | `2026-05-16T22:10:03Z` | 160 contrastive | logos **1.0** / CF **0.494** | — | **⚠ Synthetic-news warning:** built from `*_benchmark_*_real_oos_latest.json` arms (synthetic holdout news). **Not** a clean external-news reval. Do not use for OOS marketing. |

**Hardset split detail (Logos reval):** calibration 3/3 (1.0) · train_holdout 18/20 (0.9) · locked_eval 4/4 (1.0).

**Contrastive48 vs counterfactual (prior reval run, optional check):** `logos_symbolic_event_backtest_clean_contrastive48_counterfactual_reval_latest.json` → hit_rate **0.292** (n=48, band 0.05) vs Logos **0.708** — predictions differ on most rows.

If any row in the table is missing on disk: **run reval first** (CLI block below).

---

## Weekly CLI reproduce (copy-paste)

Run from repo root `c:\workspace`. Requires input JSONL paths to exist.

```powershell
cd c:\workspace

# 1) Hardset — Logos map (primary clean external-news slice)
py scripts/run_logos_symbolic_event_backtest_v1.py `
  --news-jsonl docs/final/artifacts/news_observation_v1_blind_split_hardset_latest.jsonl `
  --labels-jsonl docs/final/artifacts/direction_label_bar_v1_latest.jsonl `
  --neutral-score-band 0.05 `
  --output-json docs/final/artifacts/logos_symbolic_event_backtest_reval_hardset_latest.json `
  --output-csv docs/final/artifacts/logos_symbolic_event_backtest_reval_hardset_rows_latest.csv

# 2) Hardset — counterfactual map (falsification control)
py scripts/run_logos_symbolic_event_backtest_v1.py `
  --news-jsonl docs/final/artifacts/news_observation_v1_blind_split_hardset_latest.jsonl `
  --labels-jsonl docs/final/artifacts/direction_label_bar_v1_latest.jsonl `
  --symbol-map-json docs/final/artifacts/logos_symbolic_event_map_counterfactual_v1.json `
  --neutral-score-band 0.25 `
  --output-json docs/final/artifacts/logos_symbolic_event_backtest_clean_hardset_counterfactual_reval_latest.json `
  --output-csv docs/final/artifacts/logos_symbolic_event_backtest_clean_hardset_counterfactual_reval_rows_latest.csv

# 3) Contrastive challenge (48 rows, all non_synthetic)
py scripts/run_logos_symbolic_event_backtest_v1.py `
  --news-jsonl docs/final/artifacts/news_observation_v1_contrastive_challenge_latest.jsonl `
  --labels-jsonl docs/final/artifacts/direction_label_bar_v1_contrastive_challenge_latest.jsonl `
  --neutral-score-band 0.05 `
  --output-json docs/final/artifacts/logos_symbolic_event_backtest_reval_contrastive48_latest.json `
  --output-csv docs/final/artifacts/logos_symbolic_event_backtest_reval_contrastive48_rows_latest.csv

# 4) Contrastive48 — counterfactual (optional head-to-head)
py scripts/run_logos_symbolic_event_backtest_v1.py `
  --news-jsonl docs/final/artifacts/news_observation_v1_contrastive_challenge_latest.jsonl `
  --labels-jsonl docs/final/artifacts/direction_label_bar_v1_contrastive_challenge_latest.jsonl `
  --symbol-map-json docs/final/artifacts/logos_symbolic_event_map_counterfactual_v1.json `
  --neutral-score-band 0.05 `
  --output-json docs/final/artifacts/logos_symbolic_event_backtest_clean_contrastive48_counterfactual_reval_latest.json `
  --output-csv docs/final/artifacts/logos_symbolic_event_backtest_clean_contrastive48_counterfactual_reval_rows_latest.csv

# 5) Legacy falsification slice (synthetic holdout arms — label clearly if cited)
py scripts/build_logos_falsification_contrastive_slice_v1.py `
  --logos-json docs/final/artifacts/logos_symbolic_event_backtest_benchmark_logos_real_oos_latest.json `
  --counterfactual-json docs/final/artifacts/logos_symbolic_event_backtest_benchmark_counterfactual_real_oos_latest.json `
  --iching-json docs/final/artifacts/logos_symbolic_event_backtest_benchmark_iching_real_oos_latest.json `
  --quantum-json docs/final/artifacts/logos_symbolic_event_backtest_benchmark_quantum_real_oos_latest.json `
  --output-json docs/final/artifacts/logos_falsification_contrastive_slice_latest.json

# Optional: weekly falsification benchmark task (separate artifact)
# py scripts/run_logos_falsification_benchmark_v1.py --execute --include-real-oos `
#   --output-json docs/final/artifacts/logos_weekly_revalidation_latest.json
```

After runs: refresh this doc’s summary table from the `*_latest.json` files (no hand-edited hit rates).

---

## Ten forbidden external phrases → allowed replacements

| # | Forbidden (do not headline) | Allowed replacement |
| --- | --- | --- |
| 1 | “번들 **94.9%** 적중” / “weighted **94.9%**” | “번들 가중치 **연구용**; **hardset n=27 비합성**에서 Logos **92.6%** (아티팩트 `reval_hardset`)" |
| 2 | “**real OOS 100%**” / “실전 OOS 완벽” | “holdout 벤치는 **합성 뉴스**; OOS **증명 아님** · `[HYPO]`" |
| 3 | “성경·Logos가 **시장을 예언**한다” | “**[NON_GATING]** 상징 매핑 **관측**; 방향은 라벨 대비 **백테스트**만" |
| 4 | “**Track A** / 실매매 **자동** 승격” | “**hypothesis_tier B** · Track A·주문 트리거 **미연결**" |
| 5 | “**우주 OS 완성** / 신학적 정답” | “B-track **코퍼스·게마트리아** 실험; **연구 전용**" |
| 6 | “**무손실 100%** 압축·원어 완벽” | “압축·렌즈는 **별 축**; Logos 백테스트 수치와 **합선 금지**" |
| 7 | “**locked_eval 100%** = 실전 검증” | “**n=4** 잠금 분할; **표본 작음** · 외부 hardset 전체 **92.6%**" |
| 8 | “대조군 **100%** / 이칭·양자 **0%**만으로 우월” | “`contrastive_slice`는 **합성 holdout** · contrastive48 **재실행** 수치 우선" |
| 9 | “**신경과학·장뇌**로 성과 보장” | “교육용 은유; **PUBLIC_FACING** v1.7 §3 준수" |
| 10 | “**번들 8-run** 합산 = 독립 표본” | “run 간 **labels/news 중복**; **코퍼스별** n·hit_rate만 보고" |

---

## Boundary (copy-paste one-liner)

`[B-TRACK][HYPO][research_only] hypothesis_tier=B — Logos symbolic backtest is observational; no Track A promotion, no live-trading trigger, no OOS proof from synthetic-news benchmarks.`
