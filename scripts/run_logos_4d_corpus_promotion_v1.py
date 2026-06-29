#!/usr/bin/env python3
"""Promote patched Logos 4pipeline SSOT + jsonl encoder sync (B-track, commander-approved)."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FULL = ROOT / "data/logos/verse_4pipeline_full_31102.json"
PATCHED = ROOT / "reports/logos_verse_4pipeline_patched_full_v1.json"
BACKUP_DIR = ROOT / "data/logos/backups"
ART = ROOT / "docs/final/artifacts"
OUT = ART / "logos_4d_corpus_promotion_v1_latest.json"
LOG = ROOT / "reports/logos_4d_corpus_promotion_log_v1.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _run_py(script: str, *args: str) -> dict:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    tail = (cp.stdout or "").strip().splitlines()
    doc = json.loads(tail[-1]) if tail else {"ok": False, "stderr": cp.stderr}
    doc["_exit_code"] = cp.returncode
    return doc


def promote_pipeline(*, patched: Path, full: Path, dry_run: bool) -> dict:
    if not patched.is_file():
        return {"ok": False, "error": "missing patched full json"}
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup = BACKUP_DIR / f"verse_4pipeline_full_31102.json.bak_{ts}"
    before_sha = _sha256(full) if full.is_file() else None
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "would_backup_to": str(backup),
            "would_copy_from": str(patched),
            "before_sha256": before_sha,
            "after_sha256": _sha256(patched),
        }
    if full.is_file():
        shutil.copy2(full, backup)
    shutil.copy2(patched, full)
    return {
        "ok": True,
        "backup_path": str(backup),
        "before_sha256": before_sha,
        "after_sha256": _sha256(full),
        "promoted_from": str(patched),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--patched-full", type=Path, default=PATCHED)
    ap.add_argument("--full-json", type=Path, default=FULL)
    ap.add_argument("--out-json", type=Path, default=OUT)
    ap.add_argument("--commander-approved", action="store_true", required=False)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-jsonl", action="store_true")
    ap.add_argument("--skip-pipeline", action="store_true")
    ap.add_argument("--skip-post-audit", action="store_true")
    ap.add_argument("--reviewer", default="commander_chat_2026-06-04")
    ap.add_argument("--notes", default="Commander 승격승인 — Logos 4D corpus SSOT (B-track only).")
    args = ap.parse_args()
    if not args.commander_approved and not args.dry_run:
        print(json.dumps({"ok": False, "error": "pass --commander-approved for live promotion"}))
        return 2
    if not args.patched_full.is_file():
        print(json.dumps({"ok": False, "error": f"missing {args.patched_full}"}))
        return 2

    pipe = {"skipped": True}
    if not args.skip_pipeline:
        pipe = promote_pipeline(patched=args.patched_full, full=args.full_json, dry_run=args.dry_run)
    jsonl_stats: dict = {"skipped": True}
    if not args.skip_jsonl:
        jsonl_args = ["--dry-run"] if args.dry_run else []
        jsonl_stats = _run_py("apply_logos_jsonl_4d_encoder_promotion_v1.py", *jsonl_args)

    audits: dict = {"skipped": True}
    if not args.skip_post_audit and not args.dry_run:
        audits = {
            "cross": _run_py(
                "audit_logos_4pipeline_jsonl_4d_cross_v1.py",
                "--out-json",
                "reports/logos_4pipeline_jsonl_4d_cross_audit_post_promotion_v1_latest.json",
            ),
            "dedupe": _run_py(
                "audit_logos_verse_4d_dedupe_v1.py",
                "--out-json",
                "reports/logos_verse_4d_dedupe_audit_post_promotion_v1_latest.json",
            ),
        }

    payload = {
        "schema": "logos_4d_corpus_promotion_v1",
        "generated_at_utc": _utc(),
        "decision": "PROMOTE_B_TRACK_LOGOS_4D_CORPUS_SSOT",
        "reviewer_label": args.reviewer,
        "notes": args.notes,
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "human_approval": {"commander_approved": bool(args.commander_approved or args.dry_run)},
        "track_wall": {
            "compression_track_a_touch": False,
            "apply_gematria_4d_bridge_policy": False,
            "promotion_to_a_track_allowed": False,
            "live_trading_enabled": False,
            "multilens_active_report_mutated": False,
        },
        "pipeline_promotion": pipe,
        "jsonl_promotion": jsonl_stats,
        "post_promotion_audits": audits,
        "evidence_paths": {
            "patched_full": str(args.patched_full.resolve()),
            "full_ssot": str(args.full_json.resolve()),
        },
    }
    if not args.dry_run:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "generated_at_utc": payload["generated_at_utc"],
                        "decision": payload["decision"],
                        "after_sha256": pipe.get("after_sha256"),
                        "artifact": str(args.out_json),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    ok = (pipe.get("ok", pipe.get("skipped"))) and jsonl_stats.get("ok", jsonl_stats.get("skipped"))
    print(json.dumps({"ok": bool(ok), "artifact": str(args.out_json), "pipeline": pipe, "jsonl": jsonl_stats}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
