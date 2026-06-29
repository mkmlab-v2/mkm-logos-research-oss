#!/usr/bin/env python3
"""Run IJEOMA pyobyeong query set PBQ01–PBQ08 via nlm CLI (optional).

Dry-run writes stub jsonl without calling NotebookLM.
Worktree output only.

  py scripts/run_ijeoma_pyobyeong_query_set_v1.py --dry-run
  py scripts/run_ijeoma_pyobyeong_query_set_v1.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUERY_SET = ROOT / "experiments/sasang-head-btrack/research/ijeoma_pyobyeong_query_set_v1.json"
OUT_DIR = ROOT / "experiments/sasang-head-btrack/artifacts"
OUT_JSONL = OUT_DIR / "ijeoma_pyobyeong_query_run_v1.jsonl"
OUT_SUMMARY = OUT_DIR / "ijeoma_pyobyeong_query_run_v1_summary.json"
NOTEBOOK_UUID = "e6c1f050-40ef-49f0-8b2c-c509b8570cf4"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_questions() -> list[dict]:
    doc = json.loads(QUERY_SET.read_text(encoding="utf-8"))
    return list(doc.get("questions") or [])


def run(*, dry_run: bool, append: bool, timeout_s: int) -> int:
    if not QUERY_SET.is_file():
        print(f"missing query set: {QUERY_SET}", file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not append and OUT_JSONL.exists():
        OUT_JSONL.unlink()

    rows: list[dict] = []
    for item in _load_questions():
        qid = str(item.get("query_id") or "")
        question = str(item.get("question_ko") or "")
        t0 = time.time()
        ok = False
        answer = ""
        conv = None
        err = ""
        if dry_run:
            ok = True
            answer = "[DRY_RUN] NL batch not executed — run without --dry-run when nlm CLI + IJEOMA auth ready."
        else:
            try:
                proc = subprocess.run(
                    ["nlm", "notebook", "query", NOTEBOOK_UUID, question],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=str(ROOT),
                    timeout=timeout_s,
                )
                ok = proc.returncode == 0
                if ok:
                    try:
                        payload = json.loads(proc.stdout)
                        val = payload.get("value") or payload
                        answer = str(val.get("answer") or "")
                        conv = val.get("conversation_id")
                    except json.JSONDecodeError:
                        ok = False
                        err = proc.stdout[:500]
                else:
                    err = (proc.stderr or proc.stdout or "")[:500]
            except subprocess.TimeoutExpired:
                ok = False
                err = f"nlm query timed out after {timeout_s}s"
        elapsed = round(time.time() - t0, 1)
        row = {
            "schema": "ijeoma_pyobyeong_query_run_v1",
            "query_id": qid,
            "topic": item.get("topic"),
            "question_ko": question,
            "dry_run": dry_run,
            "ok": ok,
            "elapsed_s": elapsed,
            "conversation_id": conv,
            "answer_preview": (answer or err)[:1200],
            "answer_chars": len(answer or ""),
            "generated_at_utc": _utc(),
        }
        rows.append(row)
        with OUT_JSONL.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(json.dumps({"query_id": qid, "ok": ok, "dry_run": dry_run, "chars": row["answer_chars"]}, ensure_ascii=False))
        if not dry_run:
            time.sleep(1.0)

    summary = {
        "schema": "ijeoma_pyobyeong_query_run_v1_summary",
        "generated_at_utc": _utc(),
        "dry_run": dry_run,
        "notebook_uuid": NOTEBOOK_UUID,
        "total": len(rows),
        "ok": sum(1 for r in rows if r["ok"]),
        "fail": sum(1 for r in rows if not r["ok"]),
        "jsonl": str(OUT_JSONL.relative_to(ROOT)).replace("\\", "/"),
        "query_set": str(QUERY_SET.relative_to(ROOT)).replace("\\", "/"),
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("SUMMARY", json.dumps(summary, ensure_ascii=False))
    if dry_run:
        return 0
    return 0 if summary["fail"] == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Write stub jsonl without nlm")
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=120, help="Per-query nlm timeout (default 120)")
    args = parser.parse_args()
    return run(dry_run=args.dry_run, append=args.append, timeout_s=args.timeout_s)


if __name__ == "__main__":
    raise SystemExit(main())
