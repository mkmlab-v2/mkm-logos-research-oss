#!/usr/bin/env python3
"""Prune MKM_CORE_FACT NL notebook to slim-pack keep set."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK_INDEX = ROOT / "reports" / "notebooklm_core_fact_sync_pack_v1" / "index.json"
URL_FILE = ROOT / "reports" / "notebooklm_core_fact_notebook_url_v1.txt"
OUT_DEFAULT = ROOT / "reports" / "notebooklm_core_fact_prune_result_v1_latest.json"

KEEP_BASE_TITLES = {
    "00_core_fact_lane_boundary_snippet.md",
    "COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md",
    "MKM_LESSONS_LEARNED_V1.md",
    "MKM_CORE_THEORY_V1.md",
    "COMPRESSION_SLA_POLICY_V1.md",
    "mkm_inter_agent_encoding_sota_map_v1.md",
    "lg_compression_trust_packet_onepager_v1.md",
    "mkm_inter_agent_wire_profile_v0.json",
    "mkm_inter_agent_encoding_status_latest.json",
    "mkm_inter_agent_first_message_worked_example_v1.md",
    "mkm_inter_agent_first_message_worked_example_v1.json",
    "mkm_inter_agent_first_message_live_http_v1.json",
    "mkm_inter_agent_compress_request_v1.json",
    "mkm_inter_agent_expand_request_v1.json",
    "openapi_token_compression_v2_draft.yaml",
}

NEVER_DELETE_TITLES = {"붙여넣은 텍스트"}


def base_title(raw: str) -> str:
    t = (raw or "").strip()
    if "__p" in t:
        t = t.split("__p", 1)[0]
    t = re.sub(r"\s*\(sync\s+[^)]+\)\s*$", "", t, flags=re.I)
    t = re.sub(r"\s*\(text\)\s*$", "", t, flags=re.I)
    return t.strip()


def logical_keep_key(raw: str) -> str:
    """Map lens-pack NL titles (docs__final__…) to slim-pack basename."""
    t = base_title(raw)
    for prefix in (
        "docs__final__artifacts__fixtures__",
        "docs__final__artifacts__",
        "docs__final__",
        "reports__constitution__btrack_pilot__",
    ):
        if t.startswith(prefix):
            return t[len(prefix) :]
    return t


def _notebook_id_from_pack() -> str | None:
    if URL_FILE.is_file():
        url = URL_FILE.read_text(encoding="utf-8").strip()
        m = re.search(r"notebook/([0-9a-f-]{36})", url, re.I)
        if m:
            return m.group(1)
    if PACK_INDEX.is_file():
        idx = json.loads(PACK_INDEX.read_text(encoding="utf-8"))
        url = (idx.get("notebook_url") or "").strip()
        m = re.search(r"notebook/([0-9a-f-]{36})", url, re.I)
        if m:
            return m.group(1)
    return None


def fetch_sources(notebook_id: str) -> list[dict]:
    raw = subprocess.check_output(
        ["nlm", "notebook", "get", notebook_id, "--json"],
        text=True,
        encoding="utf-8-sig",
    )
    data = json.loads(raw)
    val = data.get("value", data)
    return list(val.get("sources") or [])


def delete_source(source_id: str) -> bool:
    r = subprocess.run(
        ["nlm", "source", "delete", source_id, "--confirm"],
        capture_output=True,
        text=True,
    )
    return r.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--notebook-id", default="")
    ap.add_argument("--what-if", action="store_true")
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    args = ap.parse_args()

    nb = (args.notebook_id or "").strip() or _notebook_id_from_pack()
    if not nb:
        raise SystemExit(
            "notebook UUID missing — set reports/notebooklm_core_fact_notebook_url_v1.txt or --notebook-id"
        )

    sources = fetch_sources(nb)
    to_delete: list[dict] = []
    kept: list[dict] = []
    for s in sources:
        sid = s.get("id", "")
        title = s.get("title", "")
        base = base_title(title)
        logical = logical_keep_key(title)
        row = {"id": sid, "title": title, "base_title": base, "logical_keep_key": logical}
        if logical in KEEP_BASE_TITLES:
            kept.append(row)
        elif title in NEVER_DELETE_TITLES or base in NEVER_DELETE_TITLES:
            kept.append({**row, "note": "nl_paste_title_preserved"})
        else:
            to_delete.append(row)

    def _prefer_score(title: str) -> int:
        t = base_title(title)
        if t.startswith("docs__final__"):
            return 3
        if t.endswith(".md"):
            return 2
        return 1

    by_logical: dict[str, list[dict]] = {}
    for row in kept:
        by_logical.setdefault(row["logical_keep_key"], []).append(row)
    deduped_kept: list[dict] = []
    for _key, rows in by_logical.items():
        rows_sorted = sorted(rows, key=lambda r: _prefer_score(r["title"]), reverse=True)
        deduped_kept.append(rows_sorted[0])
        for extra in rows_sorted[1:]:
            to_delete.append({**extra, "note": "duplicate_logical_key"})

    kept = deduped_kept

    doc = {
        "schema": "notebooklm_core_fact_prune_result_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "notebook_id": nb,
        "data_lane": "mkm_core_fact",
        "keep_base_titles": sorted(KEEP_BASE_TITLES),
        "sources_before": len(sources),
        "keep_count": len(kept),
        "delete_count": len(to_delete),
        "delete": to_delete,
        "kept_base_summary": sorted({k["logical_keep_key"] for k in kept}),
        "missing_keep_bases": sorted(KEEP_BASE_TITLES - {k["logical_keep_key"] for k in kept}),
    }

    if args.what_if:
        Path(args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"what_if": True, "delete_count": len(to_delete), "out": args.out}, ensure_ascii=False))
        return 0

    ok = fail = 0
    for row in to_delete:
        if delete_source(row["id"]):
            ok += 1
        else:
            fail += 1

    sources_after = fetch_sources(nb)
    doc["deleted_ok"] = ok
    doc["deleted_fail"] = fail
    doc["sources_after"] = len(sources_after)
    Path(args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"deleted_ok": ok, "deleted_fail": fail, "sources_after": len(sources_after), "out": args.out},
            ensure_ascii=False,
        )
    )
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
