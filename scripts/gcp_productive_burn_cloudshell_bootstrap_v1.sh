#!/bin/bash
# Bootstrap productive burn on Cloud Shell: build bundle from compact fills + start lanes.
set -euo pipefail
COMPACT="${HOME}/fills_daily_compact_v1.json"
RUNNER="${HOME}/gcp_productive_burn_lane_runner_v1.py"
BUNDLE="${HOME}/mkm_productive_burn_bundle_v1.json"
LOG_DIR="${HOME}/productive_burn_logs"
mkdir -p "$LOG_DIR"

echo "=== productive bootstrap $(date -u -Iseconds) ==="

for pat in wave3_burn gcp_max_burn gcp_max_after_wave3 gcp_burn_watchdog gcp_burn_phase2 'gcp_burn\.sh' gcp_burn_chain; do
  pkill -f "$pat" 2>/dev/null || true
done
sleep 2

pip install -q google-genai

python3 <<'PY'
import json, os
from pathlib import Path

home = Path(os.environ["HOME"])
compact_path = home / "fills_daily_compact_v1.json"
compact = json.loads(compact_path.read_text(encoding="utf-8"))
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
    out = []
    i = 0
    while len(out) < count:
        base = seeds[i % len(seeds)]
        idx = len(out) + 1
        out.append({
            "lane": profile,
            "prompt_profile": profile,
            "index": idx,
            "prompt": f"{base}\n\n[burn-meta] profile={profile} index={idx}/{count}",
        })
        i += 1
    return out

fills = []
dates = sorted(daily.keys())
repeat = 4
target_fills = 200
for rep in range(repeat):
    for d in dates:
        row = daily.get(d)
        if not isinstance(row, dict):
            continue
        payload = {"utc_date": d, **row}
        fills.append({
            "lane": "btrack_fills_daily",
            "utc_date": d,
            "prompt_profile": "btrack_fills_daily",
            "prompt": TEMPLATE.format(payload=json.dumps(payload, ensure_ascii=False)) + f"\n[burn-meta] date={d} rep={rep+1}",
        })
        if len(fills) >= target_fills:
            break
    if len(fills) >= target_fills:
        break

bundle = {
    "schema": "mkm_productive_burn_bundle_v1",
    "generated_at_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "hypothesis_tier": "B",
    "track_wall": "btrack_research_only",
    "lanes": {
        "btrack_fills_daily": fills[:target_fills],
        "asset_rag": expand_profile("asset_rag", 600),
        "cross_lens": expand_profile("cross_lens", 400),
    },
    "total_prompts": min(len(fills), target_fills) + 600 + 400,
}
(home / "mkm_productive_burn_bundle_v1.json").write_text(
    json.dumps(bundle, ensure_ascii=False), encoding="utf-8"
)
print("bundle_written", bundle["total_prompts"])
PY

if [[ -x "${HOME}/gcp_productive_burn_resume_genlang.sh" ]]; then
  bash "${HOME}/gcp_productive_burn_resume_genlang.sh"
elif [[ -f "${HOME}/gcp_productive_burn_deploy.sh" ]]; then
  bash "${HOME}/gcp_productive_burn_deploy.sh"
else
  echo "MISSING deploy/resume scripts" >&2
  exit 1
fi

echo "=== bootstrap done ==="
pgrep -af gcp_productive || true
