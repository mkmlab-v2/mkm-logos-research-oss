#!/usr/bin/env python3
"""Record commander approval for LoRA tranche-2 multi-pack (bench 4×40 B-track).

Does NOT approve Track A promotion or live trading. Refreshes signoff + Track C copy.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SIGNOFF = ROOT / "reports/lora_tranche2_multipack_human_signoff_latest.json"
DEFAULT_GO = ROOT / "reports/lora_tranche2_multipack_go_no_go_latest.json"
DEFAULT_TRANCHE2_SIGNOFF = ROOT / "docs/final/artifacts/lora_tranche2_signoff_pack_v1_latest.json"
DEFAULT_QWEN4 = ROOT / "reports/lora_tranche2_qwen4pack_train_ablation_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd))
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def build_signoff(
    *,
    approver: str,
    note: str,
    qwen4: dict[str, Any],
    tranche2: dict[str, Any],
) -> dict[str, Any]:
    diversity_ok = qwen4.get("diversity", {}).get("diversity_ok") is True
    tranche_ready = tranche2.get("tranche2_btrack_ready") is True
    approved = diversity_ok and tranche_ready

    return {
        "schema": "lora_tranche2_multipack_human_signoff_v1",
        "recorded_at_utc": _utc_now(),
        "approver": approver,
        "approved": approved,
        "decision": "APPROVED_BENCH_4X40_BTRACK" if approved else "BLOCKED_PREREQ",
        "scope": {
            "architecture": "bench_4x40",
            "approved_pack_count": 4,
            "allow_deploy_multipack_btrack": approved,
            "mkm12_expansion_lane": "hier_12x75_hybrid",
            "track_a_promotion": False,
            "live_trading": False,
            "single_pack_rc_unchanged": True,
            "vision_20x200_production": False,
        },
        "prerequisites": {
            "qwen4pack_diversity_ok": diversity_ok,
            "tranche2_btrack_ready": tranche_ready,
            "qwen4pack_ablation_json": str(DEFAULT_QWEN4.relative_to(ROOT)).replace("\\", "/"),
        },
        "note_ko": note,
        "disclaimer": (
            "B-track bench 4×40 multi-pack deploy scope only. "
            "Not Track A·MS·live-trading authorization."
        ),
    }


def build_go_no_go(signoff: dict[str, Any]) -> dict[str, Any]:
    approved = signoff.get("approved") is True
    return {
        "schema": "lora_tranche2_multipack_go_no_go_v1",
        "generated_at_utc": _utc_now(),
        "human_signoff_approved": approved,
        "allow_deploy_multipack_btrack": approved,
        "validation_passed": signoff.get("prerequisites", {}).get("qwen4pack_diversity_ok") is True,
        "track_a_promotion": False,
        "live_trading": False,
        "required_actions": [] if approved else ["complete_qwen4pack_ablation", "tranche2_btrack_ready"],
        "signoff_ref": str(DEFAULT_SIGNOFF.relative_to(ROOT)).replace("\\", "/"),
        "scope": signoff.get("scope", {}),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Apply LoRA tranche-2 multi-pack commander approval.")
    p.add_argument("--approver", default="commander")
    p.add_argument(
        "--note",
        default="지휘관 승인: bench 4×40 Qwen distinct-adapter B-track 멀티팩. Track A·실매매 OFF.",
    )
    p.add_argument("--signoff-out", default=str(DEFAULT_SIGNOFF))
    p.add_argument("--go-no-go-out", default=str(DEFAULT_GO))
    p.add_argument("--skip-refresh", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    qwen4 = _read_json(DEFAULT_QWEN4)
    tranche2 = _read_json(DEFAULT_TRANCHE2_SIGNOFF)

    signoff = build_signoff(
        approver=args.approver,
        note=args.note,
        qwen4=qwen4,
        tranche2=tranche2,
    )
    go = build_go_no_go(signoff)

    if args.dry_run:
        print(json.dumps({"signoff": signoff, "go_no_go": go}, ensure_ascii=False, indent=2))
        return 0

    for path, doc in (
        (Path(args.signoff_out), signoff),
        (Path(args.go_no_go_out), go),
    ):
        out = path if path.is_absolute() else ROOT / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {out}")

    if not args.skip_refresh:
        for script in (
            "scripts/build_lora_tranche2_signoff_pack_v1.py",
            "scripts/build_lora_tranche2_trackc_copy_v1.py",
        ):
            rc = _run([sys.executable, str(ROOT / script)])
            if rc != 0:
                return rc

    print(json.dumps({"approved": signoff["approved"], "allow_deploy_multipack_btrack": go["allow_deploy_multipack_btrack"]}))
    return 0 if signoff["approved"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
