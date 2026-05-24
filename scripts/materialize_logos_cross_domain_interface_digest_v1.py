#!/usr/bin/env python3
"""CDIM latest JSON → operator digest Markdown (deterministic, no LLM)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs" / "final" / "artifacts" / "logos_cross_domain_interface_latest.json"
DEFAULT_OUT = ROOT / "reports" / "logos_cross_domain_interface_digest_latest.md"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def build_markdown(doc: dict[str, Any], *, input_rel: str) -> str:
    lines: list[str] = []
    lines.append("# Logos CDIM — 크로스 도메인 인터페이스 digest")
    lines.append("")
    lines.append("**[HYPO] · research_only · [NON_GATING]** — 성경 코퍼스 오행 이식 없음.")
    lines.append("")
    lines.append(f"- **입력:** `{input_rel}`")
    lines.append(f"- **ts_utc:** `{doc.get('ts_utc')}`")
    lines.append(f"- **field_regime_id:** `{doc.get('field_regime_id')}`")
    lines.append(f"- **no_verse_level_ohaeng_ingest:** `{doc.get('no_verse_level_ohaeng_ingest')}`")
    lines.append("")
    lines.append("## 렌즈 스냅샷 (독립 산출)")
    lines.append("")
    lines.append("| lens | sign | score | conf | path |")
    lines.append("|------|------|-------|------|------|")
    for row in doc.get("lens_snapshots") or []:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"| {row.get('lens_id')} | {row.get('direction_sign')} | "
            f"{row.get('direction_score')} | {row.get('confidence')} | "
            f"`{row.get('artifact_path')}` |"
        )
    lines.append("")
    lines.append("## cross_refs (typed)")
    lines.append("")
    for ref in doc.get("cross_refs") or []:
        if not isinstance(ref, dict):
            continue
        vids = ref.get("verse_ids") or []
        vid_note = f" · verses={len(vids)}" if vids else ""
        lines.append(
            f"- **{ref.get('relation_type')}** {ref.get('from_domain')}→{ref.get('to_domain')} "
            f"`{ref.get('evidence_path')}`{vid_note}"
        )
        if ref.get("note"):
            lines.append(f"  - {ref['note']}")
    lines.append("")
    csum = doc.get("conflict_summary") if isinstance(doc.get("conflict_summary"), dict) else {}
    if csum:
        lines.append("## conflict_summary (fusion_stub verbatim)")
        lines.append("")
        nar = csum.get("conflict_narrative_guarded")
        if nar:
            lines.append(str(nar))
            lines.append("")
        minority = csum.get("minority_lens_ids")
        if minority:
            lines.append(f"- **minority_lens_ids:** `{minority}`")
    lines.append("")
    lines.append("## 금지 주장 (고정)")
    lines.append("")
    for claim in doc.get("forbidden_claims") or []:
        lines.append(f"- `{claim}`")
    lines.append("")
    lines.append("## MS 방어선")
    lines.append("")
    lines.append("- Oracle era **text_blind 4.3%** only — CDIM은 hit%·예언 승격 근거 **아님**.")
    lines.append(f"- 설계: `{doc.get('design_doc')}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = _read_json(args.input)
    if not doc:
        raise SystemExit(f"missing CDIM json: {args.input}")
    try:
        input_rel = args.input.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        input_rel = str(args.input)
    md = build_markdown(doc, input_rel=input_rel)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(md, encoding="utf-8")
    try:
        out_rel = args.output.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        out_rel = str(args.output)
    print(json.dumps({"ok": True, "input": input_rel, "output": out_rel}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
