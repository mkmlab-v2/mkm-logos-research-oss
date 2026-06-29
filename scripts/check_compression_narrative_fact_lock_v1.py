#!/usr/bin/env python3
"""Compression narrative Fact-Lock lint (plan B 3-layer wording guard; read-only)."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCAN_ROOTS = [
    ROOT / "AGENTS.md",
    ROOT / "CLAUDE.md",
    ROOT / "docs" / "final" / "P0_COMMERCIALIZATION_TRACKER.md",
    ROOT / "docs" / "final" / "COMPRESSION_SLA_POLICY_V1.md",
    ROOT / "docs" / "final" / "COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md",
    ROOT / "docs" / "final" / "artifacts",
]

SKIP_PARTS = (
    "sasang_interpretive_insight_bundle",
    "patient_care_bundle",
    "interpretive",
    "btrack",
    "hypo",
)

FORBIDDEN = [
    (re.compile(r"사상\s*4축.*(엔진|압축).*(제어|구동|지휘)"), "sasang_4axis_controls_codec"),
    (re.compile(r"sasang\s+4\s*axis.*(control|drive)s?\s+(the\s+)?(codec|compression)", re.I), "sasang_4axis_controls_codec_en"),
    (re.compile(r"(Track\s*A|MS).{0,40}사상동역학", re.I | re.S), "sasang_dynamics_in_track_a_ms"),
    (re.compile(r"(Track\s*A|MS).{0,40}우주\s*통일장", re.I | re.S), "toe_in_track_a_ms"),
]


def _iter_files() -> list[Path]:
    out: list[Path] = []
    for entry in SCAN_ROOTS:
        if entry.is_file():
            out.append(entry)
            continue
        if not entry.is_dir():
            continue
        for p in entry.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in {".md", ".json", ".txt"}:
                continue
            rel = p.as_posix().lower()
            if any(s in rel for s in SKIP_PARTS):
                continue
            out.append(p)
    return sorted(set(out))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-json",
        default=str(ROOT / "reports" / "compression_narrative_fact_lock_latest.json"),
    )
    args = parser.parse_args()

    violations: list[dict[str, str]] = []
    scanned = 0
    for path in _iter_files():
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pattern, code in FORBIDDEN:
            if pattern.search(text):
                violations.append(
                    {
                        "file": path.relative_to(ROOT).as_posix(),
                        "code": code,
                    }
                )

    ok = len(violations) == 0
    report = {
        "schema": "compression_narrative_fact_lock_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "policy": "plan_b_frozen_v1",
        "architecture_ssot": {
            "layer_1": "lexicon/shard/inverse_decoder (discrete math)",
            "layer_2": "L1 mode-router pruner (perm_cap, cheap_top_k; not sasang engine)",
            "layer_3": "interpretive codebook (human_only; B-track)",
            "gematria_4d_bridge": "metadata-only; ~-14.3pp saving if injected into codec path",
        },
        "files_scanned": scanned,
        "violation_count": len(violations),
        "ok": ok,
        "violations": violations[:50],
        "note": "No auto-edit. Fix manually or ask agent with file path.",
    }

    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"OK: compression narrative fact-lock" if ok else f"FAIL: {len(violations)} violation(s)")
    print(f"Artifact: {out_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
