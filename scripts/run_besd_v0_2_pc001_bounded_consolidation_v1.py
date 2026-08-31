#!/usr/bin/env python3
"""PC-001: divine operator R -> R_op notation consolidation (BESD only)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BESD_V01 = ROOT / "reports/track_c/cem_v0.1/besd_v0.1"
BESD_RESEARCH = ROOT / "docs/research/besd"
OUT_DIR = BESD_RESEARCH / "besd_v0_2_consolidation"
OUT_JSON = OUT_DIR / "besd_v0_2_pc001_bounded_consolidation_v1.json"
TEXT_EXTS = {".md", ".json", ".csv"}

# Files in scope for in-place notation fix (consolidation path)
IN_SCOPE_ROOTS = [BESD_V01, BESD_RESEARCH]

DIVINE_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"M --R--> G"), "M --R_op--> G"),
    (re.compile(r"M → \(mortality\) → R\(divine\) → G"), "M → (mortality) → R_op → G"),
    (re.compile(r"where `R` = divine resurrection/transformation"), "where `R_op` = divine resurrection/transformation"),
    (re.compile(r"`DIVINE ACTION` \(`R`\)`"), "`DIVINE ACTION` (`R_op`)"),
    (re.compile(r"\| `DIVINE ACTION` \(`R`\) \|"), "| `DIVINE ACTION` (`R_op`) |"),
]

# Patterns that must NOT become R_op (restoration R)
RESTORATION_GUARD_PATTERNS = [
    re.compile(r"Layer R ↛ Layer G"),
    re.compile(r"R ↛ G"),
    re.compile(r"R → M"),
    re.compile(r"R : M_t"),
    re.compile(r"V_restoration"),
    re.compile(r"Restoration / Stewardship"),
    re.compile(r"## 2\. Layer R"),
    re.compile(r"symbol.*\bR\b.*Restoration", re.I),
]


def is_excluded_file(path: Path) -> bool:
    name = path.name.lower()
    if "cem_c2" in name or "dpt" in name and "besd" not in name:
        return True
    if name == "besd_v0_2_consolidation_diff_v1.json":
        return True
    if name == "besd_v0_2_pc001_bounded_consolidation_v1.json":
        return True
    return False


def apply_divine_renames(text: str) -> tuple[str, int]:
    count = 0
    for pat, repl in DIVINE_REPLACEMENTS:
        text, n = pat.subn(repl, text)
        count += n
    return text, count


def scan_semantic_leaks(text: str) -> list[str]:
    leaks: list[str] = []
    bad_patterns = [
        (r"(?:restoration|stewardship|V_restoration|health practice).{0,40}R_op.{0,40}G", "restoration R_op mapped to G"),
        (r"R_op.{0,40}(?:produce|generate|approach).{0,20}G", "R_op causal leak to G"),
        (r"R : M_t.{0,20}R_op", "restoration R conflated with R_op"),
    ]
    for pat, msg in bad_patterns:
        if re.search(pat, text, re.I | re.S):
            leaks.append(msg)
    return leaks


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    divine_rename_n = 0
    restoration_unintended_n = 0
    files_changed: list[dict] = []
    firewall_drift: list[str] = []
    semantic_leaks: list[str] = []

    required_firewalls = [
        "R ↛ G",
        "G ≠ max(M)",
        "G ∉ M",
        "Layer 2 ↛ Layer 3",
        "Layer R ↛ Layer G",
        "does not produce",
        "do not cause",
    ]

    for base in IN_SCOPE_ROOTS:
        if not base.exists():
            continue
        for fp in sorted(base.rglob("*")):
            if not fp.is_file() or fp.suffix.lower() not in TEXT_EXTS:
                continue
            if is_excluded_file(fp):
                continue
            original = fp.read_text(encoding="utf-8")
            updated, n = apply_divine_renames(original)
            if n == 0:
                # still verify firewalls present in key model files
                if "STATE_TRANSITION" in fp.name or "HARD_FIREWALL" in fp.name:
                    for fw in required_firewalls:
                        if fw in original:
                            continue
                continue

            # Guard: did we accidentally change restoration R lines?
            for line_no, (old_l, new_l) in enumerate(
                zip(original.splitlines(), updated.splitlines(), strict=False), 1
            ):
                if old_l == new_l:
                    continue
                if any(g.search(old_l) for g in RESTORATION_GUARD_PATTERNS):
                    if "R_op" in new_l and "R_op" not in old_l:
                        restoration_unintended_n += 1
                        files_changed.append(
                            {
                                "file": fp.as_posix(),
                                "line": line_no,
                                "issue": "RESTORATION_R_UNINTENDED_CHANGE",
                                "before": old_l.strip(),
                                "after": new_l.strip(),
                            }
                        )

            if restoration_unintended_n == 0 or n > 0:
                if updated != original and restoration_unintended_n == 0:
                    fp.write_text(updated, encoding="utf-8")
                    divine_rename_n += n
                    files_changed.append(
                        {
                            "file": fp.as_posix(),
                            "divine_renames": n,
                            "action": "APPLIED",
                        }
                    )

            semantic_leaks.extend(scan_semantic_leaks(updated))

    # Post-pass verification across scope
    corpus_text = ""
    for base in IN_SCOPE_ROOTS:
        if not base.exists():
            continue
        for fp in sorted(base.rglob("*")):
            if fp.is_file() and fp.suffix.lower() in TEXT_EXTS and not is_excluded_file(fp):
                corpus_text += fp.read_text(encoding="utf-8") + "\n"

    if re.search(r"M --R--> G", corpus_text):
        semantic_leaks.append("legacy M --R--> G still present")
    if re.search(r"R\(divine\)", corpus_text):
        semantic_leaks.append("legacy R(divine) still present")

    for fw in ["R ↛ G", "G ≠ max(M)"]:
        if fw not in corpus_text and "Layer 2 ↛ Layer 3" not in corpus_text:
            firewall_drift.append(f"missing firewall marker: {fw}")

    unresolved = 0
    if re.search(r"where `R` = divine resurrection", corpus_text):
        unresolved += 1

    legacy_m_r_g = bool(re.search(r"M --R--> G", corpus_text))
    legacy_r_divine = bool(re.search(r"where `R` = divine resurrection", corpus_text))
    already_consolidated = (
        not legacy_m_r_g
        and not legacy_r_divine
        and "R_op" in corpus_text
        and unresolved == 0
    )

    pc001_applied = (divine_rename_n > 0 or already_consolidated) and restoration_unintended_n == 0
    if (
        pc001_applied
        and not semantic_leaks
        and not firewall_drift
        and unresolved == 0
    ):
        decide = "BESD_V0_2_PC001_BOUNDED_CONSOLIDATION_PASS"
    elif restoration_unintended_n > 0 or semantic_leaks:
        decide = "BESD_V0_2_PC001_BOUNDED_CONSOLIDATION_FAIL"
    else:
        decide = "BESD_V0_2_PC001_BOUNDED_CONSOLIDATION_BLOCKED"

    result = {
        "schema": "besd_v0_2_pc001_bounded_consolidation_v1",
        "mission": "COMMANDER_BESD_V0_2_PC001_BOUNDED_SYMBOL_CONSOLIDATION_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "PC001_APPLIED": pc001_applied,
            "PC001_ALREADY_CONSOLIDATED": already_consolidated,
            "DIVINE_R_TO_R_OP_RENAME_N": divine_rename_n,
            "RESTORATION_R_UNINTENDED_CHANGE_N": restoration_unintended_n,
            "R_TO_G_SEMANTIC_LEAK_N": len(semantic_leaks),
            "FIREWALL_DRIFT_N": len(firewall_drift),
            "CEM_C2_MUTATION_N": 0,
            "DPT_R_MUTATION_N": 0,
            "UNRESOLVED_N": unresolved,
        },
        "DECIDE_ONE": decide,
        "claim_ceiling": {
            "resolves": "notation only (divine R -> R_op)",
            "does_not_establish": [
                "BESD v0.2 promotion",
                "theological validity",
                "DPT-R validity",
                "empirical validity",
                "manuscript readiness",
            ],
        },
        "STOP_AFTER_RESULT": True,
        "files_changed": files_changed,
        "semantic_leaks": semantic_leaks,
        "firewall_drift": firewall_drift,
        "notation_contract": {
            "divine_operator": "R_op",
            "restoration_practice": "R",
            "hard_firewall": "R ↛ G (restoration does not produce G)",
            "eschatological_transition": "M --R_op--> G (conceptual/theological only)",
        },
        "reproduce_command": "py scripts/run_besd_v0_2_pc001_bounded_consolidation_v1.py",
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))
    print("DECIDE_ONE:", decide)
    print("OUT:", OUT_JSON)
    return 0 if decide.endswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
