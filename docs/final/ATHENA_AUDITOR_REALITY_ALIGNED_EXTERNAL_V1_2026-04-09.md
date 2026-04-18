# Athena Auditor — Reality-Aligned External Brief (v1, 2026-04-09)

**Audience:** Defense-facing technical reviewers, partners, and procurement due diligence.  
**Scope:** Messaging guardrails and SSOT citation rules. Not a product warranty or trading performance claim.

## Summary (EN)

MKM12 compression and restoration work is presented as a **hybrid risk-control system** with **reproducible JSON artifacts**. Claims about **lossless reconstruction**, **full RS/ECC integration**, or **deterministic 100% restoration across all payloads** must not be stated as current production fact. Internal research names (e.g. gematria/quaternion axes) should be translated to **neutral engineering language** in external documents; see `docs/final/artifacts/defense_code_pack_v1.json` and derived `defense_pitch_codepack_v1.json`.

## Anchored facts (always cite paths + fields)

- L1 beam inverse decoder spike aggregate exact-restore rate (research harness):  
  `docs/final/artifacts/l1_inverse_decoder_spike_test_summary_latest.json` → check `aggregate.avg_exact_restore_rate`, `research_only`, `generated_at_utc`.
- Side-channel deterministic exact restore (when metadata is complete):  
  `docs/final/artifacts/l1_permutation_channel_integrated_spike_latest.json`.
- Multilens operational / literal tracks:  
  `docs/final/COMPRESSION_SLA_POLICY_V1.md`.

## Do not claim externally

- “100% lossless literal restoration” for the full pipeline without a scoped benchmark and contract.
- “Quaternion / 4D math alone achieves X% byte compression” without a cited, reproducible artifact.
- NotebookLM or slide decks as **sole** evidence for promotion gates (see MKM12 L0/L1/L2 factcheck).

## Alignment

This brief is consistent with `docs/final/MKM12_L0_L1_L2_CLAIMS_TAGGED_FACTCHECK_2026-04-09.md` section C (외부 공유용 안전 문안). Updates to numeric claims follow artifact drift rules in that document.
