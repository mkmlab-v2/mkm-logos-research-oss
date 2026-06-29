#!/usr/bin/env python3
"""Build grant-proposal router tasks JSONL from OpenData 327 SSOT checklists (deterministic)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

CHECKLIST = ROOT / "docs/final/artifacts/opendata_327_kstartup_submission_checklist_v1_latest.json"
READINESS = ROOT / "reports/opendata_327_submission_readiness_latest.json"
PARALLEL = ROOT / "docs/final/artifacts/opendata_327_parallel_lane_checklist_v1_latest.json"
DEFAULT_OUT = ROOT / "data/grant_proposal/opendata_327_draft_tasks_v1.jsonl"
OPEN_INNO_OUT = ROOT / "data/grant_proposal/open_innovation_draft_tasks_v1.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _task(
    task_id: str,
    task_kind: str,
    *,
    grant_program: str = "opendata_327",
    ssot_ref: str = "",
    section: str = "",
    owner: str = "agent",
    notes: str = "",
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "task_id": task_id,
        "task_kind": task_kind,
        "grant_program": grant_program,
        "owner": owner,
    }
    if ssot_ref:
        row["ssot_ref"] = ssot_ref
    if section:
        row["section"] = section
    if notes:
        row["notes"] = notes
    return row


def build_opendata_327_tasks() -> list[dict[str, Any]]:
    checklist = _read_json(CHECKLIST)
    readiness = _read_json(READINESS) if READINESS.is_file() else {}
    parallel = _read_json(PARALLEL) if PARALLEL.is_file() else {}

    tasks: list[dict[str, Any]] = []

    # Agent/script gates (OD1, OD4, G1, G2, G4 auto)
    for gate in checklist.get("pre_submit_gates", []):
        gid = str(gate.get("id", ""))
        owner = str(gate.get("owner") or "agent_review")
        ssot = str(gate.get("ssot") or checklist.get("parent_checklist", ""))
        if owner == "human":
            kind = "legal_guarantee" if gid in ("G3", "G5") else "qualification_warranty"
            tasks.append(
                _task(
                    f"327-human-{gid.lower()}",
                    kind,
                    ssot_ref=ssot,
                    section=f"pre_submit_gate.{gid}",
                    owner="human",
                    notes=str(gate.get("check", "")),
                )
            )
        else:
            tasks.append(
                _task(
                    f"327-grep-{gid.lower()}",
                    "grep_evidence",
                    ssot_ref=ssot,
                    section=f"pre_submit_gate.{gid}",
                    owner="agent",
                    notes=str(gate.get("check", "")),
                )
            )

    for item in parallel.get("checklist", []):
        oid = str(item.get("id", ""))
        owner = str(item.get("owner", ""))
        if owner == "human":
            tasks.append(
                _task(
                    f"327-parallel-{oid.lower()}",
                    "qualification_warranty",
                    ssot_ref=str(item.get("submission_checklist_ssot") or PARALLEL),
                    section=f"parallel_lane.{oid}",
                    owner="human",
                    notes=str(item.get("item", "")),
                )
            )
        elif owner == "agent_review" and item.get("done"):
            tasks.append(
                _task(
                    f"327-parallel-{oid.lower()}-review",
                    "grep_evidence",
                    ssot_ref=str(item.get("evidence", "")),
                    section=f"parallel_lane.{oid}",
                    notes=str(item.get("item", "")),
                )
            )

    tasks.append(
        _task(
            "327-fact-technical-ready",
            "implementation_claim",
            ssot_ref="reports/opendata_327_submission_readiness_latest.json",
            section="technical_ready_for_pdf_bundle",
            notes="technical_ready≠legal sign-off; no K-Startup auto-submit",
        )
    )

    tasks.append(
        _task(
            "327-fact-forbidden-claims",
            "fact_lock_claim",
            ssot_ref="docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
            section="forbidden_in_submission",
            notes="; ".join(checklist.get("forbidden_in_submission", [])[:4]),
        )
    )

    # Document bundle → draft kinds
    doc_kind_map = {
        "DOC-PLAN": ("outline", "narrative_section"),
        "DOC-ANNEX": ("json_field_copy", "risk_legal"),
        "DOC-MARKET": ("narrative_section",),
        "DOC-BRN": ("json_field_copy",),
        "DOC-TECH": ("narrative_section", "implementation_claim"),
    }
    for doc in checklist.get("document_bundle", []):
        doc_id = str(doc.get("id", ""))
        ssot = str(doc.get("ssot", ""))
        kinds = doc_kind_map.get(doc_id, ("outline",))
        for idx, kind in enumerate(kinds):
            tasks.append(
                _task(
                    f"327-doc-{doc_id.lower()}-{kind}-{idx}",
                    kind,
                    ssot_ref=ssot,
                    section=f"document_bundle.{doc_id}",
                    notes=str(doc.get("item", "")),
                )
            )

    sub_md = checklist.get("submission_md") or {}
    tasks.append(
        _task(
            "327-table-part-b",
            "table_fill",
            ssot_ref=str(sub_md.get("part_b", "")),
            section="submission_md.part_b",
            notes="§2-2 tables; human_confirm_before_submit",
        )
    )
    tasks.append(
        _task(
            "327-narrative-part-c",
            "business_model",
            ssot_ref=str(sub_md.get("part_c", "")),
            section="submission_md.part_c",
            notes="market expansion; no compression OEM headline",
        )
    )

    # Schedule table from overview
    tasks.append(
        _task(
            "327-table-dev-schedule",
            "table_fill",
            ssot_ref="docs/final/artifacts/ai_opendata_challenge_2026_327_business_plan_overview_v1.md",
            section="1-2",
            notes="§1-2 개발 추진일정 표",
        )
    )

    for idx, line in enumerate(readiness.get("human_next", []), start=1):
        text = str(line)
        kind = "legal_guarantee" if "특허" in text or "출원" in text else "qualification_warranty"
        if "표지" in text:
            kind = "qualification_warranty"
        tasks.append(
            _task(
                f"327-human-next-{idx:02d}",
                kind,
                ssot_ref="reports/opendata_327_submission_readiness_latest.json",
                section="human_next",
                owner="human",
                notes=text,
            )
        )

    # Submission channels — always human
    for ch in checklist.get("parallel_channels_required", []):
        cid = str(ch.get("id", "ch")).lower()
        tasks.append(
            _task(
                f"327-channel-{cid}",
                "qualification_warranty",
                grant_program="opendata_327",
                ssot_ref=CHECKLIST.as_posix(),
                section=f"channel.{ch.get('id')}",
                owner="human",
                notes=str(ch.get("name", "")),
            )
        )

    return tasks


def build_open_innovation_stub_tasks() -> list[dict[str, Any]]:
    """Minimal open-innovation lane (no dedicated SSOT yet — generic scaffold)."""
    return [
        _task(
            "oi-outline-01",
            "outline",
            grant_program="open_innovation",
            ssot_ref="docs/final/artifacts/moksori_mega_commercialization_roadmap_from_repo_ssot_v1.md",
            section="phase_0_1",
            notes="internal scaffold only; not 327 submission",
        ),
        _task(
            "oi-narrative-problem",
            "narrative_section",
            grant_program="open_innovation",
            section="problem_statement",
        ),
        _task(
            "oi-narrative-solution",
            "differentiation",
            grant_program="open_innovation",
            section="solution_fit",
        ),
        _task(
            "oi-fact-lock",
            "fact_lock_claim",
            grant_program="open_innovation",
            ssot_ref="docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
        ),
        _task(
            "oi-legal-signoff",
            "legal_guarantee",
            grant_program="open_innovation",
            owner="human",
            notes="counsel / commander sign-off before external send",
        ),
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(r, ensure_ascii=False) for r in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_manifest(
    opendata_rows: list[dict[str, Any]],
    open_inno_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": "grant_proposal_tasks_manifest_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "sources": {
            "kstartup_checklist": str(CHECKLIST.resolve()),
            "readiness": str(READINESS.resolve()) if READINESS.is_file() else None,
            "parallel_lane": str(PARALLEL.resolve()) if PARALLEL.is_file() else None,
        },
        "counts": {
            "opendata_327": len(opendata_rows),
            "open_innovation": len(open_inno_rows),
            "total": len(opendata_rows) + len(open_inno_rows),
        },
        "outputs": {
            "opendata_327_jsonl": str(DEFAULT_OUT.resolve()),
            "open_innovation_jsonl": str(OPEN_INNO_OUT.resolve()),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="OpenData 327 tasks JSONL")
    ap.add_argument("--open-innovation-out", type=Path, default=OPEN_INNO_OUT)
    ap.add_argument(
        "--manifest-out",
        type=Path,
        default=ROOT / "reports/grant_proposal_tasks_manifest_v1_latest.json",
    )
    ap.add_argument("--skip-open-innovation", action="store_true")
    args = ap.parse_args()

    opendata = build_opendata_327_tasks()
    write_jsonl(args.out, opendata)

    open_inno: list[dict[str, Any]] = []
    if not args.skip_open_innovation:
        open_inno = build_open_innovation_stub_tasks()
        write_jsonl(args.open_innovation_out, open_inno)

    manifest = build_manifest(opendata, open_inno)
    args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_out.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "ok": True,
                "opendata_count": len(opendata),
                "open_innovation_count": len(open_inno),
                "out": str(args.out),
                "manifest": str(args.manifest_out),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
