#!/usr/bin/env python3
"""Batch-pull priority IJEOMA NL sources → workspace proxies + fragment mine (HOLD)."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK = "e6c1f050-40ef-49f0-8b2c-c509b8570cf4"
OUT = ROOT / "reports/constitution/btrack_pilot/ijeoma_nl_priority_pull_run_v1.json"

# Priority: 격치고 partial > cheonyu layer > yugo insight > geukchi bridge
PULLS: list[dict] = [
    {
        "slug": "GEUKCHIGO_vol1_preface_ruyo_1_1",
        "source_id": "b8411a5c-86df-4667-aae5-044a0e537674",
        "skip_query": True,
        "note": "PARTIAL 격치고 儒略 1-1 — commander paste",
    },
    {
        "slug": "GEUKCHI_CHEONYU_layer",
        "source_id": "f61e2349-6909-4bf2-99ba-d7edc59d8572",
        "query": "이 소스만: 闡幽抄·천유초 SSOT·CANON 금지·list mention vs primary 구분 bullet 10개",
        "note": "PAPER_PROXY cheonyu layer firewall",
    },
    {
        "slug": "GEUKCHIGO_YUGO_insight",
        "source_id": "c407d6e5-c302-4be1-878e-22ad08221b32",
        "query": "이 소스만: 동무유고·격치고·유고초·闡幽 관련 서지·인용 구절 표",
        "note": "SECONDARY geukchi+yugo insight",
    },
    {
        "slug": "GEUKCHI_DSSBW_sasimsimmul_bridge",
        "source_id": "7a3014b0-eb6f-4c04-85c4-db84f3454704",
        "query": "이 소스만: 사심신물(事心身物) 정의·격치고↔동의수세보원 대응표",
        "note": "COMMENTARY sasimsimmul bridge",
    },
    {
        "slug": "CHEONYUCHO_JEMA_MERGED_LIT_nl",
        "source_id": "70a4a0e3-722d-4326-bd54-5461d714029f",
        "skip_query": True,
        "note": "MERGED LIT mirror for NL crosswalk",
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def pull_one(row: dict) -> dict:
    cmd = [
        sys.executable,
        "scripts/pull_notebooklm_source_to_workspace_v1.py",
        "--notebook-id",
        NOTEBOOK,
        "--source-id",
        row["source_id"],
        "--slug",
        row["slug"],
    ]
    if row.get("skip_query"):
        cmd.append("--skip-query")
    elif row.get("query"):
        cmd.extend(["--query", row["query"]])
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = (p.stdout or p.stderr or "")[-500:]
    return {"slug": row["slug"], "note": row.get("note"), "exit_code": p.returncode, "tail": tail}


def main() -> int:
    rows = [pull_one(r) for r in PULLS]
    fm = subprocess.run(
        [sys.executable, "scripts/run_cheonyucho_fragment_mine_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    gate = subprocess.run(
        [sys.executable, "scripts/check_cheonyucho_acquisition_gate_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    ok = all(r["exit_code"] == 0 for r in rows) and fm.returncode == 0 and gate.returncode == 0
    doc = {
        "schema": "ijeoma_nl_priority_pull_run_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "ok": ok,
        "pulls": rows,
        "fragment_mine_exit": fm.returncode,
        "fragment_mine_tail": (fm.stdout or fm.stderr or "")[-400:],
        "gate_exit": gate.returncode,
        "gate_tail": (gate.stdout or gate.stderr or "")[-200:],
        "reproduce": "py scripts/run_pull_ijeoma_nl_priority_sources_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "pulls": len(rows), "out": str(OUT)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
