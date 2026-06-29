#!/usr/bin/env python3
"""Build commander developer day pack from daily fortune + profile [HYPO].

B-track / research_only — developer coaching (not trading triggers).
Optional RQ-026 sim interpretive lines (CLOSED archive, non-gating).
Output: reports/commander_dev_day_pack_latest.json
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FORTUNE = ROOT / "reports" / "commander_daily_fortune_latest.json"
DEFAULT_OUT = ROOT / "reports" / "commander_dev_day_pack_latest.json"
DEFAULT_PROFILE = ROOT / "data" / "personalization" / "commander_profile_v1.local.json"
EXAMPLE_PROFILE = ROOT / "docs" / "final" / "artifacts" / "commander_profile_v1.example.json"
MAP_PATH = ROOT / "docs" / "final" / "artifacts" / "commander_dev_pack_pet_bridge_field_map_v1.json"
SIM_PATH = ROOT / "reports" / "sasang_temperament_agents_sim_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _truthy(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None or not str(v).strip():
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def _profile_path(explicit: Optional[Path]) -> Path:
    if explicit and explicit.is_file():
        return explicit
    try:
        import importlib.util

        resolver_path = ROOT / "scripts/a_code_commander_profile_resolve_v1.py"
        spec = importlib.util.spec_from_file_location("a_code_profile_resolve", resolver_path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            path, _ = mod.resolve_commander_profile_path(None)
            return path
    except Exception:
        pass
    if DEFAULT_PROFILE.is_file():
        return DEFAULT_PROFILE
    return EXAMPLE_PROFILE


def _a_code_governor_note(workspace: Path) -> Optional[Dict[str, Any]]:
    obs_path = workspace / "reports" / "a_code_governor_knob_evening_observation_v1_latest.json"
    gate_path = workspace / "reports" / "a_code_governor_promotion_gate_v1_latest.json"
    if not obs_path.is_file():
        return None
    obs = _read_json(obs_path)
    if obs.get("schema") != "a_code_governor_knob_evening_observation_v1":
        return None
    gate = _read_json(gate_path) if gate_path.is_file() else {}
    gate_summary = gate.get("summary") or {}
    return {
        "source": "RQ-028 WATCH",
        "evening_append_line": obs.get("evening_append_line"),
        "adjusted_knobs": obs.get("adjusted_knobs"),
        "gate_decision": gate_summary.get("decision"),
        "interpretive_ko": str(obs.get("evening_append_line") or "")[:220],
    }


def _first_myeongni_line(fortune: Dict[str, Any]) -> str:
    for block in fortune.get("blocks") or []:
        if block.get("id") == "myeongni":
            lines = block.get("lines") or []
            if lines:
                return str(lines[0])
    for ln in fortune.get("telegram_append_lines") or []:
        if ln.startswith("▸ 오늘 한 줄:"):
            return ln.replace("▸ 오늘 한 줄:", "").strip()
    return "Fact-Lock·검증 우선; 확장은 증거 후 [가설]"


def _four_ai_dev_roles(profile: Dict[str, Any], fortune: Dict[str, Any]) -> Dict[str, str]:
    sasang = ((profile.get("sasang_reference") or {}).get("label")) or "태양인"
    roles = {
        "taeyang": "설계·아키텍처·DoD 정의 — 오늘 주역 [가설]",
        "soeum": "수면·페이싱·저위험 자동화 — low_sleep 정합 [가설]",
        "taeeum": "구조·pytest·exit code 마감 — Fact-Lock 게이트 [가설]",
        "soyang": "대외·TG·파트너 말 — 필요한 만큼만 (과부하 방지) [가설]",
    }
    if sasang == "태양인":
        roles["taeyang"] = "★ " + roles["taeyang"]
    coaching = profile.get("assist_coaching_v1") or {}
    for tip in (coaching.get("energy_preservation") or [])[:1]:
        roles["coordinator"] = f"절대 균형(조율): {tip} [가설]"
    else:
        roles["coordinator"] = "절대 균형(조율): 채널 1개·스크립트 우선 [가설]"
    _ = fortune  # reserved for future tilt from fortune blocks
    return roles


def _rq026_sim_note(workspace: Path) -> Optional[Dict[str, Any]]:
    if not _truthy("MKM_COMMANDER_DEV_PACK_INCLUDE_RQ026_SIM", default=True):
        return None
    path = workspace / "reports" / "sasang_temperament_agents_sim_v1_latest.json"
    if not path.is_file():
        return None
    doc = _read_json(path)
    if doc.get("rq_id") != "RQ-026":
        return None
    steps = doc.get("daily_steps") or []
    if not steps:
        return None
    last = steps[-1]
    agents = last.get("agents") or []
    by_id = {a.get("constitution_id"): a for a in agents if isinstance(a, dict)}
    ty = by_id.get("taeyang") or {}
    env = last.get("environment") or {}
    return {
        "source": "RQ-026 CLOSED archive",
        "eval_date": last.get("eval_date"),
        "pathology_scalar_taeyang": ty.get("pathology_scalar"),
        "byungjeung_state": env.get("byungjeung_state"),
        "interpretive_ko": (
            f"성정 시뮬(아카이브): 태양 scalar {ty.get('pathology_scalar', '—')} · "
            f"환경 {env.get('byungjeung_state', '—')} — 가격·실매매 근거 아님 [HYPO]"
        ),
        "naming_firewall": doc.get("naming_firewall_ko"),
    }


def build_pack(
    *,
    fortune_path: Path,
    profile_path: Path,
    workspace: Path = ROOT,
) -> Dict[str, Any]:
    fortune: Dict[str, Any] = {}
    if fortune_path.is_file():
        fortune = _read_json(fortune_path)
    profile = _read_json(profile_path) if profile_path.is_file() else {}

    one_line = _first_myeongni_line(fortune)
    coaching = profile.get("assist_coaching_v1") or {}
    energy_lines = list(coaching.get("energy_preservation") or [])[:2]
    user_cond = fortune.get("user_condition") if isinstance(fortune.get("user_condition"), dict) else {}
    sleep_note = ""
    if user_cond.get("low_sleep"):
        sleep_note = "저수면 — 깊은 리팩터·야간 배포 자제; 스크립트·검증 위주 [가설]"

    four_ai = _four_ai_dev_roles(profile, fortune)
    sim_note = _rq026_sim_note(workspace)
    a_code_note = _a_code_governor_note(workspace)

    checklist = [
        "P0 경로·pytest 스모크 (저위험 변경 시)",
        "1작업=1브랜치; push-internal만",
        "장전 TG prophecy 1통 — four_lens 아님",
    ]
    if sleep_note:
        checklist.insert(0, sleep_note)

    telegram_lines: List[str] = [
        "",
        "▸ 개발 코치 [가설]",
        f"  초점: {one_line[:120]}",
        f"  {four_ai.get('taeyang', '')}",
        f"  {four_ai.get('soeum', '')}",
    ]
    if sim_note and sim_note.get("interpretive_ko"):
        telegram_lines.append(f"  {sim_note['interpretive_ko'][:200]}")
    if a_code_note and a_code_note.get("evening_append_line"):
        telegram_lines.append(f"  {str(a_code_note['evening_append_line'])[:220]}")
    telegram_lines.append("  ≠ 실매매·Track A · pet [TARGET]과 profile 분리")
    telegram_lines.append("")

    map_doc: Dict[str, Any] = {}
    if MAP_PATH.is_file():
        map_doc = {"ref": str(MAP_PATH.relative_to(ROOT)).replace("\\", "/"), "rows": 10}

    def _rel(p: Path) -> str:
        try:
            return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
        except ValueError:
            return str(p)

    return {
        "schema": "commander_dev_day_pack_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "not_promoted_track_a": True,
        "pack_meta": {
            "profile_id": "commander-dev",
            "fortune_ref": _rel(fortune_path),
            "profile_ref": _rel(profile_path),
        },
        "developer_coaching": {
            "one_line": one_line,
            "preferred_style": coaching.get("preferred_briefing_style"),
            "default_channels_per_day": coaching.get("default_output_channels_per_day"),
        },
        "energy_pacing": {
            "summary": sleep_note or (energy_lines[0] if energy_lines else "에너지 보존 모드 [가설]"),
            "tips": energy_lines,
        },
        "four_ai_roles_for_dev": four_ai,
        "checklist_today": checklist,
        "trust_packet_v2": {
            "hypothesis_labeled": True,
            "track_wall": coaching.get("track_wall"),
        },
        "fortune_ref": {
            "schema": fortune.get("schema"),
            "as_of_date": fortune.get("as_of_date"),
            "life_oracle_present": bool(fortune.get("life_oracle")),
        },
        "rq026_sim_note": sim_note,
        "a_code_governor_note": a_code_note,
        "pet_bridge_field_map_ref": map_doc,
        "telegram_dev_coach_lines": telegram_lines,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fortune-json", type=Path, default=DEFAULT_FORTUNE)
    ap.add_argument("--profile-json", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    payload = build_pack(
        fortune_path=args.fortune_json,
        profile_path=_profile_path(args.profile_json),
    )
    if not args.stdout_only:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {args.out_json}")
    for ln in payload.get("telegram_dev_coach_lines") or []:
        print(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
