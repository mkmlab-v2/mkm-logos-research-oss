#!/usr/bin/env python3
"""Manifest for Logos GTM counsel export pack (paths only — no auto zip/send)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/logos_gtm_counsel_export_manifest_v1_latest.json"

FILES = [
    "docs/final/artifacts/logos_gtm_counsel_handoff_brief_v1_latest.md",
    "docs/final/artifacts/logos_gtm_linkedin_b2b_copy_variants_v1_latest.md",
    "docs/final/artifacts/logos_graph_studio_organic_b2b_outreach_v1_latest.md",
    "docs/final/artifacts/logos_track_l_external_send_signoff_v1_latest.json",
    "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md",
    "reports/logos_gtm_linkedin_b2b_copy_scan_v1_latest.json",
    "reports/logos_research_public_docs_copy_scan_v1_latest.json",
    "reports/logos_gtm_counsel_handoff_bundle_v1_latest.json",
    # INTERNAL_ONLY — LTM research slot (not public surface)
    "docs/research/nextgen_ltm_knowledge_os/NEXTGEN_LTM_KNOWLEDGE_OS_FACT_ONEPAGER_V1.md",
    "docs/research/nextgen_ltm_knowledge_os/FACT_HYPO_ROADMAP_MATRIX_V1.md",
    "docs/research/nextgen_ltm_knowledge_os/INDEX.json",
    "reports/nextgen_ltm_research_slot_v1_latest.json",
    # INTERNAL_ONLY — 4 forces / sasang matching layer (not public surface)
    "docs/research/four_forces_sasang_biophysical/FOUR_FORCES_SASANG_FACT_ONEPAGER_V1.md",
    "docs/research/four_forces_sasang_biophysical/LEXICON_ALIGNMENT_MATRIX_V1.md",
    "docs/research/four_forces_sasang_biophysical/FACT_HYPO_ROADMAP_MATRIX_V1.md",
    "docs/research/four_forces_sasang_biophysical/INDEX.json",
    "reports/four_forces_sasang_research_slot_v1_latest.json",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    entries: list[dict[str, Any]] = []
    missing: list[str] = []
    for rel in FILES:
        path = ROOT / rel.replace("/", "\\")
        ok = path.is_file()
        if not ok:
            missing.append(rel)
        entries.append({"path": rel, "ok": ok, "bytes": path.stat().st_size if ok else 0})

    doc = {
        "schema": "logos_gtm_counsel_export_manifest_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "file_count": sum(1 for e in entries if e["ok"]),
        "entries": entries,
        "missing": missing,
        "ok": not missing,
        "boundary_ack": "Manifest only; commander attaches files manually or via zip tool.",
        "reproduce": "py scripts/build_logos_gtm_counsel_export_manifest_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "file_count": doc["file_count"], "missing": len(missing)}))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
