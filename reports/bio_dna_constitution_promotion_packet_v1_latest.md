# Bio DNA Constitution Promotion Packet (v1)

- generated_at_utc: 2026-05-24T00:55:00Z
- readiness: `promotion_candidate_ready=true` (3/3 strict)
- cohort: **200-row real lane** (coverage 1.0, match 200/200)
- sweep: `passing_count=36/36` (200 candidate rows)
- recommended_policy: `coverage>=0.98`, `target_rows>=20`, `match_rows>=2`
- ab_policy_lock: `baseline_mode=neutral`, `source_mode=blind_replay_profiles`
- ab_seed_stability: `30/30 ready`, `ci_low_median=0.0934579439`, `uplift_median=0.2429906542`

## Evidence Paths

- `reports/bio_dna_promotion_readiness_v1_latest.json`
- `reports/bio_dna_promotion_readiness_real_lane_v1_latest.json`
- `reports/bio_dna_promotion_readiness_demo_lane_v1_latest.json`
- `reports/bio_dna_promotion_threshold_sweep_v1_latest.json`
- `reports/bio_paper_snp_mapping_coverage_autofill_v1.json`
- `reports/bio_genotype_paper_snp_overlap_v1_latest.json`
- `tmp/bio_genotype_long_v1.csv`
- `tmp/bio_real_cohort_merged_with_sidecar_v1.csv`
- `reports/bio_dna_ab_holdout_eval_v1_autobuild_latest.json`
- `reports/bio_dna_ab_neutral_seed_stability_v1.json`
- `reports/bio_dna_ab_neutral_seed_stability_v1.csv`

## Guardrails

- Synthetic data is E2E validation-only.
- Synthetic outputs are not promotion evidence.
- **Track A / live trading auto-promotion forbidden.**
- A/B uplift statements are restricted to research holdout scope.

## Decision Hint

- B-track research promotion: **complete** (commander approval 2026-05-24)
- Constitution update candidate: yes
- Live / operational promotion still requires separate human review.
