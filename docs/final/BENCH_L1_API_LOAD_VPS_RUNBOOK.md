# L1 압축 스텁 — VPS(본선) §9.2 부하 재측정 런북

**목적:** 로컬 `bench_l1_api_load_summary_latest.json`은 **루프백 RTT** 기준이다. 실서비스 SLA 후보를 고정하려면 **동일 스크립트**로 **VPS에서 관측한 RTT**(및 선택 시 동일 호스트 RSS)를 별도 아티팩트로 남긴다.

**SSH Cursor · 클론 루트(필수)**

- 기본 셸이 `/root`이면 **현재 디렉터리에 레포가 없을 수 있다.** 아래 중 하나로 해결한다.
- **A)** Cursor에서 **File → Open Folder**로 본선 **클론 루트**만 연고 터미널에서 `pwd`로 확정한 뒤 아래 블록 실행.
- **B)** 클론은 있는데 `cd`만 모를 때: `find /opt /home /var/www /srv /root -path '*/scripts/deploy/linux/run_bench_l1_api_load_vps_fixed_fields.sh' 2>/dev/null | head -1` 로 스크립트 경로를 찾은 뒤, 그 파일의 상위 `../../../..`가 레포 루트다(`scripts/deploy/linux/…` 기준). 또는 찾은 **절대 경로**로 C와 같이 `BASE_URL=… bash …/run_bench_l1_api_load_vps_fixed_fields.sh`만 실행해도 된다. 레포가 전혀 없으면 실패(D 참고).
- **C)** `run_bench_l1_api_load_vps_fixed_fields.sh`는 **스크립트 파일이 있는 위치**로부터 레포 루트를 계산하므로, **`/root`에서도** 다음처럼 **절대 경로**로 호출하면 된다:  
  `BASE_URL=http://127.0.0.1:8010 bash /실제/클론경로/scripts/deploy/linux/run_bench_l1_api_load_vps_fixed_fields.sh`  
  (이 경우 `cd`는 불필요.)
- **D)** 레포 자체가 없으면 스크립트가 존재하지 않는다. **지휘관이 쓰는 origin**으로 클론한 뒤 A~C를 따른다.
- 선택: `export MKM_WORKSPACE_ROOT=/실제/클론/루트` 후 스크립트를 **레포 밖에 복사해 둔 경우**에도 동작하게 할 수 있다.

**전제**

- VPS에 이 레포 클론, `POST /v1/compress`가 동작(예: `127.0.0.1:8010` + nginx TLS 프록시).
- 로컬과 동일 페이로드 정렬: `--approx-words 1000`, `data/personalization/mkm_user_context_v1.sample.json` 권장.

**모드**

1. **VPS 동일 호스트(권장, RSS 가능):** SSH로 VPS에서 실행. `BASE_URL=http://127.0.0.1:8010`. 선택: `BENCH_SERVER_PID`에 uvicorn/worker PID를 넣으면 `server_rss_bytes_*`가 채워진다.
2. **원격 클라이언트(RTT만):** 노트북 등에서 `BASE_URL=https://api.example.com`(실제 공개 베이스)로 `scripts/bench_l1_api_load.py`만 반복 실행. **RSS는 측정 불가**(스크립트 주석과 동일). `--bench-environment remote_client` 권장.

**원클릭(VPS Linux)**

```bash
cd /path/to/workspace   # REPO 루트
chmod +x scripts/deploy/linux/run_bench_l1_api_load_vps_fixed_fields.sh
# 선택: export BENCH_SERVER_PID=$(pgrep -f 'uvicorn.*8010' | head -1)
BASE_URL=http://127.0.0.1:8010 bash scripts/deploy/linux/run_bench_l1_api_load_vps_fixed_fields.sh
```

스크립트 동작 요약: 새 런을 `docs/final/artifacts/bench_runs/bench_l1_api_load_vps_*.json`에 쓴 뒤, **가장 마지막 런 파일을** `docs/final/artifacts/bench_l1_api_load_summary_vps_latest.json`에 복사하고, 콘솔에 `UTC`·`run`·`p95`·`error_rate`·`bench_environment`를 출력한다.

산출:

- 런 파일: `docs/final/artifacts/bench_runs/bench_l1_api_load_vps_*.json`
- 집계: `docs/final/artifacts/bench_l1_api_load_summary_vps_latest.json` (스키마는 런 파일과 동일: `bench_l1_api_load_v1`; 필드에 `bench_environment` 포함)

**수동(한 번만 쏘기)**

```bash
python3 scripts/bench_l1_api_load.py \
  --base-url "$BASE_URL" \
  --max-concurrent 50 --total-requests 300 \
  --mkm-user-context-json data/personalization/mkm_user_context_v1.sample.json \
  --bench-environment vps_same_host \
  --out docs/final/artifacts/bench_runs/manual_vps_once.json
```

