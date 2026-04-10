# Gematria Engineering Reproducibility Fact Check (2026-04-09)

## 3-sentence Brief
This memo validates which claims are currently supported by repository artifacts versus claims that still require additional engineering evidence.  
The core thesis is partially validated: quaternion-based order sensitivity and low determinism spread are evidenced, but Reed-Solomon and LLM-constrained unique decoding are not yet evidenced in code/artifacts.  
For academic credibility, MKM12 should present this as a research-stage reproducibility stack with explicit boundaries, not as a finalized universal scientific proof.

## Scope and Method
- Scope: workspace-local code and artifact fact check only.
- Method: trace each claim to executable scripts and JSON outputs under `scripts/` and `docs/final/artifacts/`.
- Rule: no claim is marked "verified" unless a concrete path and value are present.

## Claim-by-Claim Verdict

### 1) "학계 불신의 원인: 끼워맞추기/비표준/순서 손실"
- **Verdict:** Directionally valid as methodology critique; not yet externally cited in this memo.
- **Evidence status:** internal reasoning valid, external literature citation absent.
- **Action:** keep as "engineering diagnosis" wording unless external references are added.

### 2) "사원수(해밀턴 곱)로 순서 정보 보존"
- **Verdict:** Verified.
- **Code evidence:** `scripts/run_trackb_quaternion_word_order_experiment.py` implements quaternion multiplication (`_qmul`) and sequence encode loop.
- **Artifact evidence:** `docs/final/artifacts/trackb_quaternion_order_experiment_v1.json` shows:
  - `collision_rate: 0.0`
  - `pair_decode_exact_rate: 1.0`
- **Boundary note:** artifact itself marks this as R&D exploratory and closed-candidate nearest-neighbor decode.

### 3) "`determinism_delta: 0.0033` 재현성 근거"
- **Verdict:** Verified (research metric).
- **Artifact evidence:** `docs/final/artifacts/gematria_4d_quaternion_research_eval_result_latest.json`
  - `determinism_delta: 0.0033333333333332993`
- **Boundary note:** same artifact includes `research_only: true` and notes no deterministic prediction accuracy claim.

### 4) "리드-솔로몬 오류 정정 적용"
- **Verdict:** Not verified in current repository scan.
- **Evidence status:** no direct implementation markers found for Reed-Solomon/FEC parity-syndrome pipeline in scanned paths.
- **Action:** treat as planned/hypothesis until script path + artifact are produced.

### 5) "LLM 제약 조건으로 유일 정답 강제, 99.9% 결정론"
- **Verdict:** Not verified as stated.
- **Evidence status:** current Track B decode path is candidate/beam/heuristic search; no direct LLM-constrained unique decoder evidence in verified paths.
- **Action:** downgrade wording to "constraint-guided candidate reconstruction in research bench."

## Safe Public Wording (Recommended)
MKM12 currently demonstrates reproducible research signals for order-sensitive encoding and stable decoding metrics in a bounded benchmark setting.  
Results are promising but remain research-stage: Reed-Solomon error-correction integration and externally reproducible, open-benchmark validation are pending.  
Therefore, current outputs should be communicated as engineering evidence under controlled conditions, not as universal finalized scientific proof.

## Immediate Experimental Upgrade (for mirror)
- **Experiment name:** Intentional noise injection and forced recovery test.
- **Protocol:** introduce token-order swaps and typo/OOV perturbations, then measure detection/recovery pass rate and exact-sequence restoration rate.
- **Required outputs (minimum):**
  - reproducible script path
  - fixed seed list
  - artifact JSON with schema/version
  - failure-case JSONL
  - delta vs baseline table
- **Promotion gate (draft):**
  - deterministic rerun spread threshold
  - minimum exact-sequence recovery threshold
  - explicit "research_only vs production" flag retained

## Spike Test Update (2026-04-09, v1.1; aggregate aligned to latest summary JSON, 2026-04-10)
- **Critical correction:** previous spike scoring leaked hidden source embedding; this was fixed to decode against `noisy_observation` only.
- **Script:** `scripts/run_l1_inverse_decoder_spike_test.py` (`schema: l1_inverse_decoder_spike_test_v1_1`).
- **Summary artifact (SSOT for numbers):** `docs/final/artifacts/l1_inverse_decoder_spike_test_summary_latest.json` (`generated_at_utc: 2026-04-10T00:01:38+00:00`).
- **Snapshot run profile (from that artifact):** seeds `701,809,907`, noise levels `0.1,0.2`, `samples_per_cell=180`, `beam_size=4`, `scoring_mode: legacy`.
- **Observed aggregate (same file):**
  - `avg_exact_restore_rate: 0.5787037037037037`
  - `min_exact_restore_rate: 0.5388888888888889`
  - `max_exact_restore_rate: 0.6166666666666667`
  - `determinism_delta: 0.04166666666666674`
