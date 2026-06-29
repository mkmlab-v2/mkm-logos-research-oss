#!/usr/bin/env python3
"""Apply verifier-promoted MASTER_SUMMARY claims into gwangmyeong B2B static hub (Track B)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY = ROOT / "docs/final/artifacts/logos_b2b_proposal_master_summary_v1_latest.json"
DEFAULT_HUB = ROOT / "reports/gwangmyeong_baekje_b2b_static_hub_draft_v1.md"
DEFAULT_OUT = ROOT / "reports/gwangmyeong_baekje_b2b_static_hub_draft_v1.md"
MARKER_START = "<!-- logos_b2b_master_summary_v1 -->"
MARKER_END = "<!-- /logos_b2b_master_summary_v1 -->"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def _build_block(summary: dict[str, Any], *, generated_at: str) -> str:
    lines = [
        MARKER_START,
        "",
        "## Logos 검증 논리 블록 (MASTER_SUMMARY · Track B)",
        "",
        f"> `{generated_at}` · `[HYPO]` · `NON_GATING` · `SEND_GATE: HOLD` · 외부 송출·Track A 승격 아님",
        "",
        "지휘관 검토 전 자동 주입 — `run_logos_b2b_proposal_evolution_loop_v1.py` goal verifier 통과분만.",
        "",
    ]
    for claim in summary.get("promoted_claims") or []:
        if not isinstance(claim, dict):
            continue
        cid = claim.get("claim_id", "CLAIM")
        body = str(claim.get("body_ko") or "").strip()
        refs = claim.get("clause_refs") or []
        lines.append(f"- **{cid}:** {body}")
        if refs:
            lines.append(f"  - clause_refs: `{', '.join(refs)}`")
    lines.append("")
    transplant = summary.get("logos_structure_transplant") or {}
    if transplant:
        lines.append(
            f"- **logic_transplant:** `{transplant.get('pattern_id')}` "
            f"(pedagogical_only={transplant.get('pedagogical_only')})"
        )
        lines.append("")
    lines.append(MARKER_END)
    lines.append("")
    return "\n".join(lines)


def apply_hub(*, hub_md: str, block: str) -> str:
    pattern = re.compile(
        re.escape(MARKER_START) + r"[\s\S]*?" + re.escape(MARKER_END) + r"\n?",
        re.MULTILINE,
    )
    if pattern.search(hub_md):
        return pattern.sub(block, hub_md, count=1)
    # Insert before ## 격벽 감사 if present, else append
    anchor = "## 격벽 감사"
    idx = hub_md.find(anchor)
    if idx >= 0:
        return hub_md[:idx] + block + hub_md[idx:]
    return hub_md.rstrip() + "\n\n" + block


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--hub-in", type=Path, default=DEFAULT_HUB)
    ap.add_argument("--hub-out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    summary = _load(args.summary)
    if not summary:
        raise SystemExit(f"missing summary: {args.summary}")
    if summary.get("promoted") is not True:
        raise SystemExit("MASTER_SUMMARY not promoted — run evolution loop first")

    hub_path = args.hub_in
    if not hub_path.is_file():
        raise SystemExit(f"missing hub: {hub_path}")

    generated_at = _utc()
    block = _build_block(summary, generated_at=generated_at)
    hub_md = hub_path.read_text(encoding="utf-8")
    out_md = apply_hub(hub_md=hub_md, block=block)

    # Refresh status line timestamp if present
    out_md = re.sub(
        r"(\*\*updated:\*\* )\d{4}-\d{2}-\d{2}T[\d:Z]+",
        rf"\g<1>{generated_at}",
        out_md,
        count=1,
    )

    args.hub_out.parent.mkdir(parents=True, exist_ok=True)
    args.hub_out.write_text(out_md, encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "promoted_claims": summary.get("promoted_claim_count"),
                "out": str(args.hub_out.relative_to(ROOT)).replace("\\", "/"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
