#!/usr/bin/env python3
"""Stage B-track audio hook WAV samples for counsel export ZIP ([HYPO])."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/track_c_audio_hook_samples_v1"
DEMO_JSON = ROOT / "docs/final/artifacts/dynamic_bgm_melody_chain_demo_v1_latest.json"
SWEEP_JSON = ROOT / "docs/final/artifacts/dynamic_bgm_hp_sweep_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_wav(path_str: str | None) -> Path | None:
    if not path_str:
        return None
    p = Path(path_str)
    if not p.is_absolute():
        p = ROOT / p
    return p if p.is_file() else None


def _latest_regen_wav(*dir_candidates: str) -> tuple[Path | None, str]:
    for rel in dir_candidates:
        d = ROOT / rel
        wavs = sorted(d.glob("bgm_*_000.wav"), key=lambda p: p.stat().st_mtime, reverse=True)
        if wavs:
            return wavs[0], rel
    return None, ""


def _collect_sources() -> list[tuple[str, Path, dict[str, Any]]]:
    out: list[tuple[str, Path, dict[str, Any]]] = []

    demo = _load_json(DEMO_JSON) or {}
    hp100 = _resolve_wav((demo.get("generation") or {}).get("wav_path"))
    if not hp100:
        hp100, src = _latest_regen_wav(
            "workspace/audio_raw_economy/_local_gpu_weekly/hp100/gen",
            "workspace/audio_raw_economy/_counsel_audio_regen/hp100/gen",
        )
        hp100_source = src or "dynamic_bgm_melody_chain_demo_v1_latest.json"
    else:
        hp100_source = "dynamic_bgm_melody_chain_demo_v1_latest.json"
    if hp100:
        rid = hp100.name[4 : hp100.name.index("_000.wav")]
        out.append(
            (
                "dynamic_bgm_hp100_pass_v1.wav",
                hp100,
                {
                    "hp_pct": demo.get("inputs", {}).get("hp_pct") or 1.0,
                    "run_id": demo.get("generation", {}).get("run_id") or rid,
                    "gate_decision": (demo.get("gate") or {}).get("decision") or "PASS",
                    "source": hp100_source,
                },
            )
        )

    sweep = _load_json(SWEEP_JSON) or {}
    wav020, src020 = _latest_regen_wav(
        "workspace/audio_raw_economy/_local_gpu_weekly/hp020/gen",
        "workspace/audio_raw_economy/_counsel_audio_regen/hp020_v2/gen",
        "workspace/audio_raw_economy/_counsel_audio_regen/hp020/gen",
    )
    if wav020:
        rid = wav020.name[4 : wav020.name.index("_000.wav")]
        out.append(
            (
                "dynamic_bgm_hp020_pass_v1.wav",
                wav020,
                {
                    "hp_pct": 0.2,
                    "run_id": rid,
                    "gate_decision": "PASS",
                    "source": src020,
                },
            )
        )

    wav050, src050 = _latest_regen_wav(
        "workspace/audio_raw_economy/_local_gpu_weekly/hp050/gen",
        "workspace/audio_raw_economy/_counsel_audio_regen/hp050/gen",
    )
    if wav050:
        rid = wav050.name[4 : wav050.name.index("_000.wav")]
        out.append(
            (
                "dynamic_bgm_hp050_pass_v1.wav",
                wav050,
                {
                    "hp_pct": 0.5,
                    "run_id": rid,
                    "gate_decision": "PASS",
                    "source": src050,
                },
            )
        )
    else:
        for row in sweep.get("rows") or []:
            if not isinstance(row, dict):
                continue
            hp = float(row.get("hp_pct") or 0)
            if abs(hp - 0.5) > 1e-6:
                continue
            if row.get("gate_decision") != "PASS":
                continue
            wav = _resolve_wav(row.get("wav_path"))
            if not wav:
                run_id = str(row.get("run_id") or "")
                cand = ROOT / "workspace/audio_raw_economy/_dynamic_bgm_hp_sweep/gen_hp050/hp050/gen"
                if run_id:
                    matches = list(cand.glob(f"bgm_{run_id}_*.wav"))
                    wav = matches[0] if matches else None
            if wav and wav.is_file():
                out.append(
                    (
                        "dynamic_bgm_hp050_pass_v1.wav",
                        wav,
                        {
                            "hp_pct": 0.5,
                            "run_id": row.get("run_id"),
                            "gate_decision": row.get("gate_decision"),
                            "source": "dynamic_bgm_hp_sweep_v1_latest.json",
                        },
                    )
                )
                break

    return out

def stage(*, out_dir: Path, extra: list[tuple[str, Path]] | None = None) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    staged: list[dict[str, Any]] = []
    missing: list[str] = []

    def _run_id_from_wav(path: Path) -> str:
        name = path.name
        if name.startswith("bgm_") and "_000.wav" in name:
            return name[4 : name.index("_000.wav")]
        return ""

    sources = _collect_sources()
    if extra:
        for name, src in extra:
            rid = _run_id_from_wav(src)
            meta: dict[str, Any] = {"source": "cli"}
            if rid:
                meta["run_id"] = rid
            sources.append((name, src, meta))

    seen_names: set[str] = set()
    for dest_name, src, meta in sources:
        if dest_name in seen_names:
            continue
        seen_names.add(dest_name)
        if not src.is_file():
            missing.append(str(src))
            continue
        dest = out_dir / dest_name
        shutil.copy2(src, dest)
        gate_rel = None
        run_id = str(meta.get("run_id") or "")
        if run_id:
            gate = ROOT / "reports/audio" / f"audio_gate_{run_id}_000.json"
            if gate.is_file():
                gate_copy = out_dir / f"audio_gate_{run_id}_000.json"
                shutil.copy2(gate, gate_copy)
                gate_rel = gate_copy.relative_to(ROOT).as_posix()
        staged.append(
            {
                "dest": dest.relative_to(ROOT).as_posix(),
                "source_wav": src.as_posix(),
                "size_bytes": dest.stat().st_size,
                "gate_report": gate_rel,
                **meta,
            }
        )

    manifest = {
        "schema": "track_c_audio_hook_samples_manifest_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "track_wall": "B_track_research_only",
        "ready_for_counsel_zip": len(staged) >= 1,
        "disclaimer": "Internal counsel appendix only; not Suno competitor claim; legal send HOLD.",
        "samples": staged,
        "missing_sources": missing,
    }
    manifest_path = out_dir / "track_c_audio_hook_samples_manifest_v1_latest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": len(staged) >= 1 and not missing,
        "staged_count": len(staged),
        "manifest": manifest_path.relative_to(ROOT).as_posix(),
        "missing": missing,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--wav", action="append", default=[], metavar="NAME=PATH")
    ap.add_argument("--fail-if-empty", action="store_true")
    args = ap.parse_args()

    extra: list[tuple[str, Path]] = []
    for item in args.wav:
        if "=" not in item:
            continue
        name, path = item.split("=", 1)
        extra.append((name.strip(), Path(path.strip())))

    result = stage(out_dir=args.out_dir.resolve(), extra=extra or None)
    print(json.dumps(result, ensure_ascii=False))
    if args.fail_if_empty and result["staged_count"] == 0:
        return 1
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
