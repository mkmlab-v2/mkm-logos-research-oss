#!/bin/bash
# Google Cloud Shell — Free Trial Vertex burn (jema12@mkmlife.com).
# Billing 010B19-239742-DAF438 — eligible projects ONLY (no extra billing).
# Usage: bash gcp_free_trial_cloud_shell_burn_v1.sh <calls> <wave_id> [project_id]
set -euo pipefail
CALLS="${1:-500}"
WAVE="${2:-wave3}"
PROJECT="${3:-gen-lang-client-0846393371}"
ALLOWED_RE='^(gen-lang-client-0846393371|artful-athlete-490017-k3)$'
if ! [[ "$PROJECT" =~ $ALLOWED_RE ]]; then
  echo "REFUSE project=$PROJECT not in Free Trial allowlist" >&2
  exit 2
fi
LOG="$HOME/gcp_burn_${WAVE}_$(date -u +%Y%m%dT%H%M%SZ).log"
export BURN_CALLS="$CALLS"
export BURN_WAVE="$WAVE"
export BURN_PROJECT="$PROJECT"
export BURN_MAX_BILLING_FAILS="${BURN_MAX_BILLING_FAILS:-3}"
exec > >(tee -a "$LOG") 2>&1
echo "=== GCP Free Trial burn start wave=$WAVE calls=$CALLS project=$PROJECT $(date -u -Iseconds) ==="
gcloud config set project "$PROJECT" --quiet
pip install -q google-genai
python3 <<'PY'
import os, sys, time, uuid
from datetime import datetime, timezone

ALLOWED = frozenset({"gen-lang-client-0846393371", "artful-athlete-490017-k3"})
BILLING_HINTS = (
    "billing", "BILLING", "billing account", "payment", "PAYMENT",
    "insufficient", "QUOTA_EXCEEDED", "RESOURCE_EXHAUSTED",
    "Spending limit", "budget", "BUDGET",
)

CALLS = int(os.environ["BURN_CALLS"])
WAVE = os.environ["BURN_WAVE"]
PROJECT = os.environ["BURN_PROJECT"]
MAX_BILLING_FAILS = int(os.environ.get("BURN_MAX_BILLING_FAILS", "3"))
LOCATION = "us-central1"
MODEL = "gemini-2.5-pro"
MAX_OUT = 8192

if PROJECT not in ALLOWED:
    print(f"REFUSE project={PROJECT} not in allowlist", flush=True)
    sys.exit(2)

PROMPTS = [
    "Write exactly 800 words on cloud cost optimization patterns (filler for throughput).",
    "Write exactly 800 words on RAG chunking strategies for multilingual corpora (filler for throughput).",
]

def utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def billing_like(msg: str) -> bool:
    m = msg.lower()
    return any(h.lower() in m for h in BILLING_HINTS)

from google import genai
from google.genai import types

client = genai.Client(vertexai=True, project=PROJECT, location=LOCATION)
run_id = str(uuid.uuid4())
ok = fail = billing_fails = 0
stopped_billing_guard = False
for i in range(1, CALLS + 1):
    prompt = PROMPTS[(i - 1) % len(PROMPTS)] + f"\n\n[burn-meta] {WAVE} index={i}/{CALLS}"
    t0 = time.perf_counter()
    try:
        r = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=MAX_OUT, temperature=0.2),
        )
        text = (getattr(r, "text", None) or "").strip()
        ms = round((time.perf_counter() - t0) * 1000, 1)
        ok += 1
        billing_fails = 0
        print(f"[{utc()}] {i}/{CALLS} ok chars={len(text)} ms={ms}", flush=True)
    except Exception as e:
        ms = round((time.perf_counter() - t0) * 1000, 1)
        fail += 1
        err = str(e)
        print(f"[{utc()}] {i}/{CALLS} ERR ms={ms} {err[:200]}", flush=True)
        if billing_like(err):
            billing_fails += 1
            print(f"[billing_guard] consecutive={billing_fails}/{MAX_BILLING_FAILS}", flush=True)
            if billing_fails >= MAX_BILLING_FAILS:
                print(f"STOP_BILLING_GUARD ok={ok} fail={fail} run_id={run_id}", flush=True)
                stopped_billing_guard = True
                break
    if i % 25 == 0 or i == CALLS:
        print(f"[progress] ok={ok} fail={fail} run_id={run_id}", flush=True)
    time.sleep(0.1)
status = "STOPPED_BILLING_GUARD" if stopped_billing_guard else "DONE"
print(f"{status} ok={ok} fail={fail} run_id={run_id}", flush=True)
sys.exit(0 if (fail == 0 or stopped_billing_guard) else 1)
PY
echo "=== burn finished exit=$? log=$LOG ==="
