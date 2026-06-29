#!/usr/bin/env python3
"""[HYPO] Auto Tier0 ingest for Design/S1 cinematic LIT backlog (disk-backed facts)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "docs/research/raw"
DIGEST = ROOT / "scripts/run_mkm_digestion_engine_chain_v1.py"
OUT = ROOT / "reports/design_s1_lit_tier0_auto_ingest_v1_latest.json"
SHOT_PLAN = ROOT / "docs/final/artifacts/director_agent_v2_shot_plan_latest.json"
BOOTSTRAP = ROOT / "docs/final/artifacts/cinematic_v2_workspace_bootstrap_latest.json"
SHOT01 = ROOT / "docs/final/artifacts/cinematic_v2_shot01_flow_handoff_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _fact(
    fact_id: str,
    metric_name: str,
    value: float,
    unit: str,
    arm: str,
    artifact_path: str,
    artifact_field: str,
    *,
    plane: str = "design_cinematic",
    assertion: str = "eq",
) -> str:
    return f"""### fact_id: {fact_id}
- metric_name: {metric_name}
- value: {value}
- unit: {unit}
- comparison_arm: {arm}
- verification_status: Right
- verification_method: local_artifact
- baseline_plane: {plane}
- artifact_path: {artifact_path}
- artifact_field: {artifact_field}
- assertion: {assertion}
"""


def _wrap(filename: str, lit: str, summary: str, facts: list[str]) -> str:
    rel = f"docs/research/raw/{filename}"
    return f"""# {lit} — Tier0 auto-ingest

**Generated:** {_utc()} · **Source LIT:** docs/research/{lit}
**Track:** B-track · research_only · send_gate HOLD

## Summary

{summary}

## Digested facts

{"".join(facts)}

## Reproduce

```powershell
py scripts/run_mkm_digestion_engine_chain_v1.py --input {rel} --offline
```
"""


def _build_daily_micro_cinematic() -> str:
    plan = _load(SHOT_PLAN)
    boot = _load(BOOTSTRAP)
    shot01 = _load(SHOT01)
    outputs = shot01.get("outputs") or {}
    facts = [
        _fact(
            "cinematic_v2_target_shots",
            "target_shots",
            float(plan.get("target_shots") or 0),
            "count",
            "director_agent_v2",
            "docs/final/artifacts/director_agent_v2_shot_plan_latest.json",
            "target_shots",
        ),
        _fact(
            "cinematic_v2_shot_sec",
            "shot_sec",
            float(plan.get("shot_sec") or 0),
            "count",
            "director_agent_v2",
            "docs/final/artifacts/director_agent_v2_shot_plan_latest.json",
            "shot_sec",
        ),
        _fact(
            "cinematic_v2_total_duration_sec",
            "total_duration_sec",
            float(plan.get("total_duration_sec") or 0),
            "count",
            "director_agent_v2",
            "docs/final/artifacts/director_agent_v2_shot_plan_latest.json",
            "total_duration_sec",
        ),
        _fact(
            "cinematic_v2_workspace_shot_count",
            "shot_count",
            float(boot.get("shot_count") or 0),
            "count",
            "cinematic_v2_workspace_bootstrap",
            "docs/final/artifacts/cinematic_v2_workspace_bootstrap_latest.json",
            "shot_count",
        ),
        _fact(
            "cinematic_v2_shot01_narration_wav_exists",
            "narration_wav_exists",
            1.0 if outputs.get("narration_wav_exists") else 0.0,
            "count",
            "cinematic_v2_shot01_handoff",
            "docs/final/artifacts/cinematic_v2_shot01_flow_handoff_latest.json",
            "outputs.narration_wav_exists",
        ),
    ]
    return _wrap(
        "daily_micro_cinematic_voice_video_tier0_2026-06-23.md",
        "DAILY_MICRO_CINEMATIC_VOICE_VIDEO_LIT_REVIEW_2026-06-23.md",
        "Daily micro-cinematic LIT wired to v2 shot plan + workspace bootstrap + Shot01 handoff on disk.",
        facts,
    )


def _build_video_prompt_tips_flow_veo() -> str:
    plan = _load(SHOT_PLAN)
    shot01 = _load(SHOT01)
    facts = [
        _fact(
            "flow_veo_target_shots",
            "target_shots",
            float(plan.get("target_shots") or 0),
            "count",
            "director_agent_v2",
            "docs/final/artifacts/director_agent_v2_shot_plan_latest.json",
            "target_shots",
        ),
        _fact(
            "flow_veo_shot01_duration_sec",
            "duration_sec",
            float(shot01.get("duration_sec") or 0),
            "count",
            "cinematic_v2_shot01_handoff",
            "docs/final/artifacts/cinematic_v2_shot01_flow_handoff_latest.json",
            "duration_sec",
        ),
        _fact(
            "flow_veo_shot01_clip_exists",
            "clip_mp4_exists",
            1.0 if (shot01.get("outputs") or {}).get("clip_mp4_exists") else 0.0,
            "count",
            "cinematic_v2_shot01_handoff",
            "docs/final/artifacts/cinematic_v2_shot01_flow_handoff_latest.json",
            "outputs.clip_mp4_exists",
        ),
        _fact(
            "flow_veo_ready_for_i2v",
            "ready_for_flow_i2v",
            1.0 if shot01.get("ready_for_flow_i2v") else 0.0,
            "count",
            "cinematic_v2_shot01_handoff",
            "docs/final/artifacts/cinematic_v2_shot01_flow_handoff_latest.json",
            "ready_for_flow_i2v",
        ),
    ]
    return _wrap(
        "video_prompt_tips_flow_veo_tier0_2026-06-23.md",
        "VIDEO_PROMPT_TIPS_FLOW_VEO_LIT_REVIEW_2026-06-23.md",
        "Flow/Veo prompt tips LIT wired to director v2 shot plan + Shot01 Flow handoff blockers on disk.",
        facts,
    )


TOPICS: list[tuple[str, Callable[[], str]]] = [
    ("daily_micro_cinematic_voice_video_tier0_2026-06-23.md", _build_daily_micro_cinematic),
    ("video_prompt_tips_flow_veo_tier0_2026-06-23.md", _build_video_prompt_tips_flow_veo),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-digest", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    rc = 0

    for filename, builder in TOPICS:
        path = RAW / filename
        rel = path.relative_to(ROOT).as_posix()
        if path.is_file() and not args.force:
            steps.append({"file": rel, "action": "skip_exists"})
        else:
            RAW.mkdir(parents=True, exist_ok=True)
            path.write_text(builder(), encoding="utf-8")
            steps.append({"file": rel, "action": "wrote"})

        if not args.skip_digest:
            cp = subprocess.run(
                [sys.executable, str(DIGEST), "--input", rel, "--offline"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            tail = (cp.stdout or "").strip().splitlines()
            parsed = json.loads(tail[-1]) if tail else None
            steps.append({"file": rel, "digest_exit_code": int(cp.returncode), "parsed": parsed})
            if cp.returncode != 0:
                rc = cp.returncode

    manifest = {
        "schema": "design_s1_lit_tier0_auto_ingest_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "steps": steps,
        "rc": rc,
        "topic_count": len(TOPICS),
        "reproducible_command": "py scripts/build_design_s1_lit_tier0_auto_ingest_v1.py --force",
    }
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "rc": rc, "topics": len(TOPICS)}))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
