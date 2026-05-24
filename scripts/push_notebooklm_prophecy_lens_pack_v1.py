#!/usr/bin/env python3
"""Push LENS_PROPHECY pack to 07_PROPHECY_BTRACK_2026Q2 (md file, json as text).

SSOT: docs/final/NOTEBOOKLM_PROPHECY_LENS_INDEX_V1.md
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "reports" / "notebooklm_lens_packs_v1" / "LENS_PROPHECY"
MAP = ROOT / "reports" / "notebooklm_lens_packs_v1" / "notebook_ids.json"
DEFAULT_NB = "3e95ca50-66f8-4b54-b0ef-81821c199518"


def _notebook_id() -> str:
    if MAP.is_file():
        data = json.loads(MAP.read_text(encoding="utf-8"))
        nid = (data.get("lens_notebook_id") or {}).get("LENS_PROPHECY")
        if nid:
            return str(nid)
    return DEFAULT_NB


def _existing_titles(notebook_id: str) -> set[str]:
    r = subprocess.run(
        ["nlm", "source", "list", notebook_id],
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        return set()
    try:
        rows = json.loads(r.stdout)
    except json.JSONDecodeError:
        return set()
    return {str(x.get("title", "")).strip() for x in rows if x.get("title")}


def main() -> int:
    if not PACK.is_dir():
        print(f"Missing pack dir: {PACK} — run build_notebooklm_lens_source_packs_v1.py", file=sys.stderr)
        return 1
    nb = _notebook_id()
    have = _existing_titles(nb)
    ok = skip = fail = 0
    for path in sorted(PACK.iterdir()):
        if not path.is_file() or path.name == "README.md":
            continue
        # Short title avoids Windows CreateProcess length limits.
        title = path.name
        if len(title) > 96:
            title = title[-96:]
        if path.suffix.lower() == ".json":
            title = f"{title} (text)"
        if title in have:
            skip += 1
            print(f"SKIP exists: {title}")
            continue
        print(f"ADD {title} ...")
        if path.suffix.lower() == ".json":
            text = path.read_text(encoding="utf-8")
            # Windows: avoid WinError 206 (cmdline too long) — small JSON only inline.
            if len(text) <= 6000:
                r = subprocess.run(
                    ["nlm", "source", "add", nb, "-t", text, "--title", title, "--wait"],
                    capture_output=True,
                    text=True,
                )
            else:
                upload_dir = ROOT / "reports" / "tmp_nl_prophecy_upload"
                upload_dir.mkdir(parents=True, exist_ok=True)
                tmp_path = upload_dir / f"{path.stem[:48]}.txt"
                tmp_path.write_text(text, encoding="utf-8")
                r = subprocess.run(
                    [
                        "nlm",
                        "source",
                        "add",
                        nb,
                        "--file",
                        str(tmp_path),
                        "--title",
                        title,
                        "--wait",
                    ],
                    capture_output=True,
                    text=True,
                )
        else:
            r = subprocess.run(
                ["nlm", "source", "add", nb, "--file", str(path), "--title", title, "--wait"],
                capture_output=True,
                text=True,
            )
        out = (r.stdout or r.stderr or "").strip()
        if out:
            print(out)
        if r.returncode == 0:
            ok += 1
            have.add(title)
        else:
            fail += 1
        time.sleep(0.4)
    print(json.dumps({"notebook_id": nb, "ok": ok, "skip": skip, "fail": fail}, ensure_ascii=False))
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
