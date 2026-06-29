#!/usr/bin/env python3
"""Push LTM_GRAPH_OPS lens pack to NotebookLM via `nlm source add --text`.

  py scripts/push_notebooklm_ltm_graph_ops_nlm_v1.py --dry-run
  py scripts/push_notebooklm_ltm_graph_ops_nlm_v1.py
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
PACK_DIR = ROOT / "reports" / "notebooklm_lens_packs_v1" / "LTM_GRAPH_OPS"
MAP_PATH = ROOT / "reports" / "notebooklm_lens_packs_v1" / "notebook_ids.json"
LOG = ROOT / "reports" / "notebooklm_ltm_graph_ops_push_latest.log"
OUT = ROOT / "reports" / "notebooklm_ltm_graph_ops_push_result_v1_latest.json"
CHUNK = 6_000

# Fallback: 01 · 지휘·운영 (2026-06 MCP get_health active notebook)
DEFAULT_NOTEBOOK_UUID = "9bc26140-70c4-47d0-b9ea-bd3a394916a9"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _notebook_id() -> str:
    if MAP_PATH.is_file():
        doc = json.loads(MAP_PATH.read_text(encoding="utf-8-sig"))
        nid = (doc.get("lens_notebook_id") or {}).get("LTM_GRAPH_OPS")
        if nid:
            return str(nid)
    return DEFAULT_NOTEBOOK_UUID


def _chunks(text: str) -> list[str]:
    if len(text) <= CHUNK:
        return [text]
    return [text[i : i + CHUNK] for i in range(0, len(text), CHUNK)]


def _nlm_text(notebook_uuid: str, title: str, text: str, *, dry_run: bool) -> tuple[bool, str]:
    if dry_run:
        return True, f"DRY_RUN title={title} bytes={len(text.encode('utf-8'))}"
    cmd = [
        "nlm",
        "source",
        "add",
        notebook_uuid,
        "--text",
        text,
        "--title",
        title[:120],
        "--wait",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (proc.stdout or "") + (proc.stderr or "")
    ok = proc.returncode == 0 and ("Added source" in out or "already" in out.lower())
    return ok, out[-800:] if len(out) > 800 else out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.6)
    ap.add_argument("--notebook-id", default="")
    args = ap.parse_args()

    if not PACK_DIR.is_dir():
        print(f"FAIL: pack missing {PACK_DIR} — run Invoke-NotebookLmLtmGraphOpsSetup_v1.ps1", file=sys.stderr)
        return 1

    if not args.dry_run:
        if subprocess.run(["nlm", "--version"], capture_output=True).returncode != 0:
            print(
                "FAIL: nlm CLI not on PATH — use NL web UI upload from reports/notebooklm_lens_packs_v1/LTM_GRAPH_OPS/",
                file=sys.stderr,
            )
            return 1

    nid = args.notebook_id.strip() or _notebook_id()
    rows: list[dict] = []
    ok_n = fail_n = 0
    log_lines = [f"=== push_notebooklm_ltm_graph_ops_nlm_v1 {_utc()} notebook={nid} ==="]

    # Brief first for NL anchor ordering
    files = sorted(PACK_DIR.iterdir(), key=lambda p: (0 if "BRIEF" in p.name.upper() else 1, p.name))
    for path in files:
        if not path.is_file():
            continue
        body = path.read_text(encoding="utf-8", errors="replace")
        base_title = path.name.replace("__", "/")
        for i, part in enumerate(_chunks(body)):
            title = base_title if i == 0 else f"{base_title}__p{i}"
            success, tail = _nlm_text(nid, title, part, dry_run=args.dry_run)
            row = {"file": path.name, "part": i, "title": title, "success": success, "tail": tail}
            rows.append(row)
            log_lines.append(json.dumps(row, ensure_ascii=False))
            if success:
                ok_n += 1
            else:
                fail_n += 1
            if not args.dry_run:
                time.sleep(args.sleep)

    doc = {
        "schema": "notebooklm_ltm_graph_ops_push_result_v1",
        "generated_at_utc": _utc(),
        "notebook_id": nid,
        "pack_dir": str(PACK_DIR.relative_to(ROOT)).replace("\\", "/"),
        "dry_run": args.dry_run,
        "ok": ok_n,
        "fail": fail_n,
        "rows": rows,
    }
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT} ok={ok_n} fail={fail_n}")
    return 0 if fail_n == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
