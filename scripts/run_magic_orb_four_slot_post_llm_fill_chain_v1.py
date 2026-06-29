#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chain: product boundary → envelope (optional tier15) → post-LLM fill → quality → validate → gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_INSIGHT = ROOT / "docs/final/artifacts/magic_orb_question_insight_v1_latest.json"
DEFAULT_ENVELOPE = ROOT / "docs/final/artifacts/logos_four_slot_generation_envelope_v1_latest.json"
ACK = ROOT / "docs/final/artifacts/magic_orb_four_slot_llm_fill_human_gate_ack_v1_latest.json"
OUT = ROOT / "reports/magic_orb_four_slot_post_llm_fill_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(ROOT))


def _write_ack(*, dummy: bool = False) -> None:
    doc = {
        "schema": "magic_orb_four_slot_llm_fill_human_gate_ack_v1",
        "generated_at_utc": _utc(),
        "human_gate_ack": True,
        "research_only": True,
        "track_a_blocked": True,
        "send_gate": "HOLD",
        "allowed_slots": ["imagination_path", "unknown_gap"],
        "note_ko": (
            "B-track tier_15 post-LLM slot fill — fact_locked·corpus_bound LLM 금지, Track A·SEND 승격 없음."
        ),
        "dummy_template_only": dummy,
    }
    ACK.parent.mkdir(parents=True, exist_ok=True)
    ACK.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--insight-json", type=Path, default=DEFAULT_INSIGHT)
    ap.add_argument("--envelope-json", type=Path, default=DEFAULT_ENVELOPE)
    ap.add_argument("--mode", choices=("template_expand", "live"), default="template_expand")
    ap.add_argument("--human-gate-ack", action="store_true", help="Record ack artifact (required for live).")
    ap.add_argument("--rebuild-envelope", action="store_true")
    ap.add_argument("--enable-tier15-envelope", action="store_true")
    ap.add_argument("--skip-validate", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    steps: dict[str, Any] = {}
    insight_path = args.insight_json if args.insight_json.is_absolute() else ROOT / args.insight_json
    envelope_path = args.envelope_json if args.envelope_json.is_absolute() else ROOT / args.envelope_json

    rc = _run([PY, str(ROOT / "scripts/build_magic_orb_four_slot_product_boundary_v1.py")])
    steps["product_boundary"] = {"ok": rc == 0, "exit_code": rc}
    if rc != 0:
        return rc

    if args.rebuild_envelope or args.enable_tier15_envelope:
        env_cmd = [PY, str(ROOT / "scripts/build_logos_four_slot_generation_envelope_v1.py")]
        if args.enable_tier15_envelope:
            env_cmd.append("--enable-tier15-llm-fill")
        rc = _run(env_cmd)
        steps["envelope_rebuild"] = {"ok": rc == 0, "exit_code": rc}
        if rc != 0:
            return rc

    if args.human_gate_ack and not args.dry_run:
        _write_ack(dummy=args.mode != "live")

    if not envelope_path.is_file():
        print(json.dumps({"ok": False, "error": "missing_envelope"}, ensure_ascii=False))
        return 1
    if not insight_path.is_file():
        print(json.dumps({"ok": False, "error": "missing_insight"}, ensure_ascii=False))
        return 1

    if args.dry_run:
        steps["fill"] = {"ok": True, "dry_run": True, "mode": args.mode}
    else:
        sys.path.insert(0, str(ROOT / "scripts"))
        from magic_orb_four_slot_post_llm_fill_v1 import apply_post_llm_fill, quality_check

        insight = _load(insight_path)
        envelope = _load(envelope_path)
        updated, fill_report = apply_post_llm_fill(
            insight,
            envelope=envelope,
            mode=args.mode,
            human_gate_ack=args.human_gate_ack or ACK.is_file(),
        )
        steps["fill"] = fill_report
        if not fill_report.get("ok"):
            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text(
                json.dumps(
                    {"schema": OUT.stem, "ok": False, "steps": steps},
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            return 1

        q_errors = quality_check(updated, envelope)
        steps["quality"] = {"ok": not q_errors, "errors": q_errors}
        if q_errors:
            return 1

        insight_path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        steps["insight_written"] = {"ok": True, "path": str(insight_path)}

        if not args.skip_validate:
            vrc = _run(
                [
                    PY,
                    str(ROOT / "scripts/validate_magic_orb_four_slot_v1.py"),
                    "--insight-json",
                    str(insight_path),
                ]
            )
            steps["validate"] = {"ok": vrc == 0, "exit_code": vrc}
            if vrc != 0:
                return vrc
            grc = _run(
                [
                    PY,
                    str(ROOT / "scripts/run_magic_orb_four_slot_post_llm_gate_v1.py"),
                    "--insight-json",
                    str(insight_path),
                    "--envelope-json",
                    str(envelope_path),
                ]
            )
            steps["post_llm_gate"] = {"ok": grc == 0, "exit_code": grc}
            if grc != 0:
                return grc

    doc = {
        "schema": "magic_orb_four_slot_post_llm_fill_chain_v1",
        "ok": True,
        "generated_at_utc": _utc(),
        "mode": args.mode,
        "hypothesis_tier": "B",
        "research_only": True,
        "track_a_blocked": True,
        "send_gate": "HOLD",
        "steps": steps,
        "reproduce": (
            "py scripts/run_magic_orb_four_slot_post_llm_fill_chain_v1.py "
            "--human-gate-ack --enable-tier15-envelope --rebuild-envelope"
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
