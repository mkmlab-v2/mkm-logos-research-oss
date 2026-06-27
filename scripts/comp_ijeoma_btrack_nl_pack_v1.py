#!/usr/bin/env python3
"""Build B-track NotebookLM ingest brief for 이제마 corpus (local pack, MCP-ready text)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
OUT_JSON = PILOT / "comp_ijeoma_btrack_nl_pack_v1.json"
OUT_MD = PILOT / "comp_ijeoma_btrack_nl_ingest_brief_v1.md"

READINESS = PILOT / "comp_corpus01_readiness_v1.json"
G5 = PILOT / "comp_sasang_g5_join_poc_v1.json"
QUERY_SET = ROOT / "data/corpus/ijeoma/_inventory/IJEOMA_NOTEBOOKLM_QUERY_SET_2026-03-29.md"
SASANG = ROOT / "docs/final/artifacts/SASANG_CROSS_REF_DRAFT.json"
NOTEBOOK_B_URL = "https://notebooklm.google.com/notebook/e6c1f050-40ef-49f0-8b2c-c509b8570cf4"
NOTEBOOK_PROPHECY_ID = "07-prophecy-btrack-2026q2"


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    PILOT.mkdir(parents=True, exist_ok=True)
    readiness = _read_json(READINESS)
    g5 = _read_json(G5)
    lines = [
        "# 이제마 B-track ingest brief (2026-05-20)",
        "",
        "[HYPO] / research_only — Track A·실매매·OOF 자동 합선 금지.",
        "",
        "## Corpus SSOT (workspace)",
        f"- corpus_import_ready: {readiness.get('corpus_import_ready')}",
        f"- verify_ijeoma_chunk_table_exit: {readiness.get('verify_ijeoma_chunk_table_exit')}",
        f"- sasang_cross_ref entries: {(readiness.get('sasang_cross_ref_draft') or {}).get('entry_count')}",
        "",
        "## G5 PoC",
        f"- g5_poc_ok: {g5.get('g5_poc_ok')}",
        f"- chunk_table_on_disk: {g5.get('chunk_table_on_disk')}",
        f"- entries_missing_chunk_id: {g5.get('entries_missing_chunk_id_in_table')}",
        "",
        "## NotebookLM targets",
        f"- Primary B research notebook (manifest): {NOTEBOOK_B_URL}",
        f"- MCP library prophecy lens id (optional cross-ref): `{NOTEBOOK_PROPHECY_ID}`",
        "",
        "## MCP add_source (text) suggested titles",
        "1. `MKM_IJEOMA_CORPUS_UNBLOCK_2026-05-20` — this brief",
        "2. `IJEOMA_NOTEBOOKLM_QUERY_SET` — query set MD (if restored)",
        "",
        "## Boundaries",
        "- 1차 레짐(regime_map) 주 · 2차 성경 보 — 실전 트리거 금지",
        "- Active compression KPI frozen 47.5% / bridge OFF unless commander approves",
        "",
    ]
    if QUERY_SET.is_file():
        qs = QUERY_SET.read_text(encoding="utf-8")
        if len(qs) > 12000:
            qs = qs[:12000] + "\n\n…[truncated for MCP text limit]\n"
        lines.extend(["## Query set excerpt", "", qs, ""])
    if SASANG.is_file():
        doc = json.loads(SASANG.read_text(encoding="utf-8"))
        lines.extend(
            [
                "## SASANG draft meta",
                f"- schema: {doc.get('schema')}",
                f"- entries: {len(doc.get('entries') or [])}",
                f"- disclaimer: {doc.get('disclaimer', '')[:200]}",
                "",
            ]
        )

    body = "\n".join(lines)
    OUT_MD.write_text(body, encoding="utf-8")
    pack = {
        "schema": "comp_ijeoma_btrack_nl_pack_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "brief_md": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        "brief_chars": len(body),
        "query_set_present": QUERY_SET.is_file(),
        "notebook_b_url": NOTEBOOK_B_URL,
        "mcp_steps": [
            "add_notebook(url=notebook_b_url) if not in library",
            f"add_source(type=text, notebook_id={NOTEBOOK_PROPHECY_ID} OR B url, title=MKM_IJEOMA_CORPUS_UNBLOCK)",
            "ask_question: 이제마 청크·SASANG cross-ref가 Track A 압축 KPI와 합선되지 않는 조건은?",
        ],
    }
    OUT_JSON.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote_md": OUT_MD.name, "wrote_json": OUT_JSON.name, "chars": len(body)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
