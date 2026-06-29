#!/usr/bin/env python3
"""MS evidence pack — optional Track B B2B Logos logic verifier appendix (internal)."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MS_PACK = ROOT / "reports/external_validation_ms_evidence_pack_v1_latest"
DEFAULT_OUT = MS_PACK / "ms_b2b_logos_logic_verifier_appendix_v1.md"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def _build_md(
    *,
    master: dict[str, Any] | None,
    verifier: dict[str, Any] | None,
    xref: dict[str, Any] | None,
    macula: dict[str, Any] | None,
    registry: dict[str, Any] | None,
    graphrag_audit: dict[str, Any] | None,
    closure: dict[str, Any] | None,
) -> str:
    lines = [
        "# MS 부록 — Track B B2B 논리 검증기 (Logos 구조 이식)",
        "",
        f"> `{_utc()}` · **내부 부록만** · MS 1페이지 헤드라인·압축 KPI와 **합산 금지**",
        "",
        "## 격벽",
        "",
        "- `[HYPO]` · `NON_GATING` · `research_only`",
        "- 성경 **내용**·구절 인용은 제안서 카피로 승격하지 않음 — **논리 엔진·검증 절차**만",
        "- Track A·실매매·send_gate 자동 개방 아님",
        "",
        "## Goal Verifier",
        "",
    ]
    if verifier:
        lines.append(f"- verdict: `{verifier.get('verdict')}` · ok: `{verifier.get('ok')}`")
        lines.append(f"- reproduce: `{verifier.get('reproduce')}`")
    else:
        lines.append("- verifier artifact missing")
    lines.extend(["", "## MASTER_SUMMARY (광명백제 B2B)", ""])
    if master and master.get("promoted"):
        for c in master.get("promoted_claims") or []:
            lines.append(f"- `{c.get('claim_id')}`: {c.get('body_ko')}")
    else:
        lines.append("- not promoted — run `py scripts/run_logos_b2b_proposal_evolution_loop_v1.py`")
    lines.extend(["", "## Graph / MACULA / Xref (B-track)", ""])
    if macula:
        lines.append(f"- macula_themed_edges: `{macula.get('edges_built')}` (TSV=`{macula.get('macula_tsv_dir')}`)")
    if xref:
        lines.append(f"- xref_1hop_openbible: `{xref.get('total_edges')}` edges")
    if registry:
        rules = registry.get("retrieval_rules") or {}
        lines.append(f"- retrieval_rules: citation_lock=`{rules.get('citation_lock_before_narrative')}`")
    if graphrag_audit:
        sm = graphrag_audit.get("summary") or {}
        lines.append(
            f"- graphrag_seed_organic: `{sm.get('seed_hits_organic')}` · xref 후: `{sm.get('seed_hits_full')}`"
        )
    if closure:
        gates = closure.get("gates") or {}
        metrics = closure.get("metrics") or {}
        lines.append(f"- phase_l_ok: `{gates.get('phase_l_ok')}`")
        lines.append(f"- llm_citation_valid_themes: `{metrics.get('llm_citation_valid_themes')}`")
        lines.append(
            f"- topic_graphrag_seed_hits (6-topic): `{metrics.get('topic_graphrag_seed_hits')}`"
        )
    lines.extend(
        [
            "",
            "## 재현",
            "",
            "```powershell",
            "py scripts/run_logos_track_b_phase_m_v1.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--update-ms-manifest", action="store_true", default=True)
    ap.add_argument("--no-update-ms-manifest", action="store_false", dest="update_ms_manifest")
    args = ap.parse_args()

    master = _load(ROOT / "docs/final/artifacts/logos_b2b_proposal_master_summary_v1_latest.json")
    verifier = _load(ROOT / "reports/logos_b2b_proposal_goal_verifier_v1_latest.json")
    xref = _load(ROOT / "reports/logos_themed_xref_subgraph_v1_latest.json")
    macula = _load(ROOT / "reports/logos_macula_themed_ingest_v1_latest.json")
    registry = _load(ROOT / "docs/final/artifacts/logos_reasoning_pattern_registry_v1_latest.json")
    graphrag_audit = _load(ROOT / "reports/logos_themed_graphrag_seed_retrieval_v1_latest.json")
    closure = _load(ROOT / "reports/logos_track_b_integration_closure_v1_latest.json")

    md = _build_md(
        master=master,
        verifier=verifier,
        xref=xref,
        macula=macula,
        registry=registry,
        graphrag_audit=graphrag_audit,
        closure=closure,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md, encoding="utf-8")

    pointer = {
        "schema": "ms_b2b_logos_logic_verifier_appendix_pointer_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "internal_only": True,
        "appendix_md": str(args.out.relative_to(ROOT)).replace("\\", "/"),
        "verifier_ok": (verifier or {}).get("ok"),
        "master_promoted": (master or {}).get("promoted"),
        "reproduce": "py scripts/build_external_validation_ms_b2b_logic_appendix_v1.py",
    }
    pointer_path = MS_PACK / "ms_b2b_logos_logic_verifier_appendix_pointer_v1.json"
    pointer_path.write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.update_ms_manifest:
        manifest_path = MS_PACK / "manifest.json"
        if manifest_path.is_file():
            manifest = _load(manifest_path) or {}
            optional = manifest.setdefault("track_b_optional_appendix", [])
            entry = {
                "path": str(args.out.relative_to(ROOT)).replace("\\", "/"),
                "pointer": str(pointer_path.relative_to(ROOT)).replace("\\", "/"),
                "note": "B2B logic verifier — not for MS headline merge",
            }
            if entry not in optional:
                optional.append(entry)
            manifest["generated_at_utc"] = _utc()
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Copy hub draft pointer into pack for internal review
    hub = ROOT / "reports/gwangmyeong_baekje_b2b_static_hub_draft_v1.md"
    if hub.is_file() and MS_PACK.is_dir():
        shutil.copy2(hub, MS_PACK / "gwangmyeong_baekje_b2b_static_hub_draft_v1.md")

    ok = (verifier or {}).get("ok") is True and (master or {}).get("promoted") is True
    print(json.dumps({"ok": ok, "out": str(args.out.relative_to(ROOT)).replace("\\", "/")}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
