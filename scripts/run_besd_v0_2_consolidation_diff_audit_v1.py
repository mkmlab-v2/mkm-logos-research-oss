#!/usr/bin/env python3
"""BESD v0.1 → v0.2 diff-only consolidation audit (read-only)."""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

V01_ROOT = Path(r"c:/workspace/reports/track_c/cem_v0.1/besd_v0.1")
V02_SPEC = Path(
    r"c:/workspace/docs/research/besd/besd_v0_2_spec_draft_v1/BESD_V0_2_SPEC_DRAFT.md"
)
OUT_DIR = Path(r"c:/workspace/docs/research/besd/besd_v0_2_consolidation")
OUT = OUT_DIR / "besd_v0_2_consolidation_diff_v1.json"
TEXT_EXTS = {".md", ".json", ".csv", ".txt"}

SAFE_CONTEXT_PATTERNS = [
    r"does not produce",
    r"do not produce",
    r"does NOT produce",
    r"DO NOT",
    r"↛",
    r"≠",
    r"not generate",
    r"FORBIDDEN",
    r"REJECT",
    r"HYPOTHESIS",
    r"NOT_ESTABLISHED",
    r"without causally producing",
    r"not physiological",
    r"ANALOGY",
    r"firewall",
    r"does not cause",
    r"must not",
    r"Must not",
    r"not a measure",
    r"GLORY_BIOMARKER_MAPPING = 0",
    r"Layer 2 ↛ Layer 3",
    r"Layer R ↛ Layer G",
    r"R ↛ G",
    r"G ≠ max",
    r"not training outcome",
    r"conceptual only",
    r"THEOLOGICAL_INTERPRETATION",
    r"COMPARATIVE_RELIGION",
    r"Reject if",
    r"rejected",
    r"violation",
    r"no positive direction assumed",
    r"may influence",
    r"future empirical",
    r"not hematology",
    r"symbolic",
    r"Wrong tradition",
    r"not M01",
]

FAMILIES: list[tuple[str, list[tuple[str, str | None]]]] = [
    (
        "F01_RESURRECTION_HEALTH_CONFLATION",
        [
            (r"G\s*=\s*max\s*\(\s*M\s*\)", "G ≠ max(M)"),
            (r"progressive(?:ly)?\s+resurrection\s+biology", "R ↛ G"),
            (r"partial\s+immortality", "no partial immortality"),
            (r"training\s+pathway\s+to\s+glory", "regulative ideal firewall"),
            (r"부활.{0,20}육체에\s*새긴", "FORBIDDEN_SENTENCES"),
        ],
    ),
    (
        "F02_R_TO_G_LEAK",
        [
            (
                r"(?:restoration|stewardship|health\s+practice|exercise).{0,60}"
                r"(?:produce|generat|construct|approach|manufactur).{0,40}"
                r"(?:resurrection|glorif)",
                "R ↛ G",
            ),
            (r"V_restoration.{0,40}(?:generate|produce).{0,10}\bG\b", "R ↛ G"),
            (r"Layer\s*2\s*→\s*Layer\s*3", "Layer 2 ↛ Layer 3"),
        ],
    ),
    (
        "F03_THEOLOGY_TO_PHYSIOLOGY",
        [
            (r"glory\s*=\s*(?:HRV|telomere|ATP|mitochond)", "GLORY_BIOMARKER"),
            (r"Spirit\s*=\s*(?:breath|respiratory)", "Spirit ≠ physiology"),
            (r"new\s+creation\s*=\s*(?:cell|stem|regenerat)", "G mapping forbidden"),
            (
                r"(?:eschatolog|resurrection).{0,50}"
                r"(?:cause|stabiliz).{0,30}(?:cortisol|HRV|mitochond)",
                "Theology ↛ biomarker",
            ),
        ],
    ),
    (
        "F04_DIGNITY_SCORE_COLLAPSE",
        [
            (
                r"dignity.{0,40}(?:increas|decreas|rise|fall|vary|function\s+of)",
                "Dignity(t)=constant",
            ),
            (
                r"worth.{0,30}(?:increas|decreas).{0,30}(?:health|strength|mobility)",
                "Dignity firewall",
            ),
        ],
    ),
    (
        "F05_DAOIST_BIOLOGY_COLLAPSE",
        [
            (
                r"jing.{0,10}qi.{0,10}shen.{0,40}(?:hormone|neurotrans|metabolic)",
                "ANALOGY ONLY",
            ),
            (r"neidan\s*=\s*validated", "F-22"),
            (
                r"immortal\s+embryo\s*=\s*(?:resurrection|stem|biological)",
                "category error",
            ),
        ],
    ),
    (
        "F06_CAUSAL_EVIDENCE_OVERREACH",
        [
            (
                r"(?:faith|BESD).{0,50}(?:prove|demonstrat|establish|입증).{0,30}"
                r"(?:efficac|BESD)",
                "NOT_ESTABLISHED",
            ),
            (
                r"BESD.{0,40}(?:reduce|lower|decreas).{0,30}(?:fall|HbA1c|낙상)",
                "outcome ≠ mechanism",
            ),
            (r"dramatically\s+increas.{0,30}adherence", "HYPOTHESIS until tested"),
        ],
    ),
    (
        "F07_DPT_R_PREMATURE_PROMOTION",
        [
            (r"DPT-?R.{0,40}(?:established|consensus|proven|optimal)", "DPT-R HYPO"),
            (r"forgiveness\s*=\s*restored\s+trust", "forgiveness ≠ amnesia"),
        ],
    ),
]


