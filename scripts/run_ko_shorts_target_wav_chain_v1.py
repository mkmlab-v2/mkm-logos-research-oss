#!/usr/bin/env python3
"""P1 target WAV chain — auto-resolve WAV → spike → burn-in → validate [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ko_shorts_alignment_routing_lib_v1 import MODE_AUTO  # noqa: E402
from scripts.ko_shorts_target_wav_lib_v1 import (  # noqa: E402
    qa_case_dict_from_artifacts,
    resolve_target_wav_v1,
)
from scripts.ko_shorts_cursor_ide_qa_lib_v1 import run_case_cursor_qa_v1  # noqa: E402
from scripts.ko_shorts_subtitle_gate_lib_v1 import PROFILES, evaluate_subtitle_gate_v1, refine_segments_for_profile_v1  # noqa: E402

DEFAULT_OUT = ROOT / "reports/ko_shorts_target_wav_chain_v1_latest.json"
ALIGN_VENV_PY = ROOT / ".venv-ko-shorts-align" / "Scripts" / "python.exe"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run_step(name: str, cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    tail_lines = (proc.stdout or proc.stderr or "").strip().splitlines()
    tail = tail_lines[-1] if tail_lines else ""
    step: dict[str, Any] = {"step": name, "exit_code": proc.returncode, "cmd": cmd, "tail": tail, "ok": proc.returncode == 0}
    try:
        step["summary"] = json.loads(tail)
    except Exception:
        if proc.stderr:
            step["stderr_tail"] = proc.stderr.strip()[-500:]
    return step


def _python_for_alignment() -> str:
    return str(ALIGN_VENV_PY) if ALIGN_VENV_PY.is_file() else sys.executable


def run_target_wav_chain_v1(
    *,
    wav: Path | None,
    case_id: str | None,
    auto: bool,
    profile: str,
    domain_hint: str | None,
    skip_burn: bool,
    skip_alignment: bool,
    refetch_missing: bool,
    delegate: bool = False,
    delegation_sidecar: Path | None = None,
) -> dict[str, Any]:
    resolved = resolve_target_wav_v1(
        wav=wav,
        case_id=case_id,
        auto=auto,
        refetch_missing=refetch_missing,
        domain_hint=domain_hint,
        delegate=delegate,
        delegation_sidecar=delegation_sidecar,
    )
    cid = resolved["case_id"]
    wav_path: Path = resolved["wav"]
    art = resolved["artifacts"]
    spike_out = ROOT / art["spike_json"]
    spike_srt = ROOT / art["spike_srt"]
    steps: list[dict[str, Any]] = []

    steps.append(
        {
            "step": "resolve_wav",
            "exit_code": 0,
            "ok": True,
            "summary": {
                "ok": True,
                "case_id": cid,
                "wav": resolved["wav_rel"],
                "wav_resolved_via": resolved["wav_resolved_via"],
                "domain_hint": resolved.get("domain_hint"),
            },
        }
    )

    steps.append(
        _run_step(
            "timing_spike",
            [
                sys.executable,
                str(ROOT / "scripts/run_ko_shorts_stt_timing_spike_v1.py"),
                "--wav",
                str(wav_path),
                "--out",
                str(spike_out),
                "--srt-out",
                str(spike_srt),
                "--subtitle-profile",
                profile,
            ],
        )
    )

    burn_cmd = [
        sys.executable,
        str(ROOT / "scripts/run_ko_shorts_ass_burnin_v1.py"),
        "--spike-json",
        str(spike_out),
        "--wav",
        str(wav_path),
        "--profile",
        profile,
        "--ass-out",
        str(ROOT / art["ass"]),
        "--srt-out",
        str(ROOT / art["srt"]),
        "--mp4-out",
        str(ROOT / art["mp4"]),
        "--meta-out",
        str(ROOT / art["burnin_meta"]),
    ]
    if skip_burn:
        burn_cmd.append("--skip-burn")
    steps.append(_run_step("burnin", burn_cmd))

    if not skip_alignment:
        align_cmd = [
            _python_for_alignment(),
            str(ROOT / "scripts/run_ko_shorts_alignment_backend_spike_v1.py"),
            "--cases",
            cid,
            "--alignment-backend",
            MODE_AUTO,
        ]
        if resolved.get("domain_hint"):
            align_cmd.extend(["--domain-hint", str(resolved["domain_hint"])])
        steps.append(_run_step("alignment_routed", align_cmd))

    spike_doc = _read_json(spike_out) if spike_out.is_file() else {}
    profile_obj = PROFILES[profile]
    p1 = list(spike_doc.get("p1_segments") or [])
    refined = refine_segments_for_profile_v1(p1, profile_obj, two_pass=True)
    gate = evaluate_subtitle_gate_v1(refined, profile_obj)
    qa_case = qa_case_dict_from_artifacts(art)
    qa = run_case_cursor_qa_v1(qa_case, profile_key=profile)
    checks = qa.get("checks") or {}
    qa_pass = bool(qa.get("ok")) and all(
        bool((checks.get(k) or {}).get("auto_pass"))
        for k in ("p1_anchor_sync", "profile_parent_span", "safe_area_frames", "ass_margin_v")
    )
    validate_ok = bool(gate.get("gate_pass")) and qa_pass and all(s["ok"] for s in steps if s["step"] != "resolve_wav")

    return {
        "schema": "ko_shorts_target_wav_chain_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "generated_at_utc": _utc_now(),
        "case_id": cid,
        "profile": profile,
        "wav_resolved_via": resolved["wav_resolved_via"],
        "wav": resolved["wav_rel"],
        "domain_hint": resolved.get("domain_hint"),
        "alignment_backend": MODE_AUTO,
        "ok": validate_ok,
        "gate_pass": gate.get("gate_pass"),
        "qa_auto_pass": qa_pass,
        "steps": steps,
        "artifacts": art,
        "reproduce": f"py scripts/run_ko_shorts_target_wav_chain_v1.py --auto --case-id {cid} --profile {profile}",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wav", type=Path, default=None, help="optional; missing + --case-id triggers OSS fetch")
    ap.add_argument("--case-id", default=None, help="web_pansori|web_deeply|web_youtube_edu or target_*")
    ap.add_argument("--auto", action="store_true", help="default target web_pansori + fetch if missing")
    ap.add_argument("--delegate", action="store_true", help="resolve custom WAV from sidecar/env/inbox")
    ap.add_argument("--delegation-sidecar", type=Path, default=None)
    ap.add_argument("--profile", default="netflix_v16_pro", choices=list(PROFILES))
    ap.add_argument("--domain-hint", default=None)
    ap.add_argument("--skip-burn", action="store_true")
    ap.add_argument("--skip-alignment", action="store_true")
    ap.add_argument("--no-refetch", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    use_auto = args.auto or (not args.wav and not args.case_id and not args.delegate)
    report = run_target_wav_chain_v1(
        wav=args.wav,
        case_id=args.case_id,
        auto=use_auto,
        profile=args.profile,
        domain_hint=args.domain_hint,
        skip_burn=args.skip_burn,
        skip_alignment=args.skip_alignment,
        refetch_missing=not args.no_refetch,
        delegate=args.delegate,
        delegation_sidecar=args.delegation_sidecar,
    )
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": report["ok"],
                "case_id": report["case_id"],
                "wav": report["wav"],
                "wav_resolved_via": report["wav_resolved_via"],
                "out": _rel(out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
