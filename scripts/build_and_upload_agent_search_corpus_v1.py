#!/usr/bin/env python3
"""Build Agent Search corpus PDFs and upload to GCS.

Profiles:
  logos-ops (default) — Logos Track L/B ops docs, contracts, graph stats; no OpenData 327.
  legacy — 327 + mkmlife + a-codeai evidence (pre-2026-05-30 bundle).
  system2-gate — Gate-verified rows from reports/agent_search_corpus/system2-gate/*.md
  all — union of logos-ops + legacy.

LG-closed lane excluded. Uses headless Edge/Chrome PDF export (same as OpenData 327 export).

GCS objects use flat names under ``agent-search-docs/`` (``{pack}__{filename}.pdf``) because
Discovery Engine import glob ``agent-search-docs/*.pdf`` does not recurse into subfolders.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
REPORTS = ROOT / "reports" / "agent_search_corpus"
MANIFEST = REPORTS / "agent_search_corpus_upload_v1_latest.json"

DEFAULT_PROJECT = "mkm-lab-agi-2025"
DEFAULT_BUCKET = "mkm-lab-agi-2025-vertex-ai-staging"
DEFAULT_GCS_ROOT = "agent-search-docs"
SYSTEM2_GATE_DIR = ROOT / "reports" / "agent_search_corpus" / "system2-gate"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_to_md(path: Path, title: str) -> str:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    body = json.dumps(data, ensure_ascii=False, indent=2)
    return f"# {title}\n\nSource: `{path.relative_to(ROOT).as_posix()}`\n\n```json\n{body}\n```\n"


def _entry(
    *,
    pack: str,
    pdf_name: str,
    source: Path,
    kind: str,
    title: str,
) -> dict[str, Any]:
    return {
        "pack": pack,
        "pdf_name": pdf_name,
        "source": source,
        "kind": kind,
        "title": title,
    }


def _legacy_prebuilt_pdf_entries() -> list[dict[str, Any]]:
    """Already-exported submission PDFs (no MD→HTML pass)."""
    items = [
        (
            "opendata-327",
            "opendata_327_part_b_business_plan_v1.pdf",
            ROOT / "reports/opendata_327_part_b_v1.pdf",
        ),
        (
            "opendata-327",
            "opendata_327_submission_bcd_merged_v1.pdf",
            ROOT / "reports/opendata_327_submission_bcd_merged_v1.pdf",
        ),
        (
            "opendata-327",
            "moksori_ai_opendata327_task1_business_plan_v1.pdf",
            ROOT / "reports/moksori_ai_opendata327_task1_business_plan_v1.pdf",
        ),
        (
            "opendata-327",
            "opendata_327_part_a_cover_draft_v1.pdf",
            ROOT / "reports/opendata_327_part_a_cover_draft_v1.pdf",
        ),
    ]
    out: list[dict[str, Any]] = []
    for pack, pdf_name, src in items:
        if not src.is_file():
            out.append(
                {
                    "pack": pack,
                    "pdf_name": pdf_name,
                    "source": src.relative_to(ROOT).as_posix(),
                    "kind": "pdf",
                    "ok": False,
                    "error": "missing prebuilt pdf",
                }
            )
            continue
        local = REPORTS / pack / pdf_name
        local.parent.mkdir(parents=True, exist_ok=True)
        if src.resolve() != local.resolve():
            local.write_bytes(src.read_bytes())
        size_kb = round(local.stat().st_size / 1024, 1)
        out.append(
            {
                "pack": pack,
                "pdf_name": pdf_name,
                "source": src.relative_to(ROOT).as_posix(),
                "kind": "pdf",
                "ok": True,
                "local_pdf": local.relative_to(ROOT).as_posix(),
                "size_kb": size_kb,
                "gcs_object": f"{DEFAULT_GCS_ROOT}/{pack}__{pdf_name}",
            }
        )
    return out


def _legacy_corpus_entries() -> list[dict[str, Any]]:
    return [
        _entry(
            pack="opendata-327",
            pdf_name="opendata_327_kstartup_checklist_v1.pdf",
            source=ROOT / "docs/final/artifacts/opendata_327_kstartup_submission_checklist_v1_latest.md",
            kind="md",
            title="OpenData 327 K-Startup Checklist",
        ),
        _entry(
            pack="opendata-327",
            pdf_name="opendata_327_parallel_lane_checklist_v1.pdf",
            source=ROOT / "docs/final/artifacts/opendata_327_parallel_lane_checklist_v1_latest.json",
            kind="json",
            title="OpenData 327 Parallel Lane Checklist",
        ),
        _entry(
            pack="opendata-327",
            pdf_name="b2g_control_integrity_annex_v1.pdf",
            source=ROOT / "docs/final/B2G_CONTROL_INTEGRITY_PROPOSAL_ANNEX_V1.md",
            kind="md",
            title="B2G Control Integrity Annex",
        ),
        _entry(
            pack="mkmlife-magic-orb",
            pdf_name="track_c_external_positioning_dual_audience_v1.pdf",
            source=ROOT / "docs/final/artifacts/track_c_external_positioning_dual_audience_v1_latest.md",
            kind="md",
            title="Track C External Positioning (mkmlife Magic Orb)",
        ),
        _entry(
            pack="mkmlife-magic-orb",
            pdf_name="magic_orb_search_hud_v1_schema.pdf",
            source=ROOT / "docs/final/schemas/magic_orb_search_hud_v1.schema.json",
            kind="json",
            title="Magic Orb search_hud v1 schema",
        ),
        _entry(
            pack="a-codeai-evidence",
            pdf_name="compression_b2b_pilot_onepager_v1.pdf",
            source=ROOT / "docs/final/artifacts/compression_b2b_pilot_onepager_v1.md",
            kind="md",
            title="Compression B2B Pilot Onepager",
        ),
        _entry(
            pack="a-codeai-evidence",
            pdf_name="public_facing_security_ip_checklist_v1.pdf",
            source=ROOT / "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md",
            kind="md",
            title="Public Facing Security and IP Checklist",
        ),
        _entry(
            pack="a-codeai-evidence",
            pdf_name="lora_pack_qwen_operational_policy_v1.pdf",
            source=ROOT / "docs/final/artifacts/lora_pack_qwen_operational_policy_v1.json",
            kind="json",
            title="LoRA Pack Qwen Operational Policy",
        ),
    ]


def _logos_ops_corpus_entries() -> list[dict[str, Any]]:
    """MKM Logos ops librarian pack — contracts, graph stats, NON_GATING guardrails."""
    pack = "logos-ops"
    return [
        _entry(
            pack=pack,
            pdf_name="logos_track_l_charter_v1.pdf",
            source=ROOT / "docs/final/LOGOS_HERMENEUTICS_TRACK_L_CHARTER_V1.md",
            kind="md",
            title="Logos Hermeneutics Track L Charter v1",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_original_language_graph_rag_bridge_v1.pdf",
            source=ROOT / "docs/final/LOGOS_ORIGINAL_LANGUAGE_GRAPH_RAG_BRIDGE_V1.md",
            kind="md",
            title="Logos Original Language GraphRAG Bridge v1",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_promotion_gate_checklist_l0_l12_v1.pdf",
            source=ROOT / "docs/final/MKM_PROMOTION_GATE_CHECKLIST_L0_L12_V1.md",
            kind="md",
            title="MKM Logos Promotion Gate Checklist L0-L12",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_s1_shadow_promotion_review_packet_v1.pdf",
            source=ROOT / "docs/final/artifacts/logos_s1_shadow_promotion_review_packet_latest.md",
            kind="md",
            title="Logos S1 Shadow Promotion Review Packet",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_corpus_manifest_contract_v1.pdf",
            source=ROOT / "docs/final/artifacts/LOGOS_CORPUS_MANIFEST_V1_CONTRACT.json",
            kind="json",
            title="LOGOS Corpus Manifest v1 Contract",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_corpus_graph_bundle_contract_v1.pdf",
            source=ROOT / "docs/final/artifacts/LOGOS_CORPUS_GRAPH_BUNDLE_V1_CONTRACT.json",
            kind="json",
            title="LOGOS Corpus Graph Bundle v1 Contract",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_track_b_deep_fusion_job_contract_v1.pdf",
            source=ROOT / "docs/final/artifacts/LOGOS_TRACK_B_DEEP_FUSION_JOB_V1_CONTRACT.json",
            kind="json",
            title="LOGOS Track B Deep Fusion Job v1 Contract",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_corpus_manifest_snapshot_v1.pdf",
            source=ROOT / "docs/final/artifacts/logos_corpus_manifest_v1_latest.json",
            kind="json",
            title="Logos Corpus Manifest Snapshot (31102 verses)",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_corpus_graph_bundle_snapshot_v1.pdf",
            source=ROOT / "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json",
            kind="json",
            title="Logos Corpus Graph Bundle Snapshot (nodes/edges stats)",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_track_l_l1_readiness_v1.pdf",
            source=ROOT / "docs/final/artifacts/logos_track_l_l1_readiness_v1_latest.json",
            kind="json",
            title="Logos Track L L1 Readiness Report",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_track_l_l2_readiness_v1.pdf",
            source=ROOT / "docs/final/artifacts/logos_track_l_l2_readiness_v1_latest.json",
            kind="json",
            title="Logos Track L L2 Readiness Report",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_track_l_l3_readiness_v1.pdf",
            source=ROOT / "docs/final/artifacts/logos_track_l_l3_readiness_v1_latest.json",
            kind="json",
            title="Logos Track L L3 GraphRAG Bridge Readiness",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_track_l_l4_l5_readiness_v1.pdf",
            source=ROOT / "docs/final/artifacts/logos_track_l_l4_l5_readiness_v1_latest.json",
            kind="json",
            title="Logos Track L L4/L5 Evidence Pack Readiness",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_graphrag_bridge_evidence_pack_v1.pdf",
            source=ROOT / "docs/final/artifacts/logos_graphrag_bridge_evidence_pack_v1_latest.md",
            kind="md",
            title="Logos GraphRAG Bridge Evidence Pack v1",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_track_l_l9_l12_readiness_v1.pdf",
            source=ROOT / "docs/final/artifacts/logos_track_l_l9_l12_readiness_v1_latest.json",
            kind="json",
            title="Logos Track L L9-L12 External Send Readiness",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_track_l_external_send_signoff_v1.pdf",
            source=ROOT / "docs/final/artifacts/logos_track_l_external_send_signoff_v1_latest.json",
            kind="json",
            title="Logos Track L External Send Sign-off Template",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_track_l_commander_external_send_ack_v1.pdf",
            source=ROOT / "docs/final/artifacts/logos_track_l_commander_external_send_ack_v1_latest.json",
            kind="json",
            title="Logos Track L Commander External Send Ack",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_track_l_l6_l8_readiness_v1.pdf",
            source=ROOT / "docs/final/artifacts/logos_track_l_l6_l8_readiness_v1_latest.json",
            kind="json",
            title="Logos Track L L6-L8 S1 Shadow Advisory Readiness",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_s1_shadow_promotion_human_approval_v1.pdf",
            source=ROOT / "docs/final/artifacts/logos_s1_shadow_promotion_human_approval_latest.json",
            kind="json",
            title="Logos S1 Shadow Human Approval Record",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_shadow_promotion_kpi_progress_v1.pdf",
            source=ROOT / "docs/final/artifacts/logos_shadow_promotion_kpi_progress_latest.json",
            kind="json",
            title="Logos Shadow Promotion KPI Progress",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_track_l_l0_readiness_v1.pdf",
            source=ROOT / "docs/final/artifacts/logos_track_l_l0_readiness_v1_latest.json",
            kind="json",
            title="Logos Track L L0 Readiness Report",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_candidate_edges_offline_knn_chain_v1.pdf",
            source=ROOT / "docs/final/artifacts/logos_candidate_edges_offline_knn_chain_v1_latest.json",
            kind="json",
            title="Logos Candidate Edges Offline KNN Chain v1",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_insight_bundle_schema_v1.pdf",
            source=ROOT / "docs/final/schemas/logos_insight_bundle_v1.schema.json",
            kind="json",
            title="Logos Insight Bundle v1 Schema",
        ),
        _entry(
            pack=pack,
            pdf_name="graph_subgraph_router_lane_contract_v1.pdf",
            source=ROOT / "docs/final/artifacts/graph_subgraph_router_lane_contract_v1_latest.json",
            kind="json",
            title="Graph Subgraph Router Lane Contract v1",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_subgraph_graphrag_router_schema_v1.pdf",
            source=ROOT / "docs/final/schemas/logos_subgraph_graphrag_router_v1.schema.json",
            kind="json",
            title="Logos Subgraph GraphRAG Router Schema v1",
        ),
        _entry(
            pack=pack,
            pdf_name="magic_orb_search_hud_v1_schema.pdf",
            source=ROOT / "docs/final/schemas/magic_orb_search_hud_v1.schema.json",
            kind="json",
            title="Magic Orb search_hud v1 schema (mkmlife surface)",
        ),
        _entry(
            pack=pack,
            pdf_name="track_c_external_positioning_dual_audience_v1.pdf",
            source=ROOT / "docs/final/artifacts/track_c_external_positioning_dual_audience_v1_latest.md",
            kind="md",
            title="Track C External Positioning (Magic Orb / Logos surface)",
        ),
        _entry(
            pack=pack,
            pdf_name="public_facing_security_ip_checklist_v1.pdf",
            source=ROOT / "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md",
            kind="md",
            title="Public Facing Security and IP Checklist (NON_GATING copy guard)",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_candidate_edge_human_review_pack_v1.pdf",
            source=ROOT / "reports/logos_candidate_edge_human_review_pack_v1_latest.md",
            kind="md",
            title="Logos Candidate Edge Human Review Pack v1",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_candidate_edge_review_triage_v1.pdf",
            source=ROOT / "reports/logos_candidate_edge_review_triage_v1_latest.md",
            kind="md",
            title="Logos Candidate Edge Review Triage v1",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_review_queue_covenant_convergence_v1.pdf",
            source=ROOT / "docs/final/artifacts/logos_review_queue_covenant_convergence_v1_latest.json",
            kind="json",
            title="Logos Covenant Convergence Review Subset",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_covenant_convergence_review_pack_v1.pdf",
            source=ROOT / "reports/logos_covenant_convergence_review_pack_v1_latest.md",
            kind="md",
            title="Logos Covenant Convergence Commander Review Pack",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_candidate_edge_saturation_handoff_v1.pdf",
            source=ROOT / "reports/logos_candidate_edge_saturation_handoff_v1_latest.md",
            kind="md",
            title="Logos Candidate Edge Saturation Handoff (next-stage planning)",
        ),
        _entry(
            pack=pack,
            pdf_name="logos_candidate_edge_post_saturation_maintenance_v1.pdf",
            source=ROOT / "docs/final/artifacts/logos_candidate_edge_post_saturation_maintenance_v1_latest.json",
            kind="json",
            title="Logos Candidate Edge Post-Saturation Maintenance Report",
        ),
    ]


def _system2_gate_corpus_entries() -> list[dict[str, Any]]:
    """Dynamic entries from export_system2_vertex_staging_pack_v1.py output."""
    pack = "system2-gate"
    if not SYSTEM2_GATE_DIR.is_dir():
        return []
    entries: list[dict[str, Any]] = []
    for md in sorted(SYSTEM2_GATE_DIR.glob("*.md")):
        entries.append(
            _entry(
                pack=pack,
                pdf_name=f"{md.stem}.pdf",
                source=md,
                kind="md",
                title=f"System2 gate verified row ({md.stem})",
            )
        )
    return entries


def _resolve_profile(profile: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    key = profile.strip().lower()
    if key == "logos-ops":
        return _logos_ops_corpus_entries(), [], key
    if key == "system2-gate":
        return _system2_gate_corpus_entries(), [], key
    if key == "legacy":
        return _legacy_corpus_entries(), _legacy_prebuilt_pdf_entries(), key
    if key == "all":
        entries = _logos_ops_corpus_entries() + _legacy_corpus_entries()
        seen: set[tuple[str, str]] = set()
        deduped: list[dict[str, Any]] = []
        for entry in entries:
            sig = (entry["pack"], entry["pdf_name"])
            if sig in seen:
                continue
            seen.add(sig)
            deduped.append(entry)
        return deduped, _legacy_prebuilt_pdf_entries(), key
    raise SystemExit(f"unknown --profile {profile!r} (logos-ops | legacy | system2-gate | all)")


def _export_pdf(*, entry: dict[str, Any], browser: Path, dry_run: bool) -> dict[str, Any]:
    from export_opendata_327_submission_pdf_v1 import _export_part

    pack = entry["pack"]
    pdf_local = REPORTS / pack / entry["pdf_name"]
    html_local = pdf_local.with_suffix(".html")
    src: Path = entry["source"]
    if not src.is_file():
        return {
            "pack": entry["pack"],
            "pdf_name": entry["pdf_name"],
            "source": str(entry["source"].relative_to(ROOT).as_posix()),
            "ok": False,
            "error": f"missing source",
        }

    if dry_run:
        return {
            "pack": entry["pack"],
            "pdf_name": entry["pdf_name"],
            "source": src.relative_to(ROOT).as_posix(),
            "ok": True,
            "dry_run": True,
            "local_pdf": pdf_local.relative_to(ROOT).as_posix(),
            "gcs_object": f"{DEFAULT_GCS_ROOT}/{pack}__{entry['pdf_name']}",
        }

    if entry["kind"] == "md":
        part = _export_part(
            browser=browser,
            source_md=src,
            html_out=html_local,
            pdf_out=pdf_local,
            title=entry["title"],
        )
    else:
        md_text = _json_to_md(src, entry["title"])
        tmp_md = html_local.with_suffix(".source.md")
        tmp_md.parent.mkdir(parents=True, exist_ok=True)
        tmp_md.write_text(md_text, encoding="utf-8")
        part = _export_part(
            browser=browser,
            source_md=tmp_md,
            html_out=html_local,
            pdf_out=pdf_local,
            title=entry["title"],
        )

    return {
        "pack": pack,
        "pdf_name": entry["pdf_name"],
        "source": src.relative_to(ROOT).as_posix(),
        "kind": entry["kind"],
        "title": entry["title"],
        "ok": True,
        "local_pdf": part["pdf"],
        "size_kb": part["size_kb"],
        "gcs_object": f"{DEFAULT_GCS_ROOT}/{pack}__{entry['pdf_name']}",
    }


def _upload_pdfs(rows: list[dict[str, Any]], *, project: str, bucket: str, dry_run: bool) -> list[dict[str, Any]]:
    try:
        from google.cloud import storage
    except ImportError:
        print('Install: py -m pip install "google-cloud-storage>=2.14.0"', file=sys.stderr)
        raise SystemExit(2) from None

    client = storage.Client(project=project)
    bkt = client.bucket(bucket)
    out: list[dict[str, Any]] = []
    for row in rows:
        if not row.get("ok"):
            out.append(row)
            continue
        if row.get("dry_run"):
            out.append({**row, "uploaded": False})
            continue
        local = ROOT / row["local_pdf"]
        obj = row["gcs_object"]
        if dry_run:
            out.append({**row, "uploaded": False, "dry_run_upload": True})
            continue
        blob = bkt.blob(obj)
        blob.upload_from_filename(str(local), content_type="application/pdf")
        out.append({**row, "uploaded": True, "gs_uri": f"gs://{bucket}/{obj}"})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--profile",
        default="logos-ops",
        choices=("logos-ops", "legacy", "system2-gate", "all"),
        help="Corpus pack (default: logos-ops; system2-gate = gate-verified MD rows)",
    )
    ap.add_argument("--project", default=DEFAULT_PROJECT)
    ap.add_argument("--bucket", default=DEFAULT_BUCKET)
    ap.add_argument("--dry-run", action="store_true", help="Plan only; no PDF export or GCS upload")
    ap.add_argument("--skip-upload", action="store_true", help="Export PDFs locally only")
    args = ap.parse_args()

    from export_opendata_327_submission_pdf_v1 import _find_browser

    entries, prebuilt, profile_key = _resolve_profile(args.profile)
    browser = None if args.dry_run else _find_browser()
    rows: list[dict[str, Any]] = []
    for entry in entries:
        src: Path = entry["source"]
        if not src.is_file():
            rows.append(
                {
                    "pack": entry["pack"],
                    "pdf_name": entry["pdf_name"],
                    "source": src.relative_to(ROOT).as_posix() if src.is_relative_to(ROOT) else str(src),
                    "ok": False,
                    "error": "missing source (optional pack row skipped)",
                    "skipped": True,
                }
            )
            continue
        if args.dry_run:
            rows.append(_export_pdf(entry=entry, browser=Path("."), dry_run=True))
        else:
            assert browser is not None
            rows.append(_export_pdf(entry=entry, browser=browser, dry_run=False))
    rows.extend(prebuilt)

    if not args.dry_run and not args.skip_upload:
        rows = _upload_pdfs(rows, project=args.project, bucket=args.bucket, dry_run=False)
    elif args.skip_upload and not args.dry_run:
        for i, row in enumerate(rows):
            rows[i] = {**row, "uploaded": False, "skip_upload": True}

    manifest = {
        "schema": "agent_search_corpus_upload_v1",
        "generated_at_utc": _utc_now(),
        "profile": profile_key,
        "project": args.project,
        "bucket": args.bucket,
        "gcs_root": DEFAULT_GCS_ROOT,
        "excluded": ["lg_hs_*", "track_c_b2b_outreach_shelf", "bible_raw_corpus_66books"],
        "all_ok": all(r.get("ok") or r.get("skipped") for r in rows),
        "uploaded_count": sum(1 for r in rows if r.get("uploaded")),
        "rows": rows,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": manifest["all_ok"], "manifest": str(MANIFEST), "rows": rows}, ensure_ascii=False))
    return 0 if manifest["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
