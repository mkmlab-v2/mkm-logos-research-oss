#!/usr/bin/env python3
"""Draft Nemotron LoRA MKM lens prompt card from PROMPT_DRYRUN_LOCAL sweep [HYPO].

Does not wire into train — `wired_into_train: false` fixed.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SWEEP = ROOT / "reports/prompt_dryrun_local_mkm_lens_sweep_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/nemotron_lora_mkm_lens_prompt_card_v1_latest.json"
BASE_SYSTEM = ROOT / "reports/ollama_gemma_local_system_prompt_v1.txt"

# Import constants from dryrun script (same repo, no subprocess).
import importlib.util

_DRYRUN = ROOT / "scripts/run_prompt_dryrun_local_mkm_lens_v1.py"


def _load_dryrun():
    spec = importlib.util.spec_from_file_location("prompt_dryrun", _DRYRUN)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def _utc_now() -> str:
    return datetime.now(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_card(sweep_path: Path, system_file: Path) -> dict:
    dry = _load_dryrun()
    sweep: dict = {}
    if sweep_path.is_file():
        sweep = json.loads(sweep_path.read_text(encoding="utf-8"))

    system_template = ""
    if system_file.is_file():
        system_template = system_file.read_text(encoding="utf-8").strip()

    rows = sweep.get("rows") or []
    profile_summaries = []
    for r in rows:
        score = r.get("score") or {}
        profile_summaries.append(
            {
                "label": r.get("label"),
                "iana_tz": r.get("iana_tz"),
                "utc_instant": r.get("utc_instant"),
                "local": r.get("local"),
                "place": r.get("place"),
                "model": r.get("model"),
                "ollama_ok": r.get("ollama_ok"),
                "pass_heuristic": score.get("pass_heuristic"),
                "birth_anchor_engine_year": (r.get("birth_anchor") or {})
                .get("engine_inputs", {})
                .get("year"),
            }
        )

    return {
        "schema": "nemotron_lora_mkm_lens_prompt_card_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "wired_into_train": False,
        "auto_apply": False,
        "track_wall": "no_track_a_live_auto_merge",
        "action_id": "NEMOTRON_LORA_MKM_LENS_PROMPT_CARD",
        "purpose_ko": (
            "Nemotron LoRA 학습용 USER/system 프롬프트 초안 — "
            "PROMPT_DRYRUN_LOCAL 스윕 근거만; 본선 train 미연결"
        ),
        "user_prompt_template": dry.USER_PROMPT,
        "system_prompt_file": str(system_file.relative_to(ROOT)).replace("\\", "/"),
        "system_prompt_template_preview": system_template[:2000],
        "sweep_evidence_path": str(sweep_path.relative_to(ROOT)).replace("\\", "/"),
        "sweep_summary": {
            "n_profiles": sweep.get("n_profiles", len(rows)),
            "n_pass_heuristic": sweep.get("n_pass_heuristic"),
            "all_pass": sweep.get("all_pass"),
            "generated_at_utc": sweep.get("generated_at_utc"),
        },
        "default_sweep_profiles": list(dry.SWEEP_PROFILES),
        "profile_results": profile_summaries,
        "ollama_models": {
            "primary": dry.DEFAULT_MODEL,
            "fallback": dry.FALLBACK_MODEL,
        },
        "operator_notes": [
            "LoRA JSONL 생성 시 birth_anchor는 run_saju_global_birth_v1 출력만 사용",
            "성경 렌즈는 [NON_GATING] literal 필수; 사상은 [HYPO]",
            "Final Action = HOLD|WATCH only; 매매·가격 단정 금지",
            "wired_into_train=true 전환은 human sign-off + 별도 PR",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sweep-json", type=Path, default=DEFAULT_SWEEP)
    ap.add_argument("--system-file", type=Path, default=BASE_SYSTEM)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    card = build_card(args.sweep_json, args.system_file)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), "all_pass": card["sweep_summary"].get("all_pass")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
