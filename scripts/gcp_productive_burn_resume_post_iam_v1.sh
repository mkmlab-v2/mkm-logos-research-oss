#!/bin/bash
# Post-IAM fresh wave (P4): P3 rows were IAM errors only — do not resume at index 601.
set -euo pipefail
HOME_DIR="${HOME}"
COMPACT="${HOME_DIR}/fills_daily_compact_v1.json"
BUNDLE="${HOME_DIR}/mkm_productive_burn_bundle_v1.json"
RUNNER="${HOME_DIR}/gcp_productive_burn_lane_runner_v1.py"
LOG_DIR="${HOME_DIR}/productive_burn_logs"
ARCHIVE="${LOG_DIR}/archive_p3_iam_denied"
mkdir -p "$LOG_DIR" "$ARCHIVE"

echo "=== productive post-IAM P4 wave $(date -u -Iseconds) ==="

for pat in wave3_burn gcp_max_burn gcp_max_after_wave3 gcp_burn_watchdog gcp_burn_phase2 'gcp_burn\.sh' gcp_burn_chain gcp_productive_burn_lane_runner; do
  pkill -f "$pat" 2>/dev/null || true
done
sleep 2

if [[ ! -f "$RUNNER" ]]; then
  echo "MISSING ~/gcp_productive_burn_lane_runner_v1.py" >&2
  exit 1
fi

shopt -s nullglob
for f in "${LOG_DIR}"/*_P3a_genlang* "${LOG_DIR}"/*_P3b_fills*; do
  [[ -e "$f" ]] || continue
  echo "[archive] $f -> $ARCHIVE/"
  mv -f "$f" "$ARCHIVE/"
done
shopt -u nullglob

if [[ ! -f "$BUNDLE" ]]; then
  echo "[post-iam] building bundle"
  bash -c 'source ~/gcp_productive_burn_resume_genlang_v1.sh' 2>/dev/null || true
fi
if [[ ! -f "$BUNDLE" ]]; then
  python3 - <<'PY'
import json, os
from pathlib import Path
home = Path(os.environ["HOME"])
bundle = home / "mkm_productive_burn_bundle_v1.json"
if bundle.is_file():
    raise SystemExit(0)
compact_path = home / "fills_daily_compact_v1.json"
stub = {"fill_count": 1, "buy_fill_count": 1, "sell_fill_count": 0, "buy_sell_imbalance": 1.0,
        "maker_ratio": 0.0, "quote_qty_sum": 1000.0, "realized_pnl_sum": 0.0, "commission_sum": 0.5,
        "price_mean": 70000.0, "price_dispersion": 0.0}
compact = {"schema": "fills_daily_compact_v1",
           "daily_by_utc_date": {f"2026-05-{d:02d}": dict(stub) for d in range(1, 51)},
           "stats": {"n_fill_rows": 50, "n_daily_buckets": 50, "synthetic_fallback": True}}
compact_path.write_text(json.dumps(compact), encoding="utf-8")
TEMPLATE = ("[HYPO] research_only hypothesis_tier=B\nShadow execution analyst: given daily BTCUSDT fill aggregate JSON, "
            "output JSON only with utc_date, shadow_slippage_hypothesis, liquidity_stress_bucket, limitations[], disclaimer.\nINPUT_JSON:\n{payload}\n")
def profile_seeds(name):
    seeds = {"asset_rag": ["[HYPO] Output JSON only: RAG row for aramaic gloss placeholder with tags.",
            "[HYPO] Output JSON only: cross_lens_mapping sasang/myeongni/logos [NON_GATING].",
            "[HYPO] Output JSON only: wellness_hypothesis_card no clinical claim."],
            "cross_lens": ["[HYPO] Field=credit_expiry; resolve Final Action WATCH; research_only."]}
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
daily = compact["daily_by_utc_date"]
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
bundle_doc = {"schema": "mkm_productive_burn_bundle_v1", "hypothesis_tier": "B", "track_wall": "btrack_research_only",
          "lanes": {"btrack_fills_daily": fills[:target_fills], "asset_rag": expand_profile("asset_rag", 600),
                    "cross_lens": expand_profile("cross_lens", 400)},
          "total_prompts": min(len(fills), target_fills) + 1000}
bundle.write_text(json.dumps(bundle_doc, ensure_ascii=False), encoding="utf-8")
print("bundle_written", bundle_doc["total_prompts"])
PY
fi

pip install -q google-genai

echo "[post-iam] GCS backup archive (partial ok)"
gcloud storage cp "${ARCHIVE}"/*.jsonl "gs://gen-lang-client-burn-wave2/productive_logs/archive_p3/" 2>/dev/null || true

start_lane() {
  local lane="$1"
  local project="$2"
  local wave="$3"
  local out_jsonl="${LOG_DIR}/${lane}_${wave}.jsonl"
  local out_json="${LOG_DIR}/${lane}_${wave}_summary.json"
  if pgrep -f "gcp_productive_burn_lane_runner.*--lane ${lane}" >/dev/null 2>&1; then
    echo "[skip] lane $lane already running"
    return 0
  fi
  echo "[post-iam] lane=$lane wave=$wave start_index=1 jsonl=$out_jsonl"
  nohup python3 -u "$RUNNER" \
    --bundle "$BUNDLE" \
    --lane "$lane" \
    --project "$project" \
    --wave-id "$wave" \
    --start-index 1 \
    --out-jsonl "$out_jsonl" \
    --out-json "$out_json" \
    >>"${LOG_DIR}/${lane}_${wave}.log" 2>&1 &
  echo "[start] lane=$lane pid=$! wave=$wave"
}

start_lane "asset_rag" "gen-lang-client-0846393371" "P4a_genlang"
start_lane "btrack_fills_daily" "gen-lang-client-0846393371" "P4b_fills"

echo "=== post-IAM P4 started (cross_lens SKIPPED) ==="
pgrep -af 'gcp_productive_burn_lane_runner' || true