- **Interpretation:** this is an honest baseline after leakage removal; "100% restoration" is not supported under noisy-observation-only decoding in this spike. (Separately, `run_l1_permutation_channel_integrated_spike.py` achieves `1.0` when full side-channel metadata is attached — research harness; not LLM beam.)
- **Wire / HTTP (dev mirror, not product compress):** `scripts/l1_side_channel_wire_codec.py` + `POST /v1/research/l1_side_channel/wire` on `scripts/compression_token_api_stub.py` (OpenAPI `openapi_token_compression_stub_v1.yaml` v1.1.0; 503 if msgpack missing/unavailable). Fact-Lock cross-refs: `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §2, `COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md` §10.
- **B-track → Track A / production promotion (compression lane):** formal checklist SSOT is `docs/final/COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md` §9; commercialization row in `docs/final/P0_COMMERCIALIZATION_TRACKER.md`. OOV / BERTScore / Mamba-style forward benches stay **research tasks** outside §9 until separately scoped.

## External Citation Mapping (Patch for Residual Risk)
- Goal: attach academically recognized methods to each `[HYPO]` while preserving Fact-Lock wording.
- Rule: only verified links/titles are listed as `[FACT]`; unresolved names remain `[VERIFY]`.

### A) Constrained decoding / unique-solution search
- **[FACT]** Koo et al., *Automata-based constraints for language model decoding* (arXiv:2407.08103).  
  Link: [arXiv](https://arxiv.org/html/2407.08103v1)
- **[FACT]** *ABS: Enforcing Constraint Satisfaction On Generated Sequences Via Automata-Guided Beam Search* (arXiv:2506.09701).  
  Link: [arXiv](https://arxiv.org/abs/2506.09701)
- **[FACT]** Hokamp & Liu, *Lexically Constrained Decoding for Sequence Generation Using Grid Beam Search* (ACL 2017).  
  Link: [ACL Anthology](https://aclanthology.org/P17-1141/)
- **[VERIFY]** "ATLAS 2025 real-time constraint enforcement" exact bibliographic match not confirmed in current pass.
- **[VERIFY]** "GD-RIPOR globally-guided constrained beam search" exact bibliographic match not confirmed in current pass.

### B) Reed-Solomon / ECC integrity path
- **[FACT]** Xie et al., *Making Strong Error-Correcting Codes Work Effectively for HBM in AI Inference* (arXiv:2512.18152).  
  Link: [dblp entry](https://dblp.org/rec/journals/corr/abs-2512-18152)
- **[FACT]** General ECC comparison (Hamming vs RS vs LDPC) available as engineering overviews; use only as secondary context, not primary proof.

### C) Geometric positional/topological embedding support
- **[FACT]** *GeoPE: A Unified Geometric Positional Embedding for Structured Tensors* (arXiv:2512.04963).  
  Link: [arXiv HTML](https://arxiv.org/html/2512.04963v1)
- **[FACT]** *From Topology to Retrieval: Decoding Embedding Spaces with Unified Signatures* (arXiv:2511.22150).  
  Link: [arXiv](https://arxiv.org/abs/2511.22150)
- **[FACT]** *Topological Metric for Unsupervised Embedding Quality Evaluation* (arXiv:2512.15285).  
  Link: [arXiv HTML](https://arxiv.org/html/2512.15285v1)

### Suggested insertion sentence (external-facing safe)
The constrained-decoding and geometric-embedding components are aligned with recent automata-guided beam-search and topology-aware embedding literature; however, RS/ECC coupling in MKM12 remains a pending implementation item until a repository-traceable script and artifact are published.

## Source Paths (Fact Anchors)
- `scripts/run_trackb_quaternion_word_order_experiment.py`
- `docs/final/artifacts/trackb_quaternion_order_experiment_v1.json`
- `scripts/run_gematria_4d_quaternion_research_eval_set_v1.py`
- `docs/final/artifacts/gematria_4d_quaternion_research_eval_result_latest.json`
- `scripts/run_trackb_quaternion_generalization_bench_v6.py`
- `scripts/run_l1_inverse_decoder_spike_test.py` (Day 6-8 spike harness)

## Final Operational Note
This memo closes the "overstatement risk" by separating verified evidence from pending claims.  
NotebookLM mirror should ingest this memo as the current SSOT wording baseline for external-facing technical explanation.
