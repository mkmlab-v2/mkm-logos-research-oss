# Global Atom Corpus-Fact Brief v1

## 1) Corpus Profile (원재료 선언)
- `corpus_profile_id`: `<canon_only_v1 | canon_plus_deuterocanon_v1 | canon_plus_dss_apocrypha_v1>`
- `profile_source`: `docs/final/artifacts/global_atom_corpus_profiles_v1.json`
- `scope`: `<research_only | promotion_required>`

## 2) Snapshot Fact (Anchor)
- `anchor_freeze_id`: `<e.g., global_atom_submission_20260428T095850Z>`
- `anchor_edge_count`: `<e.g., 3051269>`
- `anchor_node_count`: `<e.g., 7477>`
- `anchor_source_path`: `<freeze onepager path>`
- `anchor_hash_sha256`: `<sha256>`

## 3) Current Reference (Latest)
- `current_edge_count`: `<e.g., 19690345>`
- `current_node_count`: `<e.g., 11573>`
- `current_source_path`: `<latest onepager path>`

## 4) Delta (변화량)
- `latest_minus_anchor_edge`: `<e.g., 16639076>`
- `edge_ratio_latest_over_anchor`: `<e.g., 6.45>`

## 5) Integrity Checks (기계 검증)
- `claim_lock_check`:
  - `py scripts/check_global_atom_claim_lock_v1.py --strict`
- `atom_set_check`:
  - `py scripts/check_global_atom_edge_claim_atom_set_v1.py --strict`
- `corpus_profile_check`:
  - `py scripts/check_global_atom_corpus_profile_lock_v1.py --strict`
- `result`: `<PASS | FAIL>` + `<checked_at_utc>`

## 6) Allowed Claim / Forbidden Claim
- Allowed:
  - "본 수치는 `<corpus_profile_id>` + `<anchor_freeze_id>` 기준 스냅샷 사실입니다."
- Forbidden:
  - "이 숫자는 모든 시점/모든 코퍼스에 항상 동일한 절대 진실입니다."
  - "이 숫자 단독으로 상용 성능을 보장합니다."

## 7) Reproducibility (재현)
- `commands`:
  - `<repro command 1>`
  - `<repro command 2>`
- `artifacts`:
  - `<core artifact path list>`
