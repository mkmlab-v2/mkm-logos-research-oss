#!/usr/bin/env python3
"""Shared nlm CLI helpers for NotebookLM pack push with optional title refresh."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any


def notebook_id_from_url(url: str) -> str:
    m = re.search(r"notebook/([0-9a-f-]{36})", url, re.I)
    if not m:
        raise ValueError(f"bad notebook URL: {url}")
    return m.group(1)


def notebook_id_from_url_file(path: Path) -> str:
    return notebook_id_from_url(path.read_text(encoding="utf-8").strip())


def list_sources(notebook_id: str) -> list[dict[str, Any]]:
    r = subprocess.run(
        ["nlm", "source", "list", notebook_id],
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        check=False,
    )
    if r.returncode != 0 or not r.stdout.strip():
        return []
    try:
        parsed = json.loads(r.stdout)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def delete_by_title(notebook_id: str, title: str) -> int:
    ids = [str(x["id"]) for x in list_sources(notebook_id) if str(x.get("title", "")).strip() == title and x.get("id")]
    if not ids:
        return 0
    d = subprocess.run(
        ["nlm", "source", "delete", *ids, "--confirm"],
        capture_output=True,
        text=True,
        check=False,
    )
    return len(ids) if d.returncode == 0 else 0


def push_pack_index(
    *,
    pack_dir: Path,
    notebook_id: str,
    refresh: bool = True,
    tmp_dir: Path,
) -> dict[str, Any]:
    index = pack_dir / "index.json"
    if not index.is_file():
        return {"ok": False, "error": "index_missing", "pack": str(pack_dir)}
    files = json.loads(index.read_text(encoding="utf-8")).get("files") or []
    rows: list[dict[str, Any]] = []
    for name in files:
        if not isinstance(name, str):
            continue
        path = pack_dir / name
        if not path.is_file():
            rows.append({"title": name, "exit_code": 1, "error": "missing"})
            continue
        upload_title = f"{name} (text)" if path.suffix.lower() == ".json" else name
        deleted = delete_by_title(notebook_id, upload_title) if refresh else 0
        if path.suffix.lower() == ".json":
            r = subprocess.run(
                ["nlm", "source", "add", notebook_id, "--text", path.read_text(encoding="utf-8"), "--title", upload_title, "--wait"],
                capture_output=True,
                text=True,
                check=False,
            )
        elif path.suffix.lower() in {".jsonl", ".yaml", ".yml"}:
            tmp_dir.mkdir(parents=True, exist_ok=True)
            tmp_path = tmp_dir / f"{path.name}.txt"
            tmp_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            r = subprocess.run(
                ["nlm", "source", "add", notebook_id, "--file", str(tmp_path), "--title", upload_title, "--wait"],
                capture_output=True,
                text=True,
                check=False,
            )
        else:
            r = subprocess.run(
                ["nlm", "source", "add", notebook_id, "--file", str(path), "--title", upload_title, "--wait"],
                capture_output=True,
                text=True,
                check=False,
            )
        rows.append(
            {
                "title": upload_title,
                "deleted": deleted,
                "exit_code": r.returncode,
                "stderr": (r.stderr or r.stdout)[-200:] if r.returncode else None,
            }
        )
    fail = sum(1 for x in rows if x.get("exit_code") != 0)
    return {
        "ok": fail == 0,
        "notebook_id": notebook_id,
        "pack": str(pack_dir),
        "pushed": len(rows) - fail,
        "fail": fail,
        "rows": rows,
    }


def push_pack_dir(
    *,
    pack_dir: Path,
    notebook_id: str,
    refresh: bool = True,
    tmp_dir: Path,
    skip_names: set[str] | None = None,
) -> dict[str, Any]:
    skip = skip_names or {"README.md"}
    rows: list[dict[str, Any]] = []
    for path in sorted(pack_dir.iterdir()):
        if not path.is_file() or path.name in skip:
            continue
        title = path.name
        if len(title) > 120:
            title = title[-120:]
        upload_title = f"{title} (text)" if path.suffix.lower() == ".json" else title
        deleted = delete_by_title(notebook_id, upload_title) if refresh else 0
        if path.suffix.lower() == ".json":
            text = path.read_text(encoding="utf-8")
            if len(text) <= 6000:
                r = subprocess.run(
                    ["nlm", "source", "add", notebook_id, "-t", text, "--title", upload_title, "--wait"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
            else:
                tmp_dir.mkdir(parents=True, exist_ok=True)
                tmp_path = tmp_dir / f"{path.stem[:48]}.txt"
                tmp_path.write_text(text, encoding="utf-8")
                r = subprocess.run(
                    ["nlm", "source", "add", notebook_id, "--file", str(tmp_path), "--title", upload_title, "--wait"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
        elif path.suffix.lower() in {".jsonl", ".yaml", ".yml"}:
            tmp_dir.mkdir(parents=True, exist_ok=True)
            tmp_path = tmp_dir / f"{path.name}.txt"
            tmp_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            r = subprocess.run(
                ["nlm", "source", "add", notebook_id, "--file", str(tmp_path), "--title", upload_title, "--wait"],
                capture_output=True,
                text=True,
                check=False,
            )
        else:
            r = subprocess.run(
                ["nlm", "source", "add", notebook_id, "--file", str(path), "--title", upload_title, "--wait"],
                capture_output=True,
                text=True,
                check=False,
            )
        rows.append(
            {
                "title": upload_title,
                "deleted": deleted,
                "exit_code": r.returncode,
                "stderr": (r.stderr or r.stdout)[-200:] if r.returncode else None,
            }
        )
    fail = sum(1 for x in rows if x.get("exit_code") != 0)
    return {
        "ok": fail == 0,
        "notebook_id": notebook_id,
        "pack": str(pack_dir),
        "pushed": len(rows) - fail,
        "fail": fail,
        "rows": rows,
    }
