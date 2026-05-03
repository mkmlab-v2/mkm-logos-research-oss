#!/usr/bin/env python3
"""Create daily evolution suggestions from consistency report (research-only)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORT = ART / "vibe_prompt_consistency_report_latest.json"
OUT_JSON = ART / "vibe_evolution_suggestions_latest.json"
OUT_MD = ART / "vibe_evolution_suggestions_latest.md"


def main() -> int:
    if not REPORT.is_file():
        raise FileNotFoundError(f"missing report: {REPORT}")

    rep = json.loads(REPORT.read_text(encoding="utf-8"))
    prompt_reports: list[dict[str, Any]] = rep.get("prompt_reports", [])

    suggestions: list[dict[str, Any]] = []
    for p in prompt_reports:
        pid = p.get("prompt_id")
        ratio = float(p.get("decision_consistency_ratio", 0.0))
        dominant = p.get("dominant_decision")
        if ratio >= 0.9:
            action = "keep"
            note = "Stable prompt. Keep current wording."
            priority = "low"
        elif ratio >= 0.7:
            action = "tighten_output_schema"
            note = "Moderate stability. Enforce stricter output schema and shorter rationale."
            priority = "medium"
        else:
            action = "rewrite_prompt_and_add_constraints"
            note = "Low stability. Rewrite prompt with deterministic fields and conservative fallback."
            priority = "high"
        suggestions.append(
            {
                "prompt_id": pid,
                "current_ratio": ratio,
                "dominant_decision": dominant,
                "recommended_action": action,
                "priority": priority,
                "note": note,
                "requires_human_approval": True,
            }
        )

    out = {
        "schema": "vibe_evolution_suggestions_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "research_only",
        "guardrail": "no_auto_apply_changes_without_human_approval",
        "source_report": str(REPORT).replace("\\", "/"),
        "suggestions": suggestions,
    }
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Vibe Evolution Suggestions (Latest)",
        "",
        f"- Generated (UTC): {out['generated_at_utc']}",
        "- Scope: research_only",
        "- Guardrail: no auto apply",
        "",
        "## Suggestions",
    ]
    for s in suggestions:
        lines.append(
            f"- {s['prompt_id']}: ratio={s['current_ratio']}, action={s['recommended_action']}, "
            f"priority={s['priority']}, approval_required={s['requires_human_approval']}"
        )
    lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"written: {OUT_JSON}")
    print(f"written: {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

