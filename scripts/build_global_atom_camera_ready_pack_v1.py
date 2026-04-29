#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build camera-ready draft + appendix from global atom pack artifacts.")
    ap.add_argument("--onepager-json", default="docs/final/artifacts/global_atom_network_academic_onepager_latest.json")
    ap.add_argument("--kdd-template-json", default="docs/final/artifacts/global_atom_kdd_submission_template_latest.json")
    ap.add_argument("--bundle-json", default="docs/final/artifacts/global_atom_submission_bundle_latest.json")
    ap.add_argument("--paper-out-md", default="docs/final/artifacts/global_atom_camera_ready_paper_draft_latest.md")
    ap.add_argument("--appendix-out-md", default="docs/final/artifacts/global_atom_camera_ready_appendix_latest.md")
    ap.add_argument("--manifest-out-json", default="docs/final/artifacts/global_atom_camera_ready_pack_latest.json")
    args = ap.parse_args()

    one_path = resolve(args.onepager_json)
    kdd_path = resolve(args.kdd_template_json)
    bnd_path = resolve(args.bundle_json)
    for p in (one_path, kdd_path, bnd_path):
        if not p.is_file():
            raise SystemExit(f"missing required input: {p}")

    one = load(one_path)
    kdd = load(kdd_path)
    bnd = load(bnd_path)
    facts = one.get("key_facts") if isinstance(one.get("key_facts"), dict) else {}
    stage_rows = one.get("stage_breakdown") if isinstance(one.get("stage_breakdown"), list) else []
    lineage = one.get("run_lineage") if isinstance(one.get("run_lineage"), dict) else {}
    methods = one.get("method_outline_en") if isinstance(one.get("method_outline_en"), list) else []
    risks = one.get("risk_notes_en") if isinstance(one.get("risk_notes_en"), list) else []
    contributions = kdd.get("contributions_en") if isinstance(kdd.get("contributions_en"), list) else []
    keywords = kdd.get("keywords_en") if isinstance(kdd.get("keywords_en"), list) else []

    stage_lines = []
    for s in stage_rows:
        if not isinstance(s, dict):
            continue
        stage_lines.append(
            f"- `{s.get('stage')}`: target={s.get('target_count')}, nodes={s.get('node_count')}, "
            f"edges={s.get('edge_count')}, signal={s.get('phase_transition_signal')}"
        )

    paper_md = "\n".join(
        [
            f"# {kdd.get('title_en')}",
            "",
            "## Abstract",
            str(kdd.get("abstract_en_180w", "")),
            "",
            "## Contributions",
            *[f"- {c}" for c in contributions],
            "",
            "## Method",
            *[f"- {m}" for m in methods],
            "",
            "## Main Results",
            f"- Nodes: `{facts.get('node_count')}`",
            f"- Edges: `{facts.get('edge_count')}`",
            f"- Stage completion: `{facts.get('batch_stages_ok')}/{facts.get('batch_stages_total')}`",
            f"- Source mode: `{facts.get('batch_source_mode')}`",
            f"- Gate status: `{facts.get('gate_status')}`",
            "",
            "## Stage Breakdown",
            *stage_lines,
            "",
            "## Risks",
            *[f"- {r}" for r in risks],
            "",
            "## Reproducibility",
            f"- run_stamp: `{lineage.get('run_stamp')}`",
            f"- stage range: `{lineage.get('start_stage')} -> {lineage.get('end_stage')}`",
            "",
        ]
    ).strip() + "\n"

    packet = bnd.get("artifact_packet") if isinstance(bnd.get("artifact_packet"), dict) else {}
    appendix_md = "\n".join(
        [
            "# Appendix: Evidence & Reproduction",
            "",
            "## Keywords",
            ", ".join(str(k) for k in keywords),
            "",
            "## Artifact Packet",
            *[f"- `{k}`: `{(v or {}).get('path')}`" for k, v in packet.items() if isinstance(v, dict)],
            "",
            "## Suggested Commands",
            "- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_global_atom_full_canon_batch_v1.ps1 -UseEventSource`",
            "- `py scripts/build_global_atom_full_canon_consolidated_manifest_v1.py`",
            "- `py scripts/build_global_atom_full_canon_batch_report_v1.py --stages-json docs/final/artifacts/global_atom_full_canon/global_atom_full_canon_consolidated_manifest_latest.json --output-json docs/final/artifacts/global_atom_full_canon_batch_report_latest.json`",
            "- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_global_atom_submission_pack_v1.ps1`",
            "",
        ]
    ).strip() + "\n"

    paper_out = resolve(args.paper_out_md)
    app_out = resolve(args.appendix_out_md)
    manifest_out = resolve(args.manifest_out_json)
    paper_out.parent.mkdir(parents=True, exist_ok=True)
    paper_out.write_text(paper_md, encoding="utf-8")
    app_out.write_text(appendix_md, encoding="utf-8")

    out = {
        "schema": "global_atom_camera_ready_pack_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "inputs": {
            "onepager_json": str(one_path),
            "kdd_template_json": str(kdd_path),
            "bundle_json": str(bnd_path),
        },
        "outputs": {
            "paper_draft_md": str(paper_out),
            "appendix_md": str(app_out),
        },
    }
    manifest_out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(manifest_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

