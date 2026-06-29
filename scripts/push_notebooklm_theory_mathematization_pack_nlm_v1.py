#!/usr/bin/env python3
"""Push MKM_THEORY_MATHEMATIZATION pack via nlm CLI (preserves source titles).

SSOT pack: reports/notebooklm_theory_mathematization_pack_v1/
URL: reports/notebooklm_theory_mathematization_notebook_url_v1.txt
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "reports" / "notebooklm_theory_mathematization_pack_v1"
URL_FILE = ROOT / "reports" / "notebooklm_theory_mathematization_notebook_url_v1.txt"
OUT = ROOT / "reports" / "notebooklm_theory_mathematization_push_nlm_latest.json"
NOTEBOOK_NAME = "23_MKM_THEORY_MATHEMATIZATION_2026Q2"


def _notebook_id() -> str:
    if URL_FILE.is_file():
        url = URL_FILE.read_text(encoding="utf-8").strip()
        m = re.search(r"notebook/([0-9a-f-]{36})", url, re.I)
        if m:
            return m.group(1)
    listed = subprocess.run(
        ["nlm", "notebook", "list", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if listed.returncode == 0:
        try:
            rows = json.loads(listed.stdout)
        except json.JSONDecodeError:
            rows = []
        for row in rows:
            if str(row.get("title", "")).strip() == NOTEBOOK_NAME and row.get("id"):
                return str(row["id"])
    raise SystemExit(f"missing notebook URL in {URL_FILE} and title not in nlm list")


def _delete_by_title(nb: str, title: str) -> int:
    r = subprocess.run(["nlm", "source", "list", nb], capture_output=True, text=True, check=False)
    if r.returncode != 0:
        return 0
    try:
        rows = json.loads(r.stdout)
    except json.JSONDecodeError:
        return 0
    ids = [str(x.get("id")) for x in rows if str(x.get("title", "")).strip() == title and x.get("id")]
    if not ids:
        return 0
    d = subprocess.run(["nlm", "source", "delete", *ids, "--confirm"], capture_output=True, text=True)
    return len(ids) if d.returncode == 0 else 0


def _add_file(nb: str, path: Path, title: str, *, refresh: bool = False) -> dict:
    deleted = _delete_by_title(nb, title) if refresh else 0
    suffix = path.suffix.lower()
    upload_title = f"{title} (text)" if suffix == ".json" else title
    if suffix in {".json", ".jsonl", ".yaml", ".yml"}:
        tmp_dir = ROOT / "reports" / "tmp_nl_lens_upload"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = tmp_dir / f"{path.name}.txt"
        tmp_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        r = subprocess.run(
            ["nlm", "source", "add", nb, "--file", str(tmp_path), "--title", upload_title, "--wait"],
            capture_output=True,
            text=True,
        )
        title = upload_title
    else:
        r = subprocess.run(
            ["nlm", "source", "add", nb, "--file", str(path), "--title", title, "--wait"],
            capture_output=True,
            text=True,
        )
    return {
        "title": title,
        "deleted": deleted,
        "exit_code": r.returncode,
        "stderr": (r.stderr or r.stdout)[-300:] if r.returncode else None,
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="Delete same-title sources before add")
    ap.add_argument("--notebook-id", default="", help="Override notebook UUID")
    args = ap.parse_args()
    if not (PACK / "index.json").is_file():
        raise SystemExit("run build_notebooklm_theory_mathematization_pack_v1.py first")
    nb = (args.notebook_id or "").strip() or _notebook_id()
    files = json.loads((PACK / "index.json").read_text(encoding="utf-8"))["files"]
    rows = [_add_file(nb, PACK / name, name, refresh=args.refresh) for name in files if isinstance(name, str)]
    doc = {
        "schema": "notebooklm_theory_mathematization_push_nlm_latest",
        "notebook_id": nb,
        "rows": rows,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fail = sum(1 for r in rows if r["exit_code"] != 0)
    print(json.dumps({"notebook_id": nb, "ok": len(rows) - fail, "fail": fail, "out": str(OUT)}, ensure_ascii=False))
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
