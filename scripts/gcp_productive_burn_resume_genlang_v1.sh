#!/bin/bash
# Resume gen-lang productive lanes only; stop filler; skip artful cross_lens.
set -euo pipefail
HOME_DIR="${HOME}"
COMPACT="${HOME_DIR}/fills_daily_compact_v1.json"
BUNDLE="${HOME_DIR}/mkm_productive_burn_bundle_v1.json"
RUNNER="${HOME_DIR}/gcp_productive_burn_lane_runner_v1.py"
LOG_DIR="${HOME_DIR}/productive_burn_logs"
mkdir -p "$LOG_DIR"

echo "=== productive resume gen-lang $(date -u -Iseconds) ==="

for pat in wave3_burn gcp_max_burn gcp_max_after_wave3 gcp_burn_watchdog gcp_burn_phase2 'gcp_burn\.sh' gcp_burn_chain; do
  pkill -f "$pat" 2>/dev/null || true
done
sleep 2
echo "[resume] filler/watchdog stopped"

if [[ ! -f "$RUNNER" ]]; then
  echo "MISSING ~/gcp_productive_burn_lane_runner_v1.py — paste install step 1 first" >&2
  exit 1
fi
if [[ ! -f "$BUNDLE" ]]; then
  echo "[resume] building bundle (compact fills or synthetic fallback)"
  python3 - <<'PY'
import json, os
from pathlib import Path
home = Path(os.environ["HOME"])
compact_path = home / "fills_daily_compact_v1.json"
if compact_path.is_file():
    compact = json.loads(compact_path.read_text(encoding="utf-8"))
else:
    stub = {
        "fill_count": 1, "buy_fill_count": 1, "sell_fill_count": 0,
        "buy_sell_imbalance": 1.0, "maker_ratio": 0.0, "quote_qty_sum": 1000.0,
        "realized_pnl_sum": 0.0, "commission_sum": 0.5, "price_mean": 70000.0,
        "price_dispersion": 0.0,
    }
    compact = {
        "schema": "fills_daily_compact_v1",
        "daily_by_utc_date": {f"2026-05-{d:02d}": dict(stub) for d in range(1, 51)},
        "stats": {"n_fill_rows": 50, "n_daily_buckets": 50, "synthetic_fallback": True},
    }
    compact_path.write_text(json.dumps(compact), encoding="utf-8")
daily = compact.get("daily_by_utc_date") or {}
TEMPLATE = (
    "[HYPO] research_only hypothesis_tier=B\n"
    "Shadow execution analyst: given daily BTCUSDT fill aggregate JSON, output JSON only "
    "with utc_date, shadow_slippage_hypothesis, liquidity_stress_bucket, limitations[], disclaimer.\n"
    "INPUT_JSON:\n{payload}\n"
)
def profile_seeds(name):
    seeds = {
        "asset_rag": [
            "[HYPO] Output JSON only: RAG row for aramaic gloss placeholder with tags.",
            "[HYPO] Output JSON only: cross_lens_mapping sasang/myeongni/logos [NON_GATING].",
            "[HYPO] Output JSON only: wellness_hypothesis_card no clinical claim.",
        ],
        "cross_lens": [
            "[HYPO] Field=credit_expiry; resolve Final Action WATCH; research_only.",
            "[HYPO] Compare filler burn vs JSONL assetization — markdown table.",
        ],
    }
    return seeds.get(name, seeds["asset_rag"])
def expand_profile(profile, count):
    seeds = profile_seeds(profile)
    out, i = [], 0
    while len(out) < count:
        base = seeds[i % len(seeds)]
        idx = len(out) + 1
        out.append({"lane": profile, "prompt_profile": profile, "index": idx,
                    "prompt": f"{base}\n\n[burn-meta] profile={profile} index={idx}/{count}"})
        i += 1
    return out
fills, dates, target_fills = [], sorted(daily.keys()), 200
for rep in range(4):
    for d in dates:
        row = daily.get(d)
        if not isinstance(row, dict):
            continue
        payload = {"utc_date": d, **row}
        fills.append({"lane": "btrack_fills_daily", "utc_date": d, "prompt_profile": "btrack_fills_daily",
                      "prompt": TEMPLATE.format(payload=json.dumps(payload, ensure_ascii=False)) + f"\n[burn-meta] date={d} rep={rep+1}"})
        if len(fills) >= target_fills:
            break
    if len(fills) >= target_fills:
        break
bundle = {"schema": "mkm_productive_burn_bundle_v1", "hypothesis_tier": "B", "track_wall": "btrack_research_only",
          "lanes": {"btrack_fills_daily": fills[:target_fills], "asset_rag": expand_profile("asset_rag", 600),
                    "cross_lens": expand_profile("cross_lens", 400)},
          "total_prompts": min(len(fills), target_fills) + 1000}
(home / "mkm_productive_burn_bundle_v1.json").write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
print("bundle_written", bundle["total_prompts"])
PY
fi

pip install -q google-genai

echo "[resume] GCS backup (partial ok)"
gcloud storage cp "${LOG_DIR}"/*.jsonl "gs://gen-lang-client-burn-wave2/productive_logs/" 2>/dev/null || true
gcloud storage cp "${LOG_DIR}"/*_summary.json "gs://gen-lang-client-burn-wave2/productive_logs/" 2>/dev/null || true

compute_start_index() {
  local jsonl="$1"
  python3 - "$jsonl" <<'PY'
import json, sys
path = sys.argv[1]
mx = 0
try:
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                mx = max(mx, int(json.loads(line).get("index", 0)))
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
except FileNotFoundError:
    print(1)
    raise SystemExit(0)
print(mx + 1 if mx else 1)
PY
}

start_lane() {
  local lane="$1"
  local project="$2"
  local wave="$3"
  local out_jsonl="${LOG_DIR}/${lane}_${wave}.jsonl"
  local out_json="${LOG_DIR}/${lane}_${wave}_summary.json"
  local start_idx
  start_idx="$(compute_start_index "$out_jsonl")"
  if pgrep -f "gcp_productive_burn_lane_runner.*--lane ${lane}" >/dev/null 2>&1; then
    echo "[skip] lane $lane already running"
    return 0
  fi
  echo "[resume] lane=$lane start_index=$start_idx jsonl=$out_jsonl"
  nohup python3 -u "$RUNNER" \
    --bundle "$BUNDLE" \
    --lane "$lane" \
    --project "$project" \
    --wave-id "$wave" \
    --start-index "$start_idx" \
    --out-jsonl "$out_jsonl" \
    --out-json "$out_json" \
    >>"${LOG_DIR}/${lane}_${wave}.log" 2>&1 &
  echo "[start] lane=$lane pid=$! from_index=$start_idx"
}

start_lane "asset_rag" "gen-lang-client-0846393371" "P3a_genlang"
start_lane "btrack_fills_daily" "gen-lang-client-0846393371" "P3b_fills"

echo "=== resume done (cross_lens SKIPPED) ==="
pgrep -af 'gcp_productive_burn_lane_runner|gcp_burn' || true
