#!/usr/bin/env python3
"""Phase P — verse 4D residual + 41k lexicon projection + reclassification audit [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT_DEFAULT = ROOT / "reports/logos_lexicon_4d_research_audit_v1_latest.json"
LEXICON_4D_OUT = ROOT / "reports/logos_lexicon_4d_v1_latest.json"
VERSE_JSONL = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"
AUDIT_OUT = ROOT / "reports/logos_41k_4d_reclassification_audit_v1_latest.json"
RESIDUAL_OUT = ROOT / "reports/logos_4d_exact_match_residual_v1_latest.json"
KEY_SHADOW_OUT = ROOT / "reports/verse_metadata_shadow_v1_latest.json"
KEY_SHADOW_V2_OUT = ROOT / "reports/verse_metadata_shadow_v2_latest.json"
TERM_POSTIT_V2_OUT = ROOT / "reports/term_postit_shadow_v2_latest.json"
ANCHOR_INDEX_OUT = ROOT / "reports/logos_bidirectional_anchor_index_v1_latest.json"
SHADOW_QUALITY_OUT = ROOT / "reports/shadow_postits_quality_gate_v1_latest.json"
SWEEP_OUT = ROOT / "reports/tracka_shadow_sweep_v1_latest.json"
PRESET_OUT = ROOT / "reports/tracka_shadow_default_preset_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, timeout: int = 7200) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-300:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--skip-phase-pa", action="store_true", help="Skip 4D jsonl vs pipeline residual")
    ap.add_argument("--skip-phase-pb", action="store_true", help="Skip verse→lexicon 4D projection")
    ap.add_argument("--skip-shadow-enrich", action="store_true", help="Skip path gate 4D shadow attach")
    ap.add_argument("--max-verse-rows", type=int, default=0, help="0=full corpus for lexicon projection")
    ap.add_argument("--residual-sample", type=int, default=40)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_phase_pa:
        pa_cmd = [
            PY,
            "scripts/audit_logos_4d_exact_match_residual_v1.py",
            "--out-json",
            str(RESIDUAL_OUT),
            "--sample",
            str(max(1, args.residual_sample)),
        ]
        steps.append(_run("phase_pa_4d_residual", pa_cmd, timeout=3600))

    if not args.skip_phase_pb:
        if not VERSE_JSONL.is_file():
            steps.append(
                {
                    "name": "phase_pb_lexicon_project",
                    "ok": False,
                    "error": f"missing verse jsonl: {VERSE_JSONL}",
                }
            )
        else:
            pb_cmd = [
                PY,
                "scripts/project_logos_verse_4d_to_lexicon_v1.py",
                "--verse-jsonl",
                str(VERSE_JSONL),
                "--out-lexicon-4d-json",
                str(LEXICON_4D_OUT),
            ]
            if args.max_verse_rows:
                pb_cmd.extend(["--max-rows", str(args.max_verse_rows)])
            steps.append(_run("phase_pb_lexicon_project", pb_cmd, timeout=3600))

    pc_cmd = [
        PY,
        "scripts/build_logos_41k_4d_reclassification_audit_v1.py",
        "--lexicon-4d",
        str(LEXICON_4D_OUT),
        "--verse-jsonl",
        str(VERSE_JSONL),
        "--out",
        str(AUDIT_OUT),
    ]
    if args.max_verse_rows:
        pc_cmd.extend(["--max-verse-rows", str(args.max_verse_rows)])
    steps.append(_run("phase_pc_reclassification_audit", pc_cmd, timeout=600))

    if not args.skip_shadow_enrich:
        steps.append(
            _run(
                "phase_shadow_enrich_path_gate",
                [PY, "scripts/enrich_logos_path_gate_4d_shadow_v1.py"],
                timeout=120,
            )
        )
    steps.append(
        _run(
            "phase_key_verse_shadow",
            [PY, "scripts/build_logos_key_verses_shadow_v1.py"],
            timeout=600,
        )
    )
    if not args.skip_shadow_enrich:
        steps.append(
            _run(
                "phase_shadow_persona_enrich",
                [PY, "scripts/enrich_logos_path_gate_shadow_persona_v1.py"],
                timeout=120,
            )
        )
    steps.append(_run("phase_term_postit_v2", [PY, "scripts/build_41k_postit_shadow_v2.py"], timeout=600))
    steps.append(_run("phase_verse_shadow_v2", [PY, "scripts/refine_31k_key_verse_shadow_v2.py"], timeout=300))
    steps.append(_run("phase_anchor_index", [PY, "scripts/build_logos_bidirectional_anchor_index_v1.py"], timeout=600))
    steps.append(_run("phase_shadow_quality_gate", [PY, "scripts/validate_shadow_postits_quality_v1.py"], timeout=300))
    steps.append(_run("phase_tracka_shadow_sweep", [PY, "scripts/run_tracka_shadow_sweep_v1.py"], timeout=1800))
    steps.append(_run("phase_tracka_shadow_preset", [PY, "scripts/build_tracka_shadow_default_preset_v1.py"], timeout=1800))

    audit: dict[str, Any] = {}
    if AUDIT_OUT.is_file():
        try:
            audit = json.loads(AUDIT_OUT.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            pass
    key_shadow: dict[str, Any] = {}
    if KEY_SHADOW_OUT.is_file():
        try:
            key_shadow = json.loads(KEY_SHADOW_OUT.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            pass
    key_shadow_v2 = json.loads(KEY_SHADOW_V2_OUT.read_text(encoding="utf-8-sig")) if KEY_SHADOW_V2_OUT.is_file() else {}
    term_postit_v2 = json.loads(TERM_POSTIT_V2_OUT.read_text(encoding="utf-8-sig")) if TERM_POSTIT_V2_OUT.is_file() else {}
    anchor_index = json.loads(ANCHOR_INDEX_OUT.read_text(encoding="utf-8-sig")) if ANCHOR_INDEX_OUT.is_file() else {}
    shadow_quality = json.loads(SHADOW_QUALITY_OUT.read_text(encoding="utf-8-sig")) if SHADOW_QUALITY_OUT.is_file() else {}
    sweep = json.loads(SWEEP_OUT.read_text(encoding="utf-8-sig")) if SWEEP_OUT.is_file() else {}
    preset = json.loads(PRESET_OUT.read_text(encoding="utf-8-sig")) if PRESET_OUT.is_file() else {}

    overall_ok = all(s.get("ok") for s in steps) and audit.get("ok") is True
    doc = {
        "schema": "logos_lexicon_4d_research_audit_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "track_wall": {
            "a_track_auto_promotion": False,
            "track_a_bridge": False,
            "live_trading_trigger": False,
            "ms_headline_merge_forbidden": True,
        },
        "artifacts": {
            "lexicon_4d": str(LEXICON_4D_OUT.relative_to(ROOT)).replace("\\", "/"),
            "audit": str(AUDIT_OUT.relative_to(ROOT)).replace("\\", "/"),
            "residual": str(RESIDUAL_OUT.relative_to(ROOT)).replace("\\", "/"),
            "key_verse_shadow": str(KEY_SHADOW_OUT.relative_to(ROOT)).replace("\\", "/"),
            "key_verse_shadow_v2": str(KEY_SHADOW_V2_OUT.relative_to(ROOT)).replace("\\", "/"),
            "term_postit_v2": str(TERM_POSTIT_V2_OUT.relative_to(ROOT)).replace("\\", "/"),
            "anchor_index": str(ANCHOR_INDEX_OUT.relative_to(ROOT)).replace("\\", "/"),
            "shadow_quality_gate": str(SHADOW_QUALITY_OUT.relative_to(ROOT)).replace("\\", "/"),
            "tracka_shadow_sweep": str(SWEEP_OUT.relative_to(ROOT)).replace("\\", "/"),
            "tracka_shadow_default_preset": str(PRESET_OUT.relative_to(ROOT)).replace("\\", "/"),
        },
        "metrics_snapshot": {
            "lexicon_4d_coverage_rate": (audit.get("phase_pb_lexicon_coverage") or {}).get(
                "lexicon_4d_coverage_rate"
            ),
            "phase_pa_exact_match_rate": (audit.get("phase_pa_residual") or {}).get("exact_match_rate"),
            "mean_four_d_coherence": (audit.get("phase_pc_path_four_d_shadow") or {}).get(
                "mean_four_d_coherence"
            ),
            "human_review_hint_count": (audit.get("phase_pc_path_four_d_shadow") or {}).get(
                "human_review_hint_count"
            ),
            "key_verse_shadow_rows": (key_shadow.get("summary") or {}).get("shadow_rows"),
            "key_verse_shadow_v2_rows": (key_shadow_v2.get("summary") or {}).get("rows"),
            "term_postit_v2_rows": (term_postit_v2.get("summary") or {}).get("rows"),
            "anchor_index_verse_nodes": (anchor_index.get("summary") or {}).get("verse_nodes"),
            "shadow_quality_overall_ok": (shadow_quality.get("summary") or {}).get("overall_ok"),
            "tracka_shadow_sweep_pareto": len(sweep.get("pareto_top5") or []),
            "tracka_shadow_preset_terms": preset.get("selected_terms_count"),
            "tracka_shadow_preset_delta_jaccard": (preset.get("delta_shadow_minus_raw") or {}).get(
                "avg_reconstruction_fidelity_jaccard"
            ),
        },
        "steps": steps,
        "ok": overall_ok,
        "reproduce": "py scripts/run_logos_lexicon_4d_research_audit_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": overall_ok, "metrics": doc["metrics_snapshot"], "out": str(args.out)}, ensure_ascii=False))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
