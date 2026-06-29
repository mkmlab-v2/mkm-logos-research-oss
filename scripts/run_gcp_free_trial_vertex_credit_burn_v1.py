#!/usr/bin/env python3
"""Vertex Gemini burst on Free Trial billing-linked projects (010B19-239742-DAF438).

Targets projects linked to billing account 010B19 (Console manage page):
  - gen-lang-client-0846393371 (Default Gemini Project)
  - artful-athlete-490017-k3 (My First Project)

NOT mkm-lab-agi-2025 (Firebase billing 019340 — separate wallet).

Outputs:
  - Summary JSON (metrics, no full response bodies)
  - Append-only JSONL asset rows (prompt + response + SRE fields) when --out-jsonl set

Prereqs:
  gcloud auth application-default login   # jema12@mkmlife.com recommended
  py -m pip install google-genai

Example:
  py scripts/run_gcp_free_trial_vertex_credit_burn_v1.py \\
    --project gen-lang-client-0846393371 --calls 150 --model gemini-2.5-pro \\
    --prompt-profile asset_rag --out-jsonl reports/gcp_free_trial_vertex_burn_assets_v1.jsonl \\
    --wave-id wave2 --max-output-tokens 8192
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "gcp_free_trial_vertex_credit_burn_v1_latest.json"
DEFAULT_JSONL = ROOT / "reports" / "gcp_free_trial_vertex_burn_assets_v1.jsonl"
DEFAULT_PROJECT = "gen-lang-client-0846393371"
DEFAULT_BILLING_ACCOUNT = "010B19-239742-DAF438"
DEFAULT_MODEL = "gemini-2.5-pro"
DEFAULT_LOCATION = "us-central1"

PROMPT_PROFILES: dict[str, list[str]] = {
    "generic": [
        "Summarize MKM multi-lens compression architecture in 120 words.",
        "Explain Vertex AI billing SKUs for Gemini 2.5 Pro token pricing.",
        "List five risks when mixing Track A and B-track evaluation metrics.",
        "Draft a JSON schema for prophecy promotion gate evidence packs.",
        "Compare Discovery Engine Enterprise vs Standard search tiers.",
    ],
    "asset_rag": [
        "[HYPO] Output JSON only with keys: id, source_lang, target_ko, topic, summary_120w, tags. "
        "Task: structure a short Aramaic lexeme gloss (placeholder: 'shalom') for RAG ingestion.",
        "[HYPO] Output JSON only: cross_lens_mapping with sasang_axis, myeongni_axis, logos_note [NON_GATING], "
        "confidence_bucket, research_only=true.",
        "[HYPO] Output JSON only: wellness_hypothesis_card with observation, mechanism_hypothesis, "
        "limitations, hypothesis_tier=B, no_clinical_claim.",
        "[HYPO] Output JSONL-ready row: compress a multi-lens conflict resolver example "
        "(Field→Lens→Conflict→Final Action) for B-track archive.",
        "[HYPO] Output JSON only: quota_stress_metadata template fields "
        "(rpm_observed, latency_ms, error_class) for SRE bench — fill with plausible example values.",
    ],
    "wellness_hypo": [
        "[HYPO] Draft a wellness education paragraph on abdominal breathing for staff training — "
        "no diagnosis, no treatment claim, include disclaimer line.",
        "[HYPO] List 5 measurable self-report proxies for stress load (B-track only, not clinical).",
        "[HYPO] Map taeeum/soeum metaphor to session intensity dial — pedagogical only, not physiology proof.",
    ],
    "cross_lens": [
        "[HYPO] Field=pre_expiry_cloud_credit; Lens sasang=burn intensity; Lens myeongni=assetization timeline; "
        "Lens logos [NON_GATING]=isolation check; resolve to Final Action WATCH with 3 bullets.",
        "[HYPO] Compare dumb traffic burn vs JSONL assetization burn — table in markdown, research_only footer.",
    ],
    "quota_stress": [
        "Write exactly 800 words on cloud cost optimization patterns (filler for throughput).",
        "Write exactly 800 words on RAG chunking strategies for multilingual corpora (filler for throughput).",
    ],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _expand_prompts(count: int, profile: str) -> list[tuple[str, str]]:
    seeds = PROMPT_PROFILES.get(profile) or PROMPT_PROFILES["generic"]
    out: list[tuple[str, str]] = []
    i = 0
    while len(out) < count:
        base = seeds[i % len(seeds)]
        idx = len(out) + 1
        out.append((profile, f"{base}\n\n[burn-meta] profile={profile} index={idx}/{count} tier=B research_only"))
        i += 1
    return out


def _usage_dict(resp: Any) -> dict[str, Any] | None:
    usage = getattr(resp, "usage_metadata", None)
    if usage is None:
        return None
    out: dict[str, Any] = {}
    for key in (
        "prompt_token_count",
        "candidates_token_count",
        "total_token_count",
        "cached_content_token_count",
    ):
        val = getattr(usage, key, None)
        if val is not None:
            out[key] = val
    return out or None


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="GCP Free Trial Vertex credit burn + JSONL assetization")
    ap.add_argument("--project", default=DEFAULT_PROJECT)
    ap.add_argument("--location", default=DEFAULT_LOCATION)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--calls", type=int, default=30, help="Number of generate_content calls")
    ap.add_argument("--max-output-tokens", type=int, default=2048)
    ap.add_argument("--sleep-ms", type=int, default=250)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--out-jsonl",
        type=Path,
        default=DEFAULT_JSONL,
        help="Append-only asset rows (prompt+response). Omit path only via --no-jsonl.",
    )
    ap.add_argument("--no-jsonl", action="store_true", help="Skip JSONL asset append")
    ap.add_argument(
        "--prompt-profile",
        choices=sorted(PROMPT_PROFILES.keys()),
        default="asset_rag",
        help="Prompt theme for assetization (default: asset_rag)",
    )
    ap.add_argument("--wave-id", default="wave1", help="Run label for JSONL rows")
    ap.add_argument("--run-id", default="", help="Optional run UUID; auto-generated if empty")
    ap.add_argument(
        "--start-index",
        type=int,
        default=1,
        help="1-based first index to execute (resume after partial run; default 1)",
    )
    args = ap.parse_args()

    if args.start_index < 1:
        print("--start-index must be >= 1", file=sys.stderr)
        return 2

    run_id = args.run_id.strip() or str(uuid.uuid4())
    prompt_items = _expand_prompts(max(1, args.calls), args.prompt_profile)
    if args.start_index > 1:
        prompt_items = prompt_items[args.start_index - 1 :]
    results: list[dict[str, Any]] = []
    ok = 0
    fail = 0
    total_chars = 0
    total_tokens: int | None = 0
    jsonl_path: Path | None = None if args.no_jsonl else args.out_jsonl

    if args.dry_run:
        for i, (prof, prompt) in enumerate(prompt_items, start=1):
            results.append({"index": i, "status": "dry_run", "prompt_profile": prof, "prompt_len": len(prompt)})
            if jsonl_path:
                _append_jsonl(
                    jsonl_path,
                    {
                        "schema": "gcp_free_trial_vertex_burn_row_v1",
                        "generated_at_utc": _utc_now(),
                        "run_id": run_id,
                        "wave_id": args.wave_id,
                        "index": i,
                        "prompt_profile": prof,
                        "hypothesis_tier": "B",
                        "track_wall": "btrack_research_only",
                        "status": "dry_run",
                        "prompt": prompt[:500],
                    },
                )
        payload = {
            "schema": "gcp_free_trial_vertex_credit_burn_v1",
            "generated_at_utc": _utc_now(),
            "run_id": run_id,
            "wave_id": args.wave_id,
            "billing_account_id": DEFAULT_BILLING_ACCOUNT,
            "project_id": args.project,
            "location": args.location,
            "model": args.model,
            "prompt_profile": args.prompt_profile,
            "billing_surface": "vertex_ai",
            "dry_run": True,
            "calls_requested": len(prompt_items),
            "calls_ok": 0,
            "calls_failed": 0,
            "out_jsonl": str(jsonl_path) if jsonl_path else None,
            "note": "Dry run only; no Vertex calls.",
            "results_sample": results[:5],
        }
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "out": str(args.out_json), "dry_run": True}, ensure_ascii=False))
        return 0

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("pip install google-genai", file=sys.stderr)
        return 2

    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", args.project)
    client = genai.Client(vertexai=True, project=args.project, location=args.location)

    for offset, (prof, prompt) in enumerate(prompt_items, start=0):
        i = args.start_index + offset
        t0 = time.perf_counter()
        row: dict[str, Any] = {
            "index": i,
            "prompt_profile": prof,
            "prompt_len": len(prompt),
        }
        jsonl_row: dict[str, Any] = {
            "schema": "gcp_free_trial_vertex_burn_row_v1",
            "generated_at_utc": _utc_now(),
            "run_id": run_id,
            "wave_id": args.wave_id,
            "index": i,
            "prompt_profile": prof,
            "hypothesis_tier": "B",
            "track_wall": "btrack_research_only",
            "billing_account_id": DEFAULT_BILLING_ACCOUNT,
            "project_id": args.project,
            "location": args.location,
            "model": args.model,
            "prompt": prompt,
        }
        try:
            resp = client.models.generate_content(
                model=args.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=args.max_output_tokens,
                    temperature=0.2,
                ),
            )
            text = (getattr(resp, "text", None) or "").strip()
            latency = round((time.perf_counter() - t0) * 1000, 1)
            usage = _usage_dict(resp)
            row["status"] = "ok"
            row["response_chars"] = len(text)
            row["latency_ms"] = latency
            if usage:
                row["usage"] = usage
                if total_tokens is not None and usage.get("total_token_count") is not None:
                    total_tokens += int(usage["total_token_count"])
                elif total_tokens is not None:
                    total_tokens = None
            total_chars += len(text)
            ok += 1
            jsonl_row.update(
                {
                    "status": "ok",
                    "response_text": text,
                    "response_chars": len(text),
                    "latency_ms": latency,
                    "usage": usage,
                }
            )
        except Exception as exc:  # noqa: BLE001 — burn script: capture all API failures
            latency = round((time.perf_counter() - t0) * 1000, 1)
            err = str(exc)[:500]
            row["status"] = "error"
            row["error"] = err
            row["latency_ms"] = latency
            fail += 1
            jsonl_row.update({"status": "error", "error": err, "latency_ms": latency})
        results.append(row)
        if jsonl_path:
            _append_jsonl(jsonl_path, jsonl_row)
        if args.sleep_ms > 0 and offset < len(prompt_items) - 1:
            time.sleep(args.sleep_ms / 1000.0)
        end_index = args.start_index + len(prompt_items) - 1
        if i % 10 == 0 or i == end_index:
            print(f"[burn] {i}/{args.calls} ok={ok} fail={fail}", flush=True)

    payload = {
        "schema": "gcp_free_trial_vertex_credit_burn_v1",
        "generated_at_utc": _utc_now(),
        "run_id": run_id,
        "wave_id": args.wave_id,
        "billing_account_id": DEFAULT_BILLING_ACCOUNT,
        "project_id": args.project,
        "location": args.location,
        "model": args.model,
        "prompt_profile": args.prompt_profile,
        "billing_surface": "vertex_ai",
        "dry_run": False,
        "calls_requested": args.calls,
        "calls_in_this_run": len(prompt_items),
        "start_index": args.start_index,
        "calls_ok": ok,
        "calls_failed": fail,
        "total_response_chars": total_chars,
        "total_tokens_reported": total_tokens,
        "max_output_tokens": args.max_output_tokens,
        "out_jsonl": str(jsonl_path) if jsonl_path else None,
        "credit_check_note": "Verify Console Billing > Credits on 010B19-239742-DAF438 after 24-48h.",
        "results": results,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": fail == 0,
                "out": str(args.out_json),
                "out_jsonl": str(jsonl_path) if jsonl_path else None,
                "calls_ok": ok,
                "calls_failed": fail,
                "run_id": run_id,
            },
            ensure_ascii=False,
        )
    )
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