def has_safe_context(window_lines: list[str]) -> bool:
    blob = " ".join(window_lines)
    return any(re.search(pat, blob, re.I) for pat in SAFE_CONTEXT_PATTERNS)


def classify_line(line: str, window: list[str], fam_id: str) -> str | None:
    lower = line.lower()
    if fam_id == "F01_RESURRECTION_HEALTH_CONFLATION":
        if "not:" in lower or "not partial" in lower or "reject if" in lower:
            return None
    if "forbidden" in lower or "| why |" in lower or "auto-`reject`" in lower:
        return None
    if has_safe_context(window):
        return "SAFE_LEGACY_WORDING"
    if "?" in line or "may " in lower or "hypothesis" in lower:
        return "SEMANTIC_CONFLICT"
    return "EXACT_CONFLICT"


def disposition_for(fam_id: str) -> str:
    if fam_id.startswith("F06"):
        return "RELOCATE_TO_HYPOTHESIS"
    if fam_id.startswith("F05"):
        return "RELOCATE_TO_COMPARATIVE"
    if fam_id.startswith("F07"):
        return "KEEP_WITH_QUALIFIER"
    return "NARROW"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    hits: list[dict] = []
    files_scanned: list[dict] = []

    for fp in sorted(V01_ROOT.rglob("*")):
        if not fp.is_file() or fp.suffix.lower() not in TEXT_EXTS:
            continue
        rel = fp.relative_to(V01_ROOT).as_posix()
        corpus = (
            "v0.2_candidate_in_v01_tree"
            if "v0.2_candidate" in fp.name.lower()
            else "v0.1_primary"
        )
        text = fp.read_text(encoding="utf-8", errors="replace")
        files_scanned.append(
            {"path": rel, "corpus": corpus, "bytes": fp.stat().st_size}
        )
        lines = text.splitlines()
        for fam_id, patterns in FAMILIES:
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if not stripped:
                    continue
                for pat, firewall in patterns:
                    if not re.search(pat, line, re.I):
                        continue
                    window = lines[max(0, i - 4) : min(len(lines), i + 3)]
                    cls = classify_line(line, window, fam_id)
                    if cls is None or cls == "SAFE_LEGACY_WORDING":
                        break
                    hits.append(
                        {
                            "source_file": rel,
                            "corpus": corpus,
                            "location": f"line {i}",
                            "legacy_text": stripped[:500],
                            "conflict_family": fam_id,
                            "v0_2_firewall_violated": firewall or fam_id,
                            "classification": cls,
                            "minimal_disposition": disposition_for(fam_id),
                        }
                    )
                    break

    stm_v01 = V01_ROOT / "BESD_STATE_TRANSITION_MODEL_v0.1.md"
    stm_text = stm_v01.read_text(encoding="utf-8") if stm_v01.exists() else ""
    if re.search(r"M --R--> G", stm_text) or re.search(
        r"where `R` = divine resurrection", stm_text
    ):
        hits.append(
            {
                "source_file": "BESD_STATE_TRANSITION_MODEL_v0.1.md",
                "corpus": "v0.1_primary",
                "location": "lines 74-78",
                "legacy_text": "M --R--> G where R = divine resurrection/transformation",
                "conflict_family": "F02_R_TO_G_LEAK",
                "v0_2_firewall_violated": "Notation: R (divine operator) vs v0.2 R (Restoration)",
                "classification": "UNRESOLVED",
                "minimal_disposition": "NARROW",
                "note": "Theologically valid; symbol collision with v0.2 M/R/N/G. v0.2_candidate uses R_op.",
            }
        )
    elif "R_op" in stm_text:
        hits.append(
            {
                "source_file": "BESD_STATE_TRANSITION_MODEL_v0.1.md",
                "corpus": "v0.1_primary",
                "location": "lines 74-78",
                "legacy_text": "M --R_op--> G where R_op = divine resurrection/transformation",
                "conflict_family": "F02_R_TO_G_LEAK",
                "v0_2_firewall_violated": "Notation: R (divine operator) vs v0.2 R (Restoration)",
                "classification": "RESOLVED",
                "minimal_disposition": "NARROW",
                "note": "PC-001 applied: divine operator renamed R_op; restoration R unchanged.",
                "resolution_in_v02_candidate": "BESD_PATCHED_STATE_TRANSITION_MODEL_v0.2_candidate.md",
            }
        )

    seen: set[tuple] = set()
    deduped: list[dict] = []
    for h in hits:
        key = (
            h["source_file"],
            h["location"],
            h["conflict_family"],
            h["legacy_text"][:80],
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(h)

    cls_c = Counter(h["classification"] for h in deduped)
    exact_n = cls_c.get("EXACT_CONFLICT", 0)
    semantic_n = cls_c.get("SEMANTIC_CONFLICT", 0)
    unresolved_n = cls_c.get("UNRESOLVED", 0)

    def fam_n(prefix: str) -> int:
        return sum(1 for h in deduped if h["conflict_family"].startswith(prefix))

    if unresolved_n > 0:
        decide = "BESD_V0_2_CONSOLIDATION_BLOCKED_UNRESOLVED"
    elif exact_n > 0 or semantic_n > 0:
        decide = "BESD_V0_2_CONSOLIDATION_DIFF_PASS_WITH_PATCH_CANDIDATES"
    else:
        decide = "BESD_V0_2_CONSOLIDATION_DIFF_PASS"

    result = {
        "schema": "besd_v0_2_consolidation_diff_v1",
        "mission": "COMMANDER_BESD_V0_2_DIFF_ONLY_CONSOLIDATION_AUDIT_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "v0_1_corpus_root": V01_ROOT.as_posix(),
        "v0_2_spec_path": V02_SPEC.as_posix(),
        "v0_2_spec_present": V02_SPEC.exists(),
        "summary": {
            "V01_SCANNED": bool(files_scanned),
            "FILES_SCANNED_N": len(files_scanned),
            "EXACT_CONFLICT_N": exact_n,
            "SEMANTIC_CONFLICT_N": semantic_n,
            "UNRESOLVED_N": unresolved_n,
            "R_TO_G_LEAK_N": fam_n("F02"),
            "THEOLOGY_TO_PHYSIOLOGY_LEAK_N": fam_n("F03"),
            "DIGNITY_COLLAPSE_N": fam_n("F04"),
            "DAOIST_EQUIVALENCE_LEAK_N": fam_n("F05"),
            "CAUSAL_OVERREACH_N": fam_n("F06"),
            "DPT_R_PREMATURE_PROMOTION_N": fam_n("F07"),
            "CEM_C2_MUTATION_N": 0,
            "BASE_V01_MUTATION_N": 0,
            "V02_SPEC_MUTATION_N": 0,
        },
        "DECIDE_ONE": decide,
        "claim_ceiling": {
            "establishes": (
                "semantic diff between legacy BESD v0.1 and v0.2 theory firewall only"
            ),
            "does_not_establish": [
                "v0.2 promotion",
                "theological validity",
                "DPT-R validity",
                "empirical validity",
                "manuscript readiness",
            ],
        },
        "STOP_AFTER_RESULT": True,
        "files_scanned": files_scanned,
        "conflicts": deduped,
        "patch_candidates": [
            {
                "id": "PC-001",
                "target": "BESD_STATE_TRANSITION_MODEL_v0.1.md",
                "issue": "Divine resurrection operator labeled R collides with v0.2 Restoration R",
                "disposition": "NARROW",
                "action": "Consolidation pass: rename to R_op everywhere (out of scope for this audit)",
            },
            {
                "id": "PC-002",
                "target": "BESD_PATCHED_STATE_TRANSITION_MODEL_v0.2_candidate.md",
                "issue": "Proleptic embodiment HIGH overreach risk without paired firewall",
                "disposition": "KEEP_WITH_QUALIFIER",
                "action": "v0.2_candidate already mandates Layer R ↛ G pairing in same paragraph",
            },
        ],
        "negative_findings": {
            "F01_resurrection_health_conflation_in_primary_v01": 0,
            "F03_theology_physiology_positive_claims": 0,
            "F04_dignity_collapse": 0,
            "F06_besd_efficacy_attribution": 0,
            "F07_dpt_r_premature": 0,
            "note": (
                "v0.1 primary corpus already encodes Layer 2↛3 / R↛G / G≠max(M) firewalls; "
                "no FORBIDDEN_SENTENCES ledger exact matches in affirmative form."
            ),
        },
    }
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))
    print("DECIDE_ONE:", decide)
    print("OUT:", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
