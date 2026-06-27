#!/usr/bin/env python3
"""Build NotebookLM upload pack for 06 smartfarm notebook (deterministic).

SSOT: docs/NotebookLM_sources_manifest.md — 스마트팜·금산 IoT row
Output: reports/notebooklm_smartfarm_geumsan_sync_pack_v1/
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "notebooklm_smartfarm_geumsan_sync_pack_v1"
NOTEBOOK_URL = "https://notebooklm.google.com/notebook/96865180-769e-4a77-89bb-5f03a8083ac3"
NOTEBOOK_MCP_ID = "06-2026q2"

# Repo-relative paths to mirror into pack (skip missing)
PACK_PDF_SOURCES: list[str] = [
    "reports/smartfarm_vendor_replies/QuBICS_CoCoNET_6CH_릴레이_컨트롤러_매뉴얼.pdf",
    "reports/smartfarm_vendor_replies/QuBICS_CoCoNET_ETH형_MQTT_게이트웨이_매뉴얼.pdf",
    "reports/smartfarm_vendor_replies/QuBICS_CoCoNET_릴레이_제어_MQTT_프로토콜_설명서.pdf",
    "reports/smartfarm_vendor_replies/QuBICS_CoCoNET_토양온습도센서기기_매뉴얼.pdf",
    "reports/smartfarm_vendor_replies/QuBICS_CoCoNET_센서데이터_송수신_설명서_2604.pdf",
    "reports/smartfarm_vendor_replies/QuBICS_CoCoNET_WiFi형_MQTT_게이트웨이_매뉴얼_20260520.pdf",
]

PACK_SOURCES: list[str] = [
    "docs/final/artifacts/smartfarm_geumsan_artifact_index_v1.json",
    "docs/final/artifacts/smartfarm_qubics_contract_signed_v1.json",
    "docs/final/artifacts/smartfarm_qubics_device_manifest_v1.json",
    "docs/final/artifacts/smartfarm_qubics_http_ingest_spec_v1.json",
    "docs/final/artifacts/smartfarm_qubics_mqtt_control_spec_v1.example.json",
    "docs/final/artifacts/smartfarm_geumsan_6channel_valve_mapping_v1.json",
    "docs/final/artifacts/smartfarm_geumsan_field_install_checklist_owner_v1.md",
    "docs/final/artifacts/smartfarm_geumsan_3channel_valve_mapping_v1.json",
    "docs/final/artifacts/smartfarm_geumsan_gateway_commissioning_v1.example.json",
    "docs/final/artifacts/smartfarm_llm_vs_mkm_gate_checklist_v1.md",
    "docs/final/artifacts/smartfarm_geumsan_vendor_rfq_v2_2026-05-18.md",
    "docs/final/artifacts/smartfarm_geumsan_vendor_proposal_request_v1.md",
    "docs/final/artifacts/smartfarm_geumsan_vendor_outreach_execution_v1.md",
    "docs/final/artifacts/smartfarm_geumsan_vendor_quote_revision_email_v1.md",
    "docs/final/artifacts/smartfarm_geumsan_county_grant_pdf_checklist_v1.json",
    "docs/final/artifacts/smartfarm_geumsan_vendor_reply_gonogo_checklist_v1_latest.json",
    "reports/smartfarm_geumsan_autopilot_brief_latest.json",
    "reports/smartfarm_geumsan_revision_email_outbox_v1.json",
    "reports/smartfarm_geumsan_vendor_reply_gonogo_eval_latest.json",
    "reports/smartfarm_geumsan_parallel_vendor_brief_v1.json",
    "reports/smartfarm_vendor_outreach_log_v1.jsonl",
    "reports/qubics_pdf_extract_latest.json",
    "reports/smartfarm_qubics_mqtt_uplink_dry_run_latest.json",
    "reports/smartfarm_qubics_phase0_e2e_latest.json",
    "reports/notebooklm_golden40_compression_watch_v1.md",
    "reports/compression_track_a_headline_policy_v1_latest.json",
    "docs/final/AI_SMARTFARM_CONTROL_SAFETY_POLICY.yaml",
]

# Generated in pack only
GENERATED_NAMES = [
    "GEUMSAN_IOT_VENDOR_OUTREACH_SYNC_LATEST.md",
    "00_ops_handoff_snippet_mission_log.md",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_outreach_sync_md(out_dir: Path, file_names: list[str]) -> None:
    dest = out_dir / "GEUMSAN_IOT_VENDOR_OUTREACH_SYNC_LATEST.md"
    lines = [
        "# GEUMSAN IoT vendor outreach sync (auto-generated)",
        "",
        f"- generated_utc: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- notebook: {NOTEBOOK_MCP_ID}",
        f"- url: {NOTEBOOK_URL}",
        "",
        "## Pack files",
    ]
    for name in sorted(file_names):
        lines.append(f"- {name}")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_ops_snippet(dest: Path) -> None:
    mission = ROOT / "MISSION_LOG.md"
    text = mission.read_text(encoding="utf-8", errors="replace") if mission.is_file() else ""
    snippet_lines = [
        "# MISSION_LOG ops snippet (금산·스마트팜 · non-SSOT handoff)",
        "",
        f"extracted_utc: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "source: MISSION_LOG.md — 작전 보드 발췌 only",
        "",
        "## 금산·CoCoNET (2026-06-26)",
        "- SSOT: smartfarm_qubics_device_manifest_v1.json (D301/D302/D202/G300, smartfarm)",
        "- MQTT qbsv4 spec confirmed; subscriber dry-run pass",
        "- 체크리스트: smartfarm_llm_vs_mkm_gate_checklist_v1.md",
        "- 다음: VPS MQTT broker + 현장 cid commission",
        "",
        "## 핸드오프 요약 (2026-05-22~23)",
        "- 큐빅스 Go/No-Go: verdict=no_go (K3 API PDF, K7 출장, 3밸브 vs RFQ 2밸브)",
        "- IoT 478.5만원 (≤500만 PASS, revision 후 재산정)",
        "- NL 활성 노트: 06_스마트팜_진도관광농원_사업화_2026Q2",
        "",
        "## Golden 40 · 41658 (ops WATCH · headline HOLD)",
        "- ACTIVE disk: saving 49.1%, jaccard 0.873; floor regression PASS",
        "- MS·대외 headline HOLD 47.5%/0.890 (FAIL-COMP-004)",
        "- SSOT: reports/compression_track_a_headline_policy_v1_latest.json",
        "",
        "boundary: B-track·협상용; Track A·실매매·대외 3억/4배/1년BEP 합선 금지.",
    ]
    # Pull goldsan row from mission log if present
    for line in text.splitlines():
        if "금산·현장" in line and "|" in line:
            snippet_lines.append(f"- mission_log_row: {line.strip()}")
            break
    dest.write_text("\n".join(snippet_lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    prev_index: dict = {}
    prev_path = OUT / "index.json"
    if prev_path.is_file():
        prev_index = json.loads(prev_path.read_text(encoding="utf-8"))

    copied: list[str] = []
    missing: list[str] = []
    file_meta: list[dict] = []

    for rel in PACK_SOURCES + PACK_PDF_SOURCES:
        src = ROOT / rel.replace("/", "\\") if "\\" in rel else ROOT / rel
        if not src.is_file():
            missing.append(rel)
            continue
        dest_name = src.name
        dest = OUT / dest_name
        shutil.copy2(src, dest)
        copied.append(dest_name)
        file_meta.append(
            {
                "name": dest_name,
                "repo_path": rel.replace("\\", "/"),
                "sha256": _sha256(dest),
                "bytes": dest.stat().st_size,
            }
        )

    _write_ops_snippet(OUT / "00_ops_handoff_snippet_mission_log.md")
    for gen in GENERATED_NAMES:
        p = OUT / gen
        if p.is_file() and p.name not in {m["name"] for m in file_meta}:
            file_meta.append(
                {
                    "name": p.name,
                    "repo_path": "(generated)",
                    "sha256": _sha256(p),
                    "bytes": p.stat().st_size,
                }
            )
            copied.append(p.name)

    _write_outreach_sync_md(OUT, sorted({m["name"] for m in file_meta}))

    prev_hashes = {f.get("name"): f.get("sha256") for f in prev_index.get("files_meta", [])}
    delta_upload: list[str] = []
    for m in file_meta:
        if prev_hashes.get(m["name"]) != m["sha256"]:
            delta_upload.append(m["name"])

    index = {
        "schema": "notebooklm_smartfarm_geumsan_sync_pack_v1",
        "version": "1.1.0",
        "notebook_mcp_id": NOTEBOOK_MCP_ID,
        "notebook_url": NOTEBOOK_URL,
        "synced_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": sorted({m["name"] for m in file_meta}),
        "files_meta": file_meta,
        "delta_upload_recommended": delta_upload,
        "missing_repo_paths": missing,
        "nl_url_sources": ["https://farm.jema-ai.com/smartfarm"],
    }
    (OUT / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"out": str(OUT), "copied": len(copied), "delta": len(delta_upload), "missing": missing}, ensure_ascii=False))
    return 0 if not missing else 0  # warn only


if __name__ == "__main__":
    raise SystemExit(main())
