# MKM digestion engine fixture — Tier 0 pilot input

**Track:** B-track · `research_only` · fixture only

## Edge results (heuristic table target)

| Work | Claim |
|------|-------|
| CE-CoLLM | 13.81% latency ↓; 84.53% cloud offload |
| NSGA-II edge router | 95.2% cloud quality; 34.9% cost ↓ |

## Digested facts

### fact_id: demo_b3_dual_plane_floor
- metric_name: dual_plane_aligned_rate
- value: 0.5
- unit: ratio
- comparison_arm: MKM_B3_floor
- verification_status: Right
- verification_method: fixture_trusted
- baseline_plane: B3_dual_plane
- artifact_path: reports/universal_root_phase1a_baseline_compare_v1_latest.json
- artifact_field: methods.B3.primary_value
- assertion: gte

### fact_id: demo_external_latency
- metric_name: latency_reduction_pct
- value: 13.81
- unit: percent
- comparison_arm: CE-CoLLM
- verification_status: Unknown
- arxiv_id: 2507.16731
