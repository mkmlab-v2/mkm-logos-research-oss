# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.50, L:0.55, K:0.78, M:0.38}
# Balance: 84
# Purpose: Prune noisy ijeoma_harvest rows from scm_boming_jiju lexicon (B-track).
"""prune_scm_boming_jiju_ijeoma_harvest_v1 — lexicon hygiene after bulk harvest merge."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.core.harvest_scm_boming_jiju_from_ijeoma_v1 import _is_rejected_phrase
from scripts.core.scm_boming_jiju_lexicon_v1 import DEFAULT_LEXICON_PATH, SCHEMA_ID

PRUNE_REPORT_SCHEMA = "scm_boming_jiju_lexicon_prune_report_v1"


def _should_prune_entry(entry: dict[str, Any], *, min_priority_keep: int = 50) -> tuple[bool, str]:
    role = str(entry.get("pillar_role") or "")
    term = str(entry.get("term") or "")
    src = entry.get("source") if isinstance(entry.get("source"), dict) else {}
    ref = str(src.get("ref") or "")
    priority = int(entry.get("priority") or 0)

    if role != "ijeoma_harvest" and "ijeoma" not in ref:
        return False, ""
    if _is_rejected_phrase(term):
        return True, "title_noise_pattern"
    if priority < min_priority_keep:
        return True, f"priority_below_{min_priority_keep}"
    if len(term) <= 2:
        return True, "hanja_too_short"
    if re.fullmatch(r"[0-9◉·\s]+", term):
        return True, "non_lexical"
    return False, ""


def plan_prune(
    lexicon_path: Path | None = None,
    *,
    min_priority_keep: int = 50,
) -> dict[str, Any]:
    lp = lexicon_path or DEFAULT_LEXICON_PATH
    if not lp.is_file():
        raise FileNotFoundError(lp)
    lex = json.loads(lp.read_text(encoding="utf-8"))
    if lex.get("schema") != SCHEMA_ID or not lex.get("boundary_ack"):
        raise ValueError("invalid lexicon SSOT")

    entries = lex.get("entries") or []
    kept: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        drop, reason = _should_prune_entry(e, min_priority_keep=min_priority_keep)
        row = {**e, "prune_reason": reason}
        if drop:
            removed.append(row)
        else:
            kept.append(e)

    return {
        "schema": PRUNE_REPORT_SCHEMA,
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lexicon_path": str(lp),
        "lexicon_version_before": lex.get("version"),
        "min_priority_keep": min_priority_keep,
        "counts": {
            "before": len(entries),
            "after": len(kept),
            "removed": len(removed),
        },
        "removed_sample": removed[:40],
        "kept_ijoeoma_harvest_count": sum(
            1 for x in kept if str(x.get("pillar_role")) == "ijeoma_harvest"
        ),
        "disclaimer_ko": "[HYPO] prune는 렉시콘 정리만. 임상·처방 의미 변경 없음.",
        "_lexicon_doc": lex,
        "_kept_entries": kept,
    }


def apply_prune(plan: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    lex = plan["_lexicon_doc"]
    kept = plan["_kept_entries"]
    out_plan = {k: v for k, v in plan.items() if not k.startswith("_")}
    if dry_run:
        out_plan["apply"] = {"dry_run": True, "would_write": False}
        return out_plan

    ver = str(lex.get("version") or "1.2.0")
    parts = ver.split(".")
    if len(parts) == 3 and parts[0].isdigit():
        parts[2] = str(int(parts[2]) + 1)
        lex["version"] = ".".join(parts)
    lex["entries"] = kept
    desc = str(lex.get("description") or "")
    if "pruned_ijoeoma_harvest" not in desc:
        lex["description"] = (desc + " pruned_ijoeoma_harvest.").strip()
    lp = Path(plan["lexicon_path"])
    lp.write_text(json.dumps(lex, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_plan["apply"] = {
        "dry_run": False,
        "new_version": lex.get("version"),
        "written": str(lp),
    }
    return out_plan
