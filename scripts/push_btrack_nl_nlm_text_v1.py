#!/usr/bin/env python3
"""Upload pack files via `nlm source add --text` (JSON/MD; avoids --file failures)."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK_ROOT = ROOT / "reports/notebooklm_lens_packs_v1"
LOG = ROOT / "reports/notebooklm_btrack_lens_pack_push_latest.log"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_nl_auto_upload_result_v1.json"
CHUNK = 6_000  # Windows CreateProcess cmdline limit (~8191)

LENS_NOTEBOOK = {
    "COMPRESSION_BTRACK": "8b0cf18f-1843-438e-8a76-709974e93c43",
    "IJEOMA_BTRACK": "e6c1f050-40ef-49f0-8b2c-c509b8570cf4",
    "LENS_SASANG": "90132f48-febd-471a-82a1-b6ec80d98618",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _chunks(text: str) -> list[str]:
    if len(text) <= CHUNK:
        return [text]
    return [text[i : i + CHUNK] for i in range(0, len(text), CHUNK)]


def _nlm_text(notebook_uuid: str, title: str, text: str) -> tuple[bool, str]:
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
    ok = proc.returncode == 0 and "Added source" in out
    return ok, out[-500:] if len(out) > 500 else out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sleep", type=float, default=0.8)
    parser.add_argument("--lenses", default="COMPRESSION_BTRACK,IJEOMA_BTRACK")
    args = parser.parse_args()
    lenses = [x.strip() for x in args.lenses.split(",") if x.strip()]
    rows: list[dict] = []
    ok_n = fail_n = 0
    log_lines = [f"=== push_btrack_nl_nlm_text_v1 {_utc()} ==="]

    for lens in lenses:
        d = PACK_ROOT / lens
        if not d.is_dir():
            continue
        nid = LENS_NOTEBOOK[lens]
        for path in sorted(d.iterdir()):
            if not path.is_file():
                continue
            body = path.read_text(encoding="utf-8", errors="replace")
            for i, part in enumerate(_chunks(body)):
                title = path.name if i == 0 else f"{path.name}__p{i}"
                success, tail = _nlm_text(nid, title, part)
                row = {
                    "lens": lens,
                    "file": path.name,
                    "part": i,
                    "success": success,
                    "tail": tail,
                }
                rows.append(row)
                if success:
                    ok_n += 1
                else:
                    fail_n += 1
                log_lines.append(f"{lens} {title} ok={success}")
                print(json.dumps(row, ensure_ascii=False), flush=True)
                time.sleep(args.sleep)

    log_lines.append(f"=== Done ok={ok_n} fail={fail_n} ===")
    LOG.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    doc = {
        "schema": "comp_nl_auto_upload_result_v1",
        "generated_at_utc": _utc(),
        "commander_approved": True,
        "method": "nlm_cli_text",
        "script": "scripts/push_btrack_nl_nlm_text_v1.py",
        "ok": ok_n,
        "fail": fail_n,
        "success": fail_n == 0 and ok_n > 0,
        "rows": rows,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok_n, "fail": fail_n, "wrote": OUT.name}, ensure_ascii=False))
    return 0 if doc["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
