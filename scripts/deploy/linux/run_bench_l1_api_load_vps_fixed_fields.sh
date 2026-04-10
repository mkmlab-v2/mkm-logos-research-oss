#!/usr/bin/env bash
set -euo pipefail

# Run L1 API bench and print fixed reporting fields:
# UTC / run / p95 / error_rate / bench_environment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "${REPO_ROOT}"

BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"
BENCH_ENVIRONMENT="${BENCH_ENVIRONMENT:-vps_same_host}"
MKM_USER_CONTEXT_JSON="${MKM_USER_CONTEXT_JSON:-data/personalization/mkm_user_context_v1.sample.json}"
MAX_CONCURRENT="${MAX_CONCURRENT:-50}"
TOTAL_REQUESTS="${TOTAL_REQUESTS:-300}"
APPROX_WORDS="${APPROX_WORDS:-1000}"

RUN_TS="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_OUT="docs/final/artifacts/bench_runs/bench_l1_api_load_vps_${RUN_TS}.json"
SUMMARY_OUT="docs/final/artifacts/bench_l1_api_load_summary_vps_latest.json"

if [[ "${SKIP_HEALTHCHECK:-0}" != "1" ]]; then
  curl -sS -o /dev/null -w "HTTP %{http_code}\n" "${BASE_URL}/health"
fi

if [[ "${DRY_RUN:-0}" == "1" ]]; then
  python3 scripts/bench_l1_api_load.py \
    --dry-run \
    --bench-environment "${BENCH_ENVIRONMENT}" \
    --out "${RUN_OUT}"
else
  python3 scripts/bench_l1_api_load.py \
    --base-url "${BASE_URL}" \
    --max-concurrent "${MAX_CONCURRENT}" \
    --total-requests "${TOTAL_REQUESTS}" \
    --approx-words "${APPROX_WORDS}" \
    --mkm-user-context-json "${MKM_USER_CONTEXT_JSON}" \
    --bench-environment "${BENCH_ENVIRONMENT}" \
    --out "${RUN_OUT}"
fi

if [[ "${DRY_RUN:-0}" != "1" ]]; then
  cp "${RUN_OUT}" "${SUMMARY_OUT}"
fi

python3 - <<'PY'
import json
from pathlib import Path
import os

p = Path("docs/final/artifacts/bench_l1_api_load_summary_vps_latest.json")
d = json.loads(p.read_text(encoding="utf-8"))
utc = d.get("generated_at_utc")
run = d.get("command_fingerprint", {}).get("argv", [])
bench_environment = d.get("bench_environment")
p95 = (d.get("latency_ms") or {}).get("p95")
error_rate = d.get("error_rate")

run_name = None
if "--out" in run:
    idx = run.index("--out")
    if idx + 1 < len(run):
        run_name = Path(run[idx + 1]).name
if run_name is None:
    run_name = Path(os.environ.get("RUN_OUT", "unknown")).name

print(f"UTC={utc}")
print(f"run={run_name or 'unknown'}")
print(f"p95={p95}")
print(f"error_rate={error_rate}")
print(f"bench_environment={bench_environment}")
PY

