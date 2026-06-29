#!/usr/bin/env python3
"""RQ-028/029 human sign-off archive pack ([HYPO] · does not close RQ or promote Track A)."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/a_code_governor_signoff_archive_pack_v1_latest.json"
DEFAULT_MD = ROOT / "reports/a_code_governor_signoff_archive_pack_v1_latest.md"

ARTIFACT_PATHS = [
    "reports/a_code_governor_evidence_pack_v1_latest.json",
    "reports/a_code_governor_promotion_gate_v1_latest.json",
    "reports/a_code_promotion_checklist_readiness_v1_latest.json",
    "reports/a_code_promotion_rq_readiness_v1_latest.json",
    "docs/final/artifacts/a_code_operator_assist_lane_v1_latest.json",
    "reports/a_code_operator_assist_lane_gate_v1_latest.json",
    "reports/a_code_constitution_pointer_row_check_v1_latest.json",
    "docs/final/artifacts/a_code_promotion_rq_commander_ack_v1_latest.json",
    "reports/a_code_rq_close_gate_v1_latest.json",
    "docs/final/artifacts/a_code_closure_readiness_v1_latest.json",
    "reports/a_code_rq_close_human_checklist_v1_latest.json",
    "reports/a_code_research_close_migration_draft_v1_latest.json",
    "reports/a_code_weekly_ops_summary_v1_latest.md",
    "docs/final/artifacts/a_code_commander_close_v1_latest.json",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _import_signoff_resolver():
    path = ROOT / "scripts/a_code_commander_signoff_resolve_v1.py"
    spec = importlib.util.spec_from_file_location("signoff_resolve", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _import_ack_resolver():
    path = ROOT / "scripts/a_code_promotion_rq_ack_resolve_v1.py"
    spec = importlib.util.spec_from_file_location("ack_resolve", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_pack() -> dict[str, Any]:
    signoff_mod = _import_signoff_resolver()
    ack_mod = _import_ack_resolver()
    signoff_path, signoff_source = signoff_mod.resolve_commander_a_code_signoff_path(None)
    ack_path, ack_source = ack_mod.resolve_promotion_rq_ack_path(None)

    files: list[dict[str, Any]] = []
    for rel in ARTIFACT_PATHS:
        p = ROOT / rel
        files.append(
            {
                "path": rel,
                "present": p.is_file(),
                "sha256": _sha256(p),
            }
        )

    checklist = _read_json(ROOT / "reports/a_code_promotion_checklist_readiness_v1_latest.json")
    promotion_rq = _read_json(ROOT / "reports/a_code_promotion_rq_readiness_v1_latest.json")
    operator_lane = _read_json(ROOT / "docs/final/artifacts/a_code_operator_assist_lane_v1_latest.json")
    rq_close_gate = _read_json(ROOT / "reports/a_code_rq_close_gate_v1_latest.json")
    closure_readiness = _read_json(ROOT / "docs/final/artifacts/a_code_closure_readiness_v1_latest.json")
    commander_close = _read_json(ROOT / "docs/final/artifacts/a_code_commander_close_v1_latest.json")

    signoff_doc = _read_json(signoff_path) if signoff_path and signoff_path.is_file() else {}
    ack_doc = _read_json(ack_path) if ack_path and ack_path.is_file() else {}

    archive_ready = (
        checklist.get("summary", {}).get("mechanical_ready") is True
        and checklist.get("summary", {}).get("human_signoff_status") == "APPROVED"
        and promotion_rq.get("summary", {}).get("operator_lane_ready") is True
        and operator_lane.get("lane_status") == "OPERATOR_ASSIST_FIXED"
    )

    return {
        "schema": "a_code_governor_signoff_archive_pack_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "rq_ids": ["RQ-028", "RQ-029", "RQ-031"],
        "hypothesis_tier": "B",
        "research_only": True,
        "archive_ready": archive_ready,
        "rq_close_allowed": False,
        "track_a_auto_promotion": False,
        "live_trading_auto_trigger": False,
        "summary": {
            "mechanical_ready": checklist.get("summary", {}).get("mechanical_ready"),
            "human_signoff_status": checklist.get("summary", {}).get("human_signoff_status"),
            "promotion_discussion_eligible": checklist.get("summary", {}).get("promotion_discussion_eligible"),
            "operator_lane_ready": promotion_rq.get("summary", {}).get("operator_lane_ready"),
            "lane_status": operator_lane.get("lane_status"),
            "gate_decision": checklist.get("summary", {}).get("gate_decision"),
            "rq_close_gate_decision": (rq_close_gate.get("summary") or {}).get("decision"),
            "mechanical_close_candidate": (rq_close_gate.get("summary") or {}).get(
                "mechanical_close_candidate"
            ),
            "closure_readiness_mechanics_ok": closure_readiness.get("mechanics_bundle_ok"),
            "closure_allowed": closure_readiness.get("closure_allowed"),
            "commander_close_recorded": commander_close.get("rq_status") == "CLOSED",
        },
        "local_signoff": {
            "signoff_path": (
                str(signoff_path.relative_to(ROOT)).replace("\\", "/")
                if signoff_path and signoff_path.is_relative_to(ROOT)
                else (str(signoff_path) if signoff_path else None)
            ),
            "signoff_source": signoff_source,
            "approved": signoff_doc.get("approved"),
            "ack_path": (
                str(ack_path.relative_to(ROOT)).replace("\\", "/")
                if ack_path and ack_path.is_relative_to(ROOT)
                else (str(ack_path) if ack_path else None)
            ),
            "ack_source": ack_source,
            "acknowledged": ack_doc.get("acknowledged"),
        },
        "artifact_files": files,
        "constitution_pointer": "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md §1.2.2",
        "track_wall_note_ko": "아카이브 팩은 human sign-off 증거 묶음. RQ CLOSED·Track A/live 승격 아님.",
        "reproduction_commands": [
            "pwsh -File scripts/Run-ACodeGovernorSignoffArchiveBundle_v1.ps1",
            "pwsh -File scripts/Invoke-ACodeGovernorSmoke_v1.ps1",
        ],
    }


def render_md(doc: dict[str, Any]) -> str:
    s = doc.get("summary") or {}
    lines = [
        "# A-code governor sign-off archive pack",
        "",
        f"- generated_at_utc: `{doc.get('generated_at_utc')}`",
        f"- archive_ready: `{doc.get('archive_ready')}` · rq_close_allowed: `{doc.get('rq_close_allowed')}`",
        f"- mechanical_ready: `{s.get('mechanical_ready')}` · human_signoff: `{s.get('human_signoff_status')}`",
        f"- operator_lane_ready: `{s.get('operator_lane_ready')}` · lane_status: `{s.get('lane_status')}`",
        "",
        "## Closure phase",
        "",
        f"- rq_close_gate: `{(doc.get('summary') or {}).get('rq_close_gate_decision')}`",
        f"- closure_allowed: `{(doc.get('summary') or {}).get('closure_allowed')}`",
        f"- commander_close_recorded: `{(doc.get('summary') or {}).get('commander_close_recorded')}`",
        "",
        "## Track wall",
        "",
        "- archive pack ≠ RESEARCH 자동 CLOSED",
        "- Track A · live · MS paste 승격 **없음**",
        "",
        "## Artifact files",
        "",
    ]
    for f in doc.get("artifact_files") or []:
        flag = "OK" if f.get("present") else "MISS"
        lines.append(f"- [{flag}] `{f.get('path')}`")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    doc = build_pack()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(render_md(doc), encoding="utf-8")
    print(f"OK: {args.out_json} archive_ready={doc.get('archive_ready')}")
    if args.strict and not doc.get("archive_ready"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
