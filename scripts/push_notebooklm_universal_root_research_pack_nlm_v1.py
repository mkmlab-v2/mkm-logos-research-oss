#!/usr/bin/env python3
"""Push universal root research pack via nlm CLI (full file bodies)."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "reports/notebooklm_universal_root_research_pack_v1"
MANIFEST = ROOT / "reports/notebooklm_universal_root_research_pack_v1_latest.json"
URL_FILE = ROOT / "reports/notebooklm_research_sandbox_notebook_url_v1.txt"
OUT = ROOT / "reports/notebooklm_universal_root_research_pack_push_v1_latest.json"
TMP = ROOT / "reports/tmp_nl_universal_root_upload"
TEXT_CHUNK = 6000
DELTA_PHASE17_PACK_NAMES: frozenset[str] = frozenset(
    {
        "docs__final__artifacts__UNIVERSAL_ROOT_GATE_SPEC_V1.json",
        "docs__final__artifacts__logos_graphrag_bridge_evidence_pack_v1_latest.json",
        "reports__logos_graphrag_phase16_topology_crosswalk_chain_v1_latest.json",
        "reports__universal_root_topology_crosswalk_v1_latest.json",
        "docs__final__artifacts__UNIVERSAL_ROOT_TOPOLOGY_CROSSWALK_SPEC_V1.json",
        "reports__logos_graphrag_phase17_closure_observability_chain_v1_latest.json",
        "docs__final__artifacts__UNIVERSAL_ROOT_WALL_DIVERGENCE_EXCEPTION_CARDS_V1.json",
        "reports__universal_root_topology_crosswalk_gate_v1_latest.json",
        "reports__logos_oracle_narrative_closure_observability_chain_v1_latest.json",
    }
)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _notebook_id() -> str:
    url = URL_FILE.read_text(encoding="utf-8").strip()
    m = re.search(r"notebook/([0-9a-f-]{36})", url, re.I)
    if not m:
        raise SystemExit(f"bad notebook URL in {URL_FILE}")
    return m.group(1)


def _existing_titles(nb: str) -> set[str]:
    proc = subprocess.run(["nlm", "source", "list", nb], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return set()
    raw = (proc.stdout or "").strip()
    if not raw:
        return set()
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        return set()
    out: set[str] = set()
    if isinstance(items, list):
        for row in items:
            if isinstance(row, dict) and row.get("title"):
                out.add(str(row["title"]))
    return out


def _list_sources(nb: str) -> list[dict]:
    proc = subprocess.run(["nlm", "source", "list", nb], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return []
    raw = (proc.stdout or "").strip()
    if not raw:
        return []
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return items if isinstance(items, list) else []


def _prune_mkm_ur_full(nb: str) -> dict:
    items = _list_sources(nb)
    ids = [str(x["id"]) for x in items if str(x.get("title") or "").startswith("MKM_UR_FULL")]
    deleted = 0
    batch_size = 25
    for i in range(0, len(ids), batch_size):
        batch = ids[i : i + batch_size]
        proc = subprocess.run(
            ["nlm", "source", "delete", *batch, "--confirm"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            deleted += len(batch)
    return {"candidate_count": len(ids), "deleted_count": deleted}


def _text_chunks(text: str) -> list[str]:
    if len(text) <= TEXT_CHUNK:
        return [text]
    return [text[i : i + TEXT_CHUNK] for i in range(0, len(text), TEXT_CHUNK)]


def _add_text(nb: str, text: str, title: str, *, existing: set[str]) -> dict:
    if title in existing:
        return {"title": title, "skipped": True, "success": True, "reason": "already_exists"}
    proc = subprocess.run(
        ["nlm", "source", "add", nb, "--text", text, "--title", title, "--wait"],
        capture_output=True,
        text=True,
        check=False,
    )
    ok = proc.returncode == 0
    tail = ((proc.stderr or "") + (proc.stdout or "")).strip()[-300:]
    if ok:
        existing.add(title)
    return {
        "title": title,
        "success": ok,
        "exit_code": proc.returncode,
        "stderr": None if ok else tail,
    }


def _add_file(nb: str, path: Path, title: str, *, existing: set[str]) -> list[dict]:
    if title in existing:
        return [{"title": title, "skipped": True, "success": True, "reason": "already_exists"}]

    body = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    use_text = suffix in {".json", ".jsonl", ".yaml", ".yml", ".md", ".txt", ".csv"}
    rows: list[dict] = []
    if use_text:
        parts = _text_chunks(body)
        for idx, part in enumerate(parts):
            part_title = title if idx == 0 else f"{title}__p{idx}"
            rows.append(_add_text(nb, part, part_title, existing=existing))
        return rows

    proc = subprocess.run(
        ["nlm", "source", "add", nb, "--file", str(path), "--title", title, "--wait"],
        capture_output=True,
        text=True,
        check=False,
    )
    ok = proc.returncode == 0
    if ok:
        existing.add(title)
    rows.append(
        {
            "title": title,
            "file": path.name,
            "success": ok,
            "exit_code": proc.returncode,
            "stderr": ((proc.stderr or "") + (proc.stdout or "")).strip()[-300:] if not ok else None,
        }
    )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--prune-mkm-ur-full",
        action="store_true",
        help="Delete existing MKM_UR_FULL_* sources before upload (notebook source cap relief)",
    )
    ap.add_argument(
        "--delta-phase17",
        action="store_true",
        help="Upload Phase16/17 delta only with MKM_UR_DELTA17_* titles (skip already_exists on FULL)",
    )
    args = ap.parse_args()

    if not MANIFEST.is_file():
        print(json.dumps({"ok": False, "error": f"missing manifest: {MANIFEST}"}), file=sys.stderr)
        return 2
    if subprocess.run(["nlm", "--version"], capture_output=True, text=True).returncode != 0:
        print(json.dumps({"ok": False, "error": "nlm CLI not on PATH"}), file=sys.stderr)
        return 2

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    nb = _notebook_id()
    prune_stats = {"skipped": True}
    if args.prune_mkm_ur_full:
        prune_stats = _prune_mkm_ur_full(nb)
    existing = _existing_titles(nb)
    rows: list[dict] = []
    for entry in manifest.get("entries") or []:
        if not entry.get("copied"):
            continue
        pack_name = str(entry["pack_name"])
        if args.delta_phase17 and pack_name not in DELTA_PHASE17_PACK_NAMES:
            continue
        path = PACK / pack_name
        short = str(pack_name).replace("docs__", "").replace("reports__", "")[:90]
        if args.delta_phase17:
            title = "MKM_UR_DELTA17_" + short
        else:
            title = "MKM_UR_FULL_" + short
        rows.extend(_add_file(nb, path, title, existing=existing))

    ok = sum(1 for r in rows if r.get("success"))
    fail = sum(1 for r in rows if not r.get("success"))
    doc = {
        "schema": "notebooklm_universal_root_research_pack_push_v1",
        "generated_at_utc": _utc(),
        "notebook_mcp_id": "14-universal-lexicon-dr",
        "notebook_uuid": nb,
        "method": "nlm_cli_source_add_text",
        "delta_phase17": bool(args.delta_phase17),
        "prune_stats": prune_stats,
        "full_content": True,
        "manifest": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "ok_count": ok,
        "fail_count": fail,
        "all_ok": fail == 0 and ok > 0,
        "rows": rows,
        "reproduce": "py scripts/push_notebooklm_universal_root_research_pack_nlm_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_ok"], "ok_count": ok, "fail_count": fail, "out": str(OUT)}, ensure_ascii=False))
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
