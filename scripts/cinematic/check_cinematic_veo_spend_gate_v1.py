#!/usr/bin/env python3
"""Economy gate for cinematic Veo spend — reuse local clips before paid Vertex API.

Reads disk SSOT only (no live Billing API). Exit 0 always; decision in JSON.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "cinematic_veo_spend_gate_latest.json"
CREDIT_SSOT = ROOT / "reports" / "nvidia_inception_email_credit_routing_ssot_v1_latest.json"
BILLING_PROBE = ROOT / "reports" / "gcp_billing_overdue_probe_latest.json"
CLIP_DONOR = ART / "cinematic_consistency_pack_v1"
DEFAULT_PROJECT = "mkm-lab-agi-2025"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def clip_ok(path: Path, min_bytes: int = 50_000) -> bool:
    return path.is_file() and path.stat().st_size >= min_bytes


def probe_clip(path: Path) -> dict[str, Any]:
    if not clip_ok(path, min_bytes=1):
        return {"ok": False, "exists": False}
    p = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
        capture_output=True,
    )
    dur = 0.0
    if p.returncode == 0:
        try:
            dur = float((p.stdout or "").strip())
        except Exception:
            dur = 0.0
    return {
        "ok": clip_ok(path),
        "exists": True,
        "bytes": path.stat().st_size,
        "duration_sec": dur,
    }


def credit_signals() -> dict[str, Any]:
    ssot = load_json(CREDIT_SSOT) or {}
    gcp = (ssot.get("gcp_billing_split") or {}).get("inception_mkm_lab") or {}
    credits = gcp.get("credits_notable") or {}
    probe = load_json(BILLING_PROBE) or {}

    startup = str(credits.get("gfs_startup_2k_usd", ""))
    startup_depleted = "depleted" in startup.lower() or "$0 /" in startup

    genai_trial = str(credits.get("genai_app_builder_trial_krw", ""))
    genai_has_balance = "remaining" in genai_trial.lower() and "₩0" not in genai_trial.split("remaining")[0]

    return {
        "billing_account_mkm_lab": gcp.get("billing_account_id"),
        "project_primary": gcp.get("project_primary", DEFAULT_PROJECT),
        "startup_2k_depleted": startup_depleted,
        "genai_app_builder_trial_hint": genai_trial,
        "genai_trial_maybe_remaining": genai_has_balance,
        "nvidia_gcp_inception_credit": (ssot.get("partner_claim_status_2026_06_23") or {}).get("gcp"),
        "billing_probe_verdict": probe.get("verdict"),
        "billing_probe_overdue": probe.get("overdue_or_payment_issue"),
    }


def inventory_hero_clips(workspace: Path, veo_shots: int) -> dict[str, Any]:
    shots: list[dict[str, Any]] = []
    for i in range(1, veo_shots + 1):
        ws = workspace / "shots" / f"shot_{i:02d}" / "clip.mp4"
        donor = CLIP_DONOR / "shots" / f"shot_{i:02d}" / "clip.mp4"
        ws_p = probe_clip(ws)
        donor_p = probe_clip(donor)
        shots.append(
            {
                "shot": i,
                "workspace_clip": ws_p,
                "donor_clip": donor_p,
                "reuse_source": (
                    "workspace"
                    if ws_p.get("ok")
                    else ("donor_pack" if donor_p.get("ok") else None)
                ),
            }
        )
    missing = [s["shot"] for s in shots if not s["reuse_source"]]
    return {"shots": shots, "missing_count": len(missing), "missing_shots": missing}


def decide(
    *,
    allow_veo_spend: bool,
    veo_smoke: bool,
    veo_overwrite: bool,
    inventory: dict[str, Any],
    credits: dict[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    missing = inventory["missing_count"]
    reuse_all = missing == 0 and not veo_overwrite

    if reuse_all:
        return {
            "mode": "reuse_local",
            "allow_veo_api": False,
            "veo_shots_to_generate": 0,
            "reasons": ["hero_clips_already_present", "no_overwrite"],
            "spend_risk": "none",
        }

    if not allow_veo_spend:
        if missing < inventory["shots"].__len__():
            reasons.append("partial_reuse_then_animatic_fallback")
        else:
            reasons.append("no_local_hero_clips")
        reasons.append("veo_spend_not_explicitly_allowed")
        return {
            "mode": "animatic_or_reuse_only",
            "allow_veo_api": False,
            "veo_shots_to_generate": 0,
            "reasons": reasons,
            "spend_risk": "none",
        }

    # Explicit spend requested — still economy caps
    if credits.get("startup_2k_depleted"):
        reasons.append("startup_2k_depleted_use_caution")
    if credits.get("billing_probe_overdue"):
        reasons.append("billing_probe_overdue_flag")
    if not credits.get("genai_trial_maybe_remaining"):
        reasons.append("genai_trial_not_confirmed_for_veo_sku")

    to_gen = missing if not veo_overwrite else inventory["shots"].__len__()
    if veo_smoke:
        to_gen = min(1, to_gen if to_gen else 1)

    return {
        "mode": "veo_smoke" if veo_smoke else "veo_generate",
        "allow_veo_api": to_gen > 0,
        "veo_shots_to_generate": to_gen,
        "reasons": reasons or ["allow_veo_spend_flag_set"],
        "spend_risk": "vertex_billed_maybe_credit_offset",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ART / "cinematic_auditable_poc_v1")
    ap.add_argument("--veo-shots", type=int, default=3)
    ap.add_argument("--allow-veo-spend", action="store_true")
    ap.add_argument("--veo-smoke", action="store_true")
    ap.add_argument("--veo-overwrite", action="store_true")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    allow = args.allow_veo_spend or os.environ.get("MKM_CINEMATIC_ALLOW_VEO_SPEND", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    workspace = args.workspace_root if args.workspace_root.is_absolute() else (ROOT / args.workspace_root)
    inventory = inventory_hero_clips(workspace, args.veo_shots)
    credits = credit_signals()
    decision = decide(
        allow_veo_spend=allow,
        veo_smoke=args.veo_smoke,
        veo_overwrite=args.veo_overwrite,
        inventory=inventory,
        credits=credits,
    )

    payload = {
        "schema": "cinematic_veo_spend_gate_v1",
        "generated_at_utc": now_utc(),
        "ok": True,
        "economy_default": "reuse_local_then_animatic_no_veo_api",
        "vertex_project": credits.get("project_primary", DEFAULT_PROJECT),
        "inputs": {
            "workspace_root": str(workspace),
            "veo_shots": args.veo_shots,
            "allow_veo_spend": allow,
            "veo_smoke": args.veo_smoke,
            "veo_overwrite": args.veo_overwrite,
        },
        "credit_signals": credits,
        "clip_inventory": inventory,
        "decision": decision,
        "recommendation": (
            "py scripts/cinematic/run_auditable_cinematic_poc_v1.py"
            if not decision.get("allow_veo_api")
            else "py scripts/cinematic/run_auditable_cinematic_poc_v1.py --allow-veo-spend"
            + (" --veo-smoke" if args.veo_smoke else "")
        ),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "decision": decision, "out_json": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
