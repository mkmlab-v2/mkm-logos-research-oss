#!/usr/bin/env python3
"""[HYPO] Commander picklist from LUT nim_anchor_staging + de_probe (no codec wire)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LUT = ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_LUT_DRAFT_V1.json"
NIM = ROOT / "reports/ng40_de_probe_nim_synthesis_v1_latest.json"
OUT = ROOT / "reports/nvidia_de_nim_commander_anchor_picklist_v1_latest.json"
OUT_TXT = ROOT / "reports/nvidia_de_nim_commander_anchor_picklist_v1_latest.txt"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    lut = json.loads(LUT.read_text(encoding="utf-8-sig")) if LUT.is_file() else {}
    nim_syn = json.loads(NIM.read_text(encoding="utf-8-sig")) if NIM.is_file() else {}
    staging = lut.get("nim_anchor_staging_v1") or {}
    syn_by_probe: dict[str, dict] = {}
    for item in nim_syn.get("syntheses") or []:
        pid = item.get("probe_id")
        if pid:
            syn_by_probe[str(pid)] = item
    by_probe = staging.get("candidates_by_probe_id") or {}
    global_refs = staging.get("verse_refs_guess") or []
    rows: list[dict] = []
    for probe_id, row in sorted(by_probe.items()):
        syn = syn_by_probe.get(probe_id) or {}
        refs = (
            syn.get("verse_refs_merged")
            or (syn.get("synthesis") or {}).get("verse_refs_guess")
            or row.get("verse_refs_merged")
            or row.get("verse_refs_guess")
            or []
        )
        rows.append(
            {
                "probe_id": probe_id,
                "label_ko": row.get("label_ko"),
                "status": row.get("status"),
                "verse_refs": refs[:8],
                "candidate_anchor_status": row.get("candidate_anchor_status"),
                "recommended_action": "pending_commander_accept_or_reject",
            }
        )
    doc = {
        "schema": "nvidia_de_nim_commander_anchor_picklist_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "gating": "NON_GATING",
        "codec_wired": False,
        "lut_status": lut.get("status"),
        "nim_summary": nim_syn.get("summary"),
        "row_count": len(rows),
        "rows": rows,
        "instruction_ko": "각 행 accept/reject만 지시. 코덱·Track A·실매매 자동 반영 금지.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# DE/NIM 앵커 픽리스트 (지휘관 검토용)",
        f"**갱신:** {doc['generated_at_utc']}",
        "[HYPO] · research_only · NON_GATING",
        "",
        f"LUT `{lut.get('status')}` · NIM ok {nim_syn.get('summary', {}).get('ok')}/{nim_syn.get('summary', {}).get('probes')}",
        "",
    ]
    for i, r in enumerate(rows, 1):
        lines.append(
            f"{i}. **{r.get('label_ko') or r['probe_id']}** (`{r['probe_id']}`) — "
            f"절 후보: {', '.join(r['verse_refs'][:4]) or '—'} · **{r['recommended_action']}**"
        )
    lines.extend(["", "**지시 예:** `probe_id` accept 3건 reject 2건", ""])
    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "rows": len(rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
