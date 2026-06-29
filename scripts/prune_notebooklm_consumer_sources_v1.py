#!/usr/bin/env python3
"""Prune Consumer NL notebook to consumer_survey_only slim-pack keep set.

SSOT pack: scripts/build_notebooklm_consumer_sync_pack_v1.py
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK_INDEX = ROOT / "reports" / "notebooklm_consumer_sync_pack_v1" / "index.json"
URL_FILE = ROOT / "reports" / "notebooklm_consumer_notebook_url_v1.txt"
OUT_DEFAULT = ROOT / "reports" / "notebooklm_consumer_prune_result_v1_latest.json"

KEEP_BASE_TITLES = {
    "00_consumer_lane_boundary_snippet.md",
    "MKM_DOMAIN_CLINICAL_LANE_V1.md",
    "MKM_DOMAIN_PORTFOLIO_POINTER_V1.md",
    "CLINIC_CONSTITUTION_MVP_V1.md",
    "NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md",
    "MKM_HEALTH_WELLNESS_COPY_GUARDRAILS_KR_V1.md",
    "PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md",
    "NOTEBOOKLM_MKMLIFE_NEWS_QUESTION_STARTER_BUNDLE_2026-04-12.md",
    "clinic_constitution_dual_lane_policy_v1.json",
    "clinic_constitution_survey_item_bank_v1.json",
    "clinic_constitution_survey_pack_public_v1.schema.json",
    "gtm_mai_copy_bundles_v1.json",
}

NEVER_DELETE_TITLES = {"붙여넣은 텍스트"}


def base_title(raw: str) -> str:
    t = (raw or "").strip()
    if "__p" in t:
        t = t.split("__p", 1)[0]
    t = re.sub(r"\s*\(sync\s+[^)]+\)\s*$", "", t, flags=re.I)
    return t.strip()


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
            "notebook UUID missing — set reports/notebooklm_consumer_notebook_url_v1.txt or --notebook-id"
        )

    sources = fetch_sources(nb)
    to_delete: list[dict] = []
    kept: list[dict] = []
    for s in sources:
        sid = s.get("id", "")
        title = s.get("title", "")
        base = base_title(title)
        row = {"id": sid, "title": title, "base_title": base}
        if base in KEEP_BASE_TITLES:
            kept.append(row)
        elif title in NEVER_DELETE_TITLES or base in NEVER_DELETE_TITLES:
            kept.append({**row, "note": "nl_paste_title_preserved"})
        else:
            to_delete.append(row)

    doc = {
        "schema": "notebooklm_consumer_prune_result_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "notebook_id": nb,
        "data_lane": "consumer_survey_only",
        "keep_base_titles": sorted(KEEP_BASE_TITLES),
        "sources_before": len(sources),
        "keep_count": len(kept),
        "delete_count": len(to_delete),
        "delete": to_delete,
        "kept_base_summary": sorted({k["base_title"] for k in kept}),
        "missing_keep_bases": sorted(KEEP_BASE_TITLES - {k["base_title"] for k in kept}),
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
