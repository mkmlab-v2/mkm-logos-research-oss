#!/usr/bin/env python3
"""Run large NotebookLM query batches and accumulate B-Track insights as JSONL.

Purpose:
- Use NotebookLM compute for high-volume exploratory insights in B-Track.
- Persist every answer with citations/sources for later local verification.
- Keep strict [HYPO]/observation-only framing (no A-track auto binding).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NOTEBOOK_ID = "71f55a03-09d0-411f-b365-0ce2a2064c24"
DEFAULT_QUERY_PACK = ROOT / "docs" / "final" / "artifacts" / "btrack_notebooklm_query_pack_v1.json"
DEFAULT_JSONL = ROOT / "reports" / "notebooklm" / "btrack_mega_insights_latest.jsonl"
DEFAULT_SUMMARY = ROOT / "reports" / "notebooklm" / "btrack_mega_insights_summary_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_query_pack(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"query-pack not found: {path}")
    o = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]]
    if isinstance(o, dict) and isinstance(o.get("queries"), list):
        rows = [r for r in o["queries"] if isinstance(r, dict)]
    elif isinstance(o, list):
        rows = [r for r in o if isinstance(r, dict)]
    else:
        raise ValueError("query-pack must be list[object] or {queries:[object]}")
    out: list[dict[str, Any]] = []
    for i, r in enumerate(rows, start=1):
        q = str(r.get("question") or "").strip()
        if not q:
            continue
        out.append(
            {
                "id": str(r.get("id") or f"q{i:03d}"),
                "question": q,
                "tags": r.get("tags") if isinstance(r.get("tags"), list) else [],
            }
        )
    if not out:
        raise ValueError("query-pack contains no valid questions")
    return out


def _is_resource_exhausted(msg: str) -> bool:
    m = msg.upper()
    return "RESOURCE_EXHAUSTED" in m or "ERROR CODE 8" in m


def _run_nlm_query(
    notebook_id: str,
    question: str,
    timeout_s: float,
    conversation_id: str | None = None,
    quota_retry_max: int = 0,
    quota_retry_base_sec: float = 90.0,
) -> dict[str, Any]:
    retries_done = 0
    last_err: Exception | None = None
    while True:
        cmd = ["nlm", "query", "notebook", notebook_id, question, "-t", str(timeout_s)]
        if conversation_id:
            cmd += ["-c", conversation_id]
        cp = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        err_text = (cp.stderr or cp.stdout or f"nlm exit {cp.returncode}").strip()
        if cp.returncode == 0:
            break
        last_err = RuntimeError(err_text)
        if (
            quota_retry_max > 0
            and retries_done < quota_retry_max
            and _is_resource_exhausted(err_text)
        ):
            retries_done += 1
            sleep_s = min(3600.0, quota_retry_base_sec * (2 ** (retries_done - 1)))
            print(
                f"QUOTA_RETRY n={retries_done}/{quota_retry_max} sleep_s={sleep_s:.0f}",
                file=sys.stderr,
            )
            time.sleep(sleep_s)
            continue
        raise last_err
    try:
        doc = json.loads(cp.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"nlm output is not JSON: {exc}") from exc
    value = doc.get("value") if isinstance(doc, dict) else None
    if not isinstance(value, dict):
        raise RuntimeError("nlm JSON missing `value` object")
    return value


def _append_jsonl(path: Path, row: dict[str, Any]) -> int:
    text = json.dumps(row, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)
    return len(text.encode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="NotebookLM mega insight batch runner ([HYPO], B-Track only).")
    ap.add_argument("--notebook-id", default=DEFAULT_NOTEBOOK_ID)
    ap.add_argument("--query-pack", type=Path, default=DEFAULT_QUERY_PACK)
    ap.add_argument("--jsonl-out", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--summary-out", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--timeout-sec", type=float, default=120.0)
    ap.add_argument("--limit", type=int, default=0, help="0 means all queries")
    ap.add_argument("--target-bytes", type=int, default=0, help="Stop when appended bytes reach this target.")
    ap.add_argument("--shared-conversation", action="store_true", help="Use one conversation_id across queries.")
    ap.add_argument("--continue-on-error", action="store_true")
    ap.add_argument(
        "--quota-retry-max",
        type=int,
        default=0,
        help="On RESOURCE_EXHAUSTED (Google error 8), retry this many times with exponential backoff.",
    )
    ap.add_argument(
        "--quota-retry-base-sec",
        type=float,
        default=90.0,
        help="Base sleep before first quota retry; doubles each attempt (cap 3600s).",
    )
    args = ap.parse_args()

    queries = _load_query_pack(args.query_pack)
    if args.limit > 0:
        queries = queries[: args.limit]

    summary: dict[str, Any] = {
        "schema": "btrack_notebooklm_mega_insight_batch_summary_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "promotion_required": True,
        "a_track_autobind_forbidden": True,
        "label": "[HYPO] NotebookLM batch insight run; observation-only, no A-track auto-binding.",
        "notebook_id": args.notebook_id,
        "query_pack": str(args.query_pack),
        "jsonl_out": str(args.jsonl_out),
        "n_planned": len(queries),
        "n_success": 0,
        "n_error": 0,
        "bytes_appended": 0,
        "first_conversation_id": None,
        "last_conversation_id": None,
        "errors": [],
    }

    conv_id: str | None = None
    for q in queries:
        if args.target_bytes > 0 and summary["bytes_appended"] >= args.target_bytes:
            break
        qid = q["id"]
        question = q["question"]
        try:
            value = _run_nlm_query(
                notebook_id=args.notebook_id,
                question=question,
                timeout_s=float(args.timeout_sec),
                conversation_id=conv_id if args.shared_conversation else None,
                quota_retry_max=int(args.quota_retry_max),
                quota_retry_base_sec=float(args.quota_retry_base_sec),
            )
            this_conv = value.get("conversation_id")
            if not summary["first_conversation_id"]:
                summary["first_conversation_id"] = this_conv
            summary["last_conversation_id"] = this_conv
            if args.shared_conversation and isinstance(this_conv, str) and this_conv:
                conv_id = this_conv

            row = {
                "schema": "btrack_notebooklm_mega_insight_row_v1",
                "ts_utc": _utc_now(),
                "hypothesis_tier": "B",
                "boundary_ack": True,
                "research_only": True,
                "promotion_required": True,
                "a_track_autobind_forbidden": True,
                "label": "[HYPO] NotebookLM comparative insight row (non-deterministic, non-medical).",
                "notebook_id": args.notebook_id,
                "query_id": qid,
                "tags": q.get("tags") or [],
                "question": question,
                "answer": value.get("answer"),
                "conversation_id": value.get("conversation_id"),
                "sources_used": value.get("sources_used"),
                "citations": value.get("citations"),
                "references": value.get("references"),
            }
            added = _append_jsonl(args.jsonl_out, row)
            summary["bytes_appended"] += int(added)
            summary["n_success"] += 1
            print(f"OK {qid}: +{added} bytes")
        except Exception as exc:  # noqa: BLE001
            summary["n_error"] += 1
            err = {"query_id": qid, "error": str(exc)}
            summary["errors"].append(err)
            print(f"ERR {qid}: {exc}", file=sys.stderr)
            if not args.continue_on_error:
                break

    summary["completed_at_utc"] = _utc_now()
    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.summary_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["n_success"] > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

