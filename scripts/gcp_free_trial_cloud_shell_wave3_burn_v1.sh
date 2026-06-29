#!/bin/bash
# Paste into Google Cloud Shell (project=gen-lang-client-0846393371, jema12@mkmlife.com).
# Free Trial billing 010B19-239742-DAF438 — Vertex gemini-2.5-pro quota_stress burn.
set -euo pipefail
CALLS="${1:-500}"
WAVE="${2:-wave3}"
LOG="$HOME/gcp_burn_${WAVE}_$(date -u +%Y%m%dT%H%M%SZ).log"
exec > >(tee -a "$LOG") 2>&1
echo "=== GCP Free Trial burn start wave=$WAVE calls=$CALLS $(date -u -Iseconds) ==="
gcloud config set project gen-lang-client-0846393371 --quiet
pip install -q google-genai
python3 <<'PY'
import os, sys, time, uuid
from datetime import datetime, timezone

CALLS = int(os.environ.get("BURN_CALLS", "500"))
WAVE = os.environ.get("BURN_WAVE", "wave3")
PROJECT = "gen-lang-client-0846393371"
LOCATION = "us-central1"
MODEL = "gemini-2.5-pro"
MAX_OUT = 8192

PROMPTS = [
    "Write exactly 800 words on cloud cost optimization patterns (filler for throughput).",
    "Write exactly 800 words on RAG chunking strategies for multilingual corpora (filler for throughput).",
]

def utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

from google import genai
from google.genai import types

client = genai.Client(vertexai=True, project=PROJECT, location=LOCATION)
run_id = str(uuid.uuid4())
ok = fail = 0
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
        print(f"[{utc()}] {i}/{CALLS} ok chars={len(text)} ms={ms}", flush=True)
    except Exception as e:
        ms = round((time.perf_counter() - t0) * 1000, 1)
        fail += 1
        print(f"[{utc()}] {i}/{CALLS} ERR ms={ms} {str(e)[:200]}", flush=True)
    if i % 25 == 0 or i == CALLS:
        print(f"[progress] ok={ok} fail={fail} run_id={run_id}", flush=True)
    time.sleep(0.1)
print(f"DONE ok={ok} fail={fail} run_id={run_id}", flush=True)
sys.exit(0 if fail == 0 else 1)
PY
echo "=== burn finished exit=$? log=$LOG ==="
