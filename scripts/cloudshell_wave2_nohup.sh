#!/usr/bin/env bash
# Cloud Shell (gen-lang-client-0846393371) — Wave 2 assetization burn.
set -euo pipefail
pip install -q google-genai
nohup python3 -u <<'PY' > ~/mkm_burn_wave2.log 2>&1 &
from google import genai
from google.genai import types
import json, time, uuid
from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

SEEDS = [
    "[HYPO] Output JSON only: cross_lens_mapping sasang/myeongni/logos [NON_GATING] research_only tier B.",
    "[HYPO] Output JSON only: wellness_hypothesis_card — no clinical claim, limitations required.",
    "[HYPO] Output JSON only: RAG row for aramaic gloss placeholder shalom with tags.",
    "[HYPO] Output JSON only: quota_stress_metadata rpm latency error_class example.",
    "[HYPO] Field=credit_expiry; resolve Final Action WATCH with 3 bullets; research_only.",
]
client = genai.Client(vertexai=True, project="gen-lang-client-0846393371", location="us-central1")
run_id = str(uuid.uuid4())
path = "mkm_burn_wave2_assets.jsonl"
ok = 0
for i in range(150):
    t0 = time.perf_counter()
    prompt = SEEDS[i % len(SEEDS)] + f"\n\n[burn-meta] wave2 index={i+1}/150 tier=B"
    row = {
        "schema": "gcp_free_trial_vertex_burn_row_v1",
        "generated_at_utc": utc_now(),
        "run_id": run_id,
        "wave_id": "wave2",
        "index": i + 1,
        "prompt_profile": "asset_rag",
        "hypothesis_tier": "B",
        "track_wall": "btrack_research_only",
        "prompt": prompt,
    }
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=8192, temperature=0.2),
        )
        text = (getattr(resp, "text", None) or "").strip()
        row.update({
            "status": "ok",
            "response_text": text,
            "response_chars": len(text),
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        })
        ok += 1
    except Exception as exc:
        row.update({
            "status": "error",
            "error": str(exc)[:500],
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        })
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    if (i + 1) % 10 == 0:
        print(f"[burn] {i+1}/150 ok={ok}", flush=True)
    time.sleep(0.15)
print("DONE", ok, "jsonl=", path)
PY
echo "Wave2 started. tail -f ~/mkm_burn_wave2.log"