**집계(`summary_vps`)만 최신 런으로 맞추기**

레포에 **다중 런 병합 전용** 집계기는 없다. `bench_runs` 아래 `bench_l1_api_load_vps_*.json` 중 **가장 최신 파일**을 수동으로 복사하거나, 동일 호스트에서 위 **원클릭**을 한 번 더 실행한다(새 측정이 부담되면 아래 한 줄만).

```bash
# 파일명에 들어 있는 UTC 타임스탬프 기준으로 가장 늦은 런(mtime이 아님 — 복사·동기화 시 안전)
latest="$(ls -1 docs/final/artifacts/bench_runs/bench_l1_api_load_vps_*.json | sort | tail -1)"
cp "$latest" docs/final/artifacts/bench_l1_api_load_summary_vps_latest.json
```

**문서 반영:** 측정 후 `P0_COMMERCIALIZATION_TRACKER.md` L2에 **VPS 스냅샷 한 줄**(날짜·`summary_vps` 경로·호스트/리전)을 추가하고, 대외 SLA 문구는 **해당 JSON의 `generated_at_utc`·git·환경**과 함께만 FACT로 쓴다.

**교차 참조:** `docs/final/SSH_CURSOR_JEMA12_DEPLOY_RUNBOOK.md`(본선 SSH), `docs/final/P0_COMMERCIALIZATION_TRACKER.md`(a-codeai nginx 분리), `COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md` §10.

---

### 팩트체크·대외 서술 (SSOT 정렬, 2026-04-10)

- **지연·RSS:** VPS/로컬 런 JSON의 **P95·RSS**는 해당 파일의 `generated_at_utc`·`command_fingerprint`와 함께만 FACT 인용. 동일 파일에 **`research_only`·`draft_benchmark`**가 있으면 **운영 SLA 최종 확정**으로 단정하지 않는다.
- **로컬 vs 본선:** `bench_l1_api_load_summary_latest.json` = 루프백/로컬 스냅샷; **본선 RTT 후보**는 `bench_l1_api_load_summary_vps_latest.json`(및 `bench_environment`).
- **P0 경로 개수:** `verify_p0_constitution_gate_paths.ps1`의 `$required` 개수는 **스크립트 변경 시 변동** — “39개” 등 고정 수치 브리핑 금지.
- **역추론 복원율:** 집계 FACT는 `l1_inverse_decoder_spike_test_summary_latest.json`의 `avg_exact_restore_rate` 등(약 **58%** 대역, 스코어링 모드 확인) — **100%**는 사이드 채널 완전 제공 시 별도 연구 스파이크로 `MKM12_L0_L1_L2_CLAIMS_TAGGED_FACTCHECK_2026-04-09.md`에 구분.
- **“24건 테스트”:** CI 스모크의 `--samples 24`는 **샘플 수**이며 pytest 건수와 혼동 금지.

---

### SSH Cursor — 복사용 (본선 클론 루트에서 실행)

`pwd`가 **레포 루트**(`.git` 존재)인지 확인한 뒤 아래를 한 블록으로 실행한다. `/root`만 열려 있으면 [SSH Cursor · 클론 루트](#ssh-cursor--클론-루트필수) 절을 먼저 따른다.

```bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
git pull origin main
chmod +x scripts/deploy/linux/run_bench_l1_api_load_vps_fixed_fields.sh
# 스텁 헬스 (HTTP 200 기대). 실패 시 BASE_URL·포트·프로세스 확인
curl -sS -o /dev/null -w "HTTP %{http_code}\n" "${BASE_URL:-http://127.0.0.1:8010}/health"
export BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"
export BENCH_ENVIRONMENT="${BENCH_ENVIRONMENT:-vps_same_host}"
# 동일 호스트 RSS까지 쓰려면 스텁 PID 지정 (선택)
# export BENCH_SERVER_PID="$(pgrep -f 'uvicorn.*8010' | head -1)"
bash scripts/deploy/linux/run_bench_l1_api_load_vps_fixed_fields.sh
test -f docs/final/artifacts/bench_l1_api_load_summary_vps_latest.json && echo "OK: summary_vps"
```

**산출 확인:** `docs/final/artifacts/bench_l1_api_load_summary_vps_latest.json` 존재 → 로컬에 `git add`·커밋 또는 Vault 보급 정책에 따름. 스키마가 `groups["50"]`를 제공하지 않으면 `latency_ms.p95`·`error_rate`·`bench_environment`를 기준으로 **P0 L2** 한 줄을 기록한다.
