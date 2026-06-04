# nextgen_clean_slate_cpu_v1 (B-track · research_only)

**Purpose:** GPU/CUDA 없이 CPU 멀티스레드 + (선택) 보조 PC RAM 샤딩 PoC. Track A·Golden-40 **비호환** 독립 baseline.

**격벽:** `research_only: true` · `track_a_active_write: false` · ACTIVE/MS/실매매 **0 합선**

**Parent charter:** `reports/btrack_nextgen_indexer_charter_v1_latest.json` · arm `nextgen_latent_indexer`

## Entry (Windows)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-NextGenCleanSlateCpuSandbox_v1.ps1
```

## Entry (Python)

```text
py scripts/run_nextgen_clean_slate_cpu_sandbox_chain_v1.py --execute
py scripts/run_nextgen_clean_slate_cpu_sandbox_chain_v1.py --execute --skip-aux-deploy
py scripts/run_nextgen_clean_slate_cpu_sandbox_chain_v1.py --dry-run
```

## Aux PC RTT (2-PC)

1. 보조 PC: `py scripts/run_nextgen_clean_slate_cpu_rtt_probe_v1.py --mode server --port 19876`
2. 메인 PC: `py scripts/run_nextgen_clean_slate_cpu_sandbox_chain_v1.py --execute --aux-host AUX_IP`

## Outputs

| Artifact | Role |
|----------|------|
| `topology_spec_v1_latest.json` | 호스트·샤딩·지연 게이트 SSOT |
| `results/rtt_probe_v1_latest.json` | LAN/loopback RTT p50/p95 |
| `results/p0_microbench_v1_latest.json` | 단일 호스트 CPU 병렬 lookup |
| `results/p1_shard_ping_v1_latest.json` | 샤드 블록 전송+원격 digest |
| `results/nextgen_neural_baseline_v1_latest.json` | NG 전용 baseline (Golden-40 비호환) |

## Phases

| Phase | Script | Goal |
|-------|--------|------|
| T0 | `build_nextgen_clean_slate_cpu_topology_v1.py` | 토폴로지·측정 프로토콜 |
| T1 | `run_nextgen_clean_slate_cpu_rtt_probe_v1.py` | RTT 실측 (#5 모름 해소) |
| P0 | `run_nextgen_clean_slate_cpu_p0_microbench_v1.py` | CPU-only 병렬 micro-bench |
| P1 | `run_nextgen_clean_slate_cpu_p1_shard_ping_v1.py` | 분산 샤드 ping (en_tech shard 패턴) |
| P2 | `run_nextgen_latent_indexer_stub_ng40_shadow_v1.py` | Golden-40 shadow (stub; same 40 cases) |

**Promotion:** beat frozen Golden-40 + human sign-off 전 **41k/31k 폐기·ACTIVE 갱신 금지**.
