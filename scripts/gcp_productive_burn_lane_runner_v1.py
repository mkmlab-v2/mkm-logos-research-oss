#!/usr/bin/env python3
"""Run one productive burn lane from mkm_productive_burn_bundle_v1.json on Vertex."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DEFAULT_BILLING = "010B19-239742-DAF438"
ALLOWED = frozenset({"gen-lang-client-0846393371", "artful-athlete-490017-k3"})
BILLING_HINTS = (
    "billing",
    "insufficient",
    "QUOTA_EXCEEDED",
    "RESOURCE_EXHAUSTED",
    "Spending limit",
    "budget",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _billing_like(msg: str) -> bool:
    m = msg.lower()
    return any(h.lower() in m for h in BILLING_HINTS)


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _adc_path() -> Path:
    return Path.home() / ".config" / "gcloud" / "application_default_credentials.json"


def _gcloud_active_account() -> str | None:
    try:
        out = subprocess.check_output(
            ["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return out.splitlines()[0] if out else None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _gcloud_print_access_token() -> str:
    return subprocess.check_output(
        ["gcloud", "auth", "print-access-token"],
        text=True,
        stderr=subprocess.PIPE,
    ).strip()


def _gcloud_cli_credentials() -> Any:
    from google.auth import credentials as auth_credentials

    class _GcloudCliTokenCredentials(auth_credentials.Credentials):
        def refresh(self, request: Any) -> None:  # noqa: ARG002
            self.token = _gcloud_print_access_token()
            self.expiry = datetime.now(timezone.utc) + timedelta(minutes=55)

    creds = _GcloudCliTokenCredentials()
    creds.refresh(None)
    return creds


def _load_vertex_credentials() -> tuple[Any, str]:
    """ADC file → gcloud CLI token → refuse metadata SA."""
    from google.auth import load_credentials_from_file
    from google.auth.transport.requests import Request

    scopes = ("https://www.googleapis.com/auth/cloud-platform",)
    adc = _adc_path()
    if adc.is_file():
        creds, _ = load_credentials_from_file(str(adc), scopes=scopes)
        if not creds.valid:
            creds.refresh(Request())
        return creds, "adc_file"

    account = _gcloud_active_account()
    if account:
        try:
            creds = _gcloud_cli_credentials()
            print(f"[auth] gcloud_cli_token account={account}", file=sys.stderr)
            return creds, "gcloud_cli_token"
        except subprocess.CalledProcessError as exc:
            print(f"[auth] gcloud token failed: {exc}", file=sys.stderr)

    import google.auth

    creds, _ = google.auth.default(scopes=scopes)
    cred_type = type(creds).__module__ + "." + type(creds).__name__
    if "compute_engine" in cred_type:
        raise RuntimeError(
            "metadata SA unusable; run: gcloud auth application-default login "
            "OR ensure gcloud auth list has ACTIVE user"
        )
    if getattr(creds, "requires_scopes", False):
        creds = creds.with_scopes(scopes)
    if not creds.valid:
        creds.refresh(Request())
    return creds, "google_auth_default"


def _usage_dict(resp: Any) -> dict[str, Any] | None:
    usage = getattr(resp, "usage_metadata", None)
    if usage is None:
        return None
    out: dict[str, Any] = {}
    for key in ("prompt_token_count", "candidates_token_count", "total_token_count"):
        val = getattr(usage, key, None)
        if val is not None:
            out[key] = val
    return out or None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle", type=Path, required=True)
    ap.add_argument("--lane", required=True, help="Lane key in bundle.lanes")
    ap.add_argument("--project", required=True)
    ap.add_argument("--location", default="us-central1")
    ap.add_argument("--model", default="gemini-2.5-pro")
    ap.add_argument("--max-output-tokens", type=int, default=4096)
    ap.add_argument("--sleep-ms", type=int, default=150)
    ap.add_argument("--max-billing-fails", type=int, default=3)
    ap.add_argument("--out-jsonl", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--wave-id", default="productive_v1")
    ap.add_argument("--start-index", type=int, default=1, help="1-based resume offset")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.project not in ALLOWED:
        print(f"REFUSE project={args.project}", file=sys.stderr)
        return 2

    bundle = json.loads(args.bundle.read_text(encoding="utf-8-sig"))
    lanes = bundle.get("lanes") if isinstance(bundle.get("lanes"), dict) else {}
    items = lanes.get(args.lane)
    if not isinstance(items, list) or not items:
        print(f"lane empty: {args.lane}", file=sys.stderr)
        return 1

    start_idx = max(1, int(args.start_index))
    run_id = str(uuid.uuid4())
    ok = fail = billing_fails = skipped_resume = 0
    stopped_billing = False
    results: list[dict[str, Any]] = []

    if args.dry_run:
        for i, item in enumerate(items, start=1):
            _append_jsonl(
                args.out_jsonl,
                {
                    "schema": "gcp_free_trial_vertex_burn_row_v1",
                    "status": "dry_run",
                    "lane": args.lane,
                    "index": i,
                    "run_id": run_id,
                },
            )
        summary = {
            "schema": "gcp_productive_burn_lane_v1",
            "generated_at_utc": _utc(),
            "lane": args.lane,
            "dry_run": True,
            "calls": len(items),
            "project_id": args.project,
        }
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        return 0

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("pip install google-genai", file=sys.stderr)
        return 2

    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", args.project)
    adc = _adc_path()
    if adc.is_file():
        os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", str(adc))

    try:
        creds, auth_mode = _load_vertex_credentials()
        print(f"[auth] mode={auth_mode}", file=sys.stderr)
        client = genai.Client(
            vertexai=True,
            project=args.project,
            location=args.location,
            credentials=creds,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Vertex auth failed: {exc}", file=sys.stderr)
        print(
            "Fix: gcloud auth list (ACTIVE user) OR gcloud auth application-default login",
            file=sys.stderr,
        )
        return 2

    for i, item in enumerate(items, start=1):
        if i < start_idx:
            skipped_resume += 1
            continue
        prompt = item.get("prompt") if isinstance(item, dict) else None
        if not isinstance(prompt, str) or not prompt.strip():
            fail += 1
            continue
        t0 = time.perf_counter()
        row: dict[str, Any] = {
            "schema": "gcp_free_trial_vertex_burn_row_v1",
            "generated_at_utc": _utc(),
            "run_id": run_id,
            "wave_id": args.wave_id,
            "lane": args.lane,
            "index": i,
            "hypothesis_tier": "B",
            "track_wall": "btrack_research_only",
            "billing_account_id": DEFAULT_BILLING,
            "project_id": args.project,
            "model": args.model,
            "prompt_profile": item.get("prompt_profile", args.lane),
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
            ms = round((time.perf_counter() - t0) * 1000, 1)
            usage = _usage_dict(resp)
            row.update(
                {
                    "status": "ok",
                    "response_text": text,
                    "response_chars": len(text),
                    "latency_ms": ms,
                    "usage": usage,
                }
            )
            ok += 1
            billing_fails = 0
        except Exception as exc:  # noqa: BLE001
            ms = round((time.perf_counter() - t0) * 1000, 1)
            err = str(exc)[:500]
            row.update({"status": "error", "error": err, "latency_ms": ms})
            fail += 1
            if _billing_like(err):
                billing_fails += 1
                if billing_fails >= args.max_billing_fails:
                    stopped_billing = True
        _append_jsonl(args.out_jsonl, row)
        results.append({"index": i, "status": row.get("status")})
        if i % 10 == 0 or i == len(items):
            print(f"[{args.lane}] {i}/{len(items)} ok={ok} fail={fail}", flush=True)
        if stopped_billing:
            print("STOP_BILLING_GUARD", flush=True)
            break
        if args.sleep_ms > 0 and i < len(items):
            time.sleep(args.sleep_ms / 1000.0)

    status = "STOPPED_BILLING_GUARD" if stopped_billing else "DONE"
    summary = {
        "schema": "gcp_productive_burn_lane_v1",
        "generated_at_utc": _utc(),
        "status": status,
        "lane": args.lane,
        "wave_id": args.wave_id,
        "run_id": run_id,
        "project_id": args.project,
        "calls_requested": len(items),
        "start_index": start_idx,
        "calls_skipped_resume": skipped_resume,
        "calls_ok": ok,
        "calls_failed": fail,
        "out_jsonl": str(args.out_jsonl),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"lane": args.lane, "status": status, "ok": ok, "fail": fail}))
    return 0 if not stopped_billing else 0


if __name__ == "__main__":
    raise SystemExit(main())
