#!/usr/bin/env python3
"""CROSS_REF ENTRY_12/13 apply diff preview — draft read-only until commander approval [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CROSS_REF = ROOT / "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json"
EVIDENCE = ROOT / "reports/cross_ref_entry_12_13_evidence_sidecar_v1_latest.json"
RELABEL = ROOT / "reports/cross_ref_entry_13_shadow_verse_relabel_sidecar_v1_latest.json"
OUT_JSON = ROOT / "reports/cross_ref_entry_12_13_apply_diff_preview_v1_latest.json"
OUT_MD = ROOT / "reports/cross_ref_entry_12_13_apply_diff_preview_v1_latest.md"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _find_entry(cross: dict[str, Any], entry_id: str) -> dict[str, Any] | None:
    for row in cross.get("entries") or []:
        if row.get("entry_id") == entry_id:
            return row
    return None


def _proposed_entry_12() -> dict[str, Any]:
    sat = (
        "MT | loc=none (no Qumran Hebrew witness for Ps.4.6 in ETCBC/local scan) "
        "| refs=BHS/MT "
        "| status=mt_only_no_qumran_witness "
        "| prior_bench=11Q5(hypothesis_retired)"
    )
    note = (
        "P5/P8 update: 11Q5 bench retired (scroll Psalms 101+); no DSS line witness for Ps.4.6. "
        "canonical_ref Ps.4.6 retained for A-track state-10 bench label only. "
        "verified_anchor not claimed."
    )
    return {
        "entry_id": "ENTRY_12",
        "canonical_ref": "Ps.4.6",
        "satellite_ref": sat,
        "source_id": sat,
        "corpus_type": "mt",
        "link_type": "lexical",
        "confidence": None,
        "artifact_path": "reports/cross_ref_entry_12_13_evidence_sidecar_v1_latest.json",
        "state_candidate_id": 10,
        "rationale": "B-Track: MT-only bench after 11Q5 retirement. A-Track state 10 anchor Ps.4.6 — non-gating.",
        "note": note,
    }


def _proposed_entry_13(relabel: dict[str, Any], intake_row: dict[str, Any]) -> dict[str, Any]:
    wid = relabel.get("witness_id") or intake_row.get("witness_id")
    sat = (
        f"4Q98b | loc=frg.1 line 1; shadow_verse_anchor=Ps.5.8-9 "
        f"(bench canonical_ref Ps.5.2; MT v.2 direct line not verified) "
        f"| refs={relabel.get('edition_ref', 'DJD XVI; QD 4Q98b')} "
        f"| witness_id={wid} "
        f"| status=commander_verified_shadow_witness "
        f"| prior_bench=11Q5(retired)"
    )
    note = (
        "P7 commander promotion: 4Q98b frg.1 line 1 shadow witness for Ps 5:8-9 per DJD/QD. "
        "CROSS_REF canonical_ref stays Ps.5.2 (A-track state-11 bench). "
        "mt_ps_5_2_crosswalk_gap remains true; verified_anchor not claimed."
    )
    return {
        "entry_id": "ENTRY_13",
        "canonical_ref": "Ps.5.2",
        "satellite_ref": sat,
        "source_id": sat,
        "corpus_type": "dss",
        "link_type": "lexical",
        "confidence": None,
        "artifact_path": "reports/shadow_4q_ps5_witness_registry_v1_latest.json",
        "state_candidate_id": 11,
        "rationale": "B-Track DSS shadow rail: 4Q98b commander-verified witness. A-Track state 11 bench Ps.5.2 — non-gating.",
        "note": note,
    }


def _diff_fields(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    fields = [
        "canonical_ref",
        "satellite_ref",
        "source_id",
        "corpus_type",
        "link_type",
        "artifact_path",
        "rationale",
        "note",
    ]
    out: list[dict[str, Any]] = []
    for f in fields:
        b, a = before.get(f), after.get(f)
        if b != a:
            out.append({"field": f, "before": b, "after": a})
    return out


def build() -> dict[str, Any]:
    cross = _load(CROSS_REF)
    evidence = _load(EVIDENCE)
    relabel = _load(RELABEL)
    intake_rows = (evidence.get("manual_intake") or {}).get("witness_promotions") or []
    e13_intake = next((r for r in intake_rows if r.get("entry_id") == "ENTRY_13"), {})

    before_12 = _find_entry(cross, "ENTRY_12") or {}
    before_13 = _find_entry(cross, "ENTRY_13") or {}
    after_12 = _proposed_entry_12()
    after_13 = _proposed_entry_13(relabel, e13_intake)

    entries = [
        {
            "entry_id": "ENTRY_12",
            "before": {k: before_12.get(k) for k in after_12},
            "after": after_12,
            "diff": _diff_fields(before_12, after_12),
            "verified_anchor_claimed": False,
        },
        {
            "entry_id": "ENTRY_13",
            "before": {k: before_13.get(k) for k in after_13},
            "after": after_13,
            "diff": _diff_fields(before_13, after_13),
            "verified_anchor_claimed": False,
            "shadow_verse_anchor": relabel.get("shadow_verse_anchor"),
        },
    ]

    return {
        "schema": "cross_ref_entry_12_13_apply_diff_preview_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "draft_path": str(CROSS_REF.relative_to(ROOT)),
        "draft_mutated": False,
        "awaiting": "commander_approval_for_hg-05",
        "track_wall": {
            "canon_31k_41k_merge": False,
            "track_a_bridge": False,
            "verified_anchor_not_claimed": True,
        },
        "entries": entries,
        "approval_prompt": "Approve hg-05 apply of satellite_ref/source_id/note for ENTRY_12 and ENTRY_13 only.",
        "reproduce": "py scripts/build_cross_ref_entry_12_13_apply_diff_preview_v1.py",
        "next_step": "py scripts/apply_cross_ref_entry_12_13_patch_v1.py --dry-run (hg-05)",
    }


def _md(doc: dict[str, Any]) -> str:
    lines = [
        "# CROSS_REF ENTRY_12/13 — Apply Diff Preview (승인 대기)",
        "",
        f"- 생성: {doc.get('generated_at_utc')}",
        f"- Draft: `{doc.get('draft_path')}` — **미변경**",
        f"- 승인 후: hg-05 apply",
        "",
        "## 격벽",
        "",
        "- canonical_ref **Ps.4.6 / Ps.5.2 유지** (A-track bench 라벨)",
        "- **verified_anchor 미주장** — ENTRY_13은 `commander_verified_shadow_witness`만",
        "- canon 31k/41k · Track A 합입 없음",
        "",
    ]
    for ent in doc.get("entries") or []:
        eid = ent.get("entry_id")
        lines.extend([f"## {eid}", ""])
        if ent.get("shadow_verse_anchor"):
            lines.append(f"- shadow_verse_anchor: **{ent['shadow_verse_anchor']}**")
            lines.append("")
        for d in ent.get("diff") or []:
            lines.append(f"### `{d['field']}`")
            lines.append("")
            lines.append("**Before:**")
            lines.append("")
            lines.append(f"> {d.get('before')}")
            lines.append("")
            lines.append("**After (proposed):**")
            lines.append("")
            lines.append(f"> {d.get('after')}")
            lines.append("")
    lines.extend(
        [
            "## 지휘관 승인",
            "",
            "승인 문구 예: 「**5번 진행**」 또는 「ENTRY_12/13 diff 승인」",
            "",
            "## 재현",
            "",
            "```powershell",
            "py scripts/build_cross_ref_entry_12_13_apply_diff_preview_v1.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json-out", type=Path, default=OUT_JSON)
    ap.add_argument("--md-out", type=Path, default=OUT_MD)
    args = ap.parse_args()
    if not CROSS_REF.is_file():
        print(json.dumps({"ok": False, "reason": "cross_ref_draft_missing"}, ensure_ascii=False))
        return 1
    doc = build()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md_out.write_text(_md(doc), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "entries": len(doc["entries"]),
                "diff_fields": sum(len(e.get("diff") or []) for e in doc["entries"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
