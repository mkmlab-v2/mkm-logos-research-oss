# Keywords: showroom, lens_audio, public-event, thin_slice, playback_lut
"""Build public-event.v1 lens_audio_observability_v1 block from weekday CPU artifacts."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

TREND_PATH = ROOT / "docs/final/artifacts/lens_music_hormone_trend_latest.json"
SWEEP_PATH = ROOT / "docs/final/artifacts/dynamic_bgm_hp_sweep_v1_latest.json"
DEMO_PATH = ROOT / "docs/final/artifacts/dynamic_bgm_melody_chain_demo_v1_latest.json"
LUT_EXAMPLE = ROOT / "docs/final/artifacts/jemaai_lens_audio_playback_lut_v1.example.json"
LUT_LATEST = ROOT / "docs/final/artifacts/jemaai_lens_audio_playback_lut_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/showroom_lens_audio_observability_v1_latest.json"
SLICE_OUT = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_lens_audio_thin_slice_v1.json"
)

_HP_TAG = {0.2: "HP020", 0.5: "HP050", 1.0: "HP100"}
_SASANG_ENUM = {"soyang", "taeyang", "taeeum", "soeum"}
_PLAYBACK_RE = re.compile(
    r"^LM_HP(020|050|100)_(SOYANG|TAEYANG|TAEEUM|SOEUM)_(IDLE|DEFEND|ATTACK)_V[0-9]+$"
)


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_week() -> str:
    return datetime.now(timezone.utc).strftime("%G-W%V")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _hp_tag(hp_pct: float) -> str:
    if hp_pct <= 0.25:
        return "HP020"
    if hp_pct <= 0.75:
        return "HP050"
    return "HP100"


def _sasang_upper(sasang: str) -> str:
    s = sasang.strip().lower()
    if s == "taeum":
        s = "taeeum"
    return s.upper()


def _mode_upper(mode: str) -> str:
    m = mode.strip().lower()
    if m not in ("idle", "defend", "attack"):
        return "IDLE"
    return m.upper()


def _playback_id(hp_pct: float, sasang: str, mode: str, version: int = 1) -> str:
    return f"LM_{_hp_tag(hp_pct)}_{_sasang_upper(sasang)}_{_mode_upper(mode)}_V{version}"


def _trend_gate_state(trend: dict[str, Any]) -> str:
    raw = str(trend.get("state") or "NODATA").upper()
    if raw in ("OK", "WATCH", "NODATA", "HOLD"):
        return raw
    return "NODATA"


def _pick_hp_for_mode(display_mode: str) -> float:
    m = display_mode.strip().lower()
    if m == "defend":
        return 1.0
    if m == "attack":
        return 0.5
    return 0.5


def _pick_sasang_for_mode(display_mode: str, default: str = "soyang") -> str:
    m = display_mode.strip().lower()
    if m == "attack":
        return "taeyang"
    return default


def _find_sweep_row(sweep: dict[str, Any], hp_pct: float, sasang: str) -> dict[str, Any] | None:
    rows = sweep.get("rows")
    if not isinstance(rows, list):
        return None
    best: dict[str, Any] | None = None
    best_delta = 999.0
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            row_hp = float(row.get("hp_pct"))
        except (TypeError, ValueError):
            continue
        row_sasang = str(row.get("sasang") or sweep.get("sasang") or "soyang").lower()
        if row_sasang != sasang.lower():
            continue
        delta = abs(row_hp - hp_pct)
        if delta < best_delta:
            best_delta = delta
            best = row
    return best


def _gate_from_row(row: dict[str, Any] | None, demo: dict[str, Any], trend_state: str) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    decision = "WATCH"
    run_id = ""
    if row:
        decision = str(row.get("gate_decision") or "WATCH").upper()
        metrics = row.get("gate_metrics") if isinstance(row.get("gate_metrics"), dict) else {}
        run_id = str(row.get("run_id") or "")
    elif demo.get("gate"):
        gate = demo["gate"]
        if isinstance(gate, dict):
            decision = str(gate.get("decision") or "WATCH").upper()
            metrics = gate.get("metrics") if isinstance(gate.get("metrics"), dict) else {}
            gen = demo.get("generation")
            if isinstance(gen, dict):
                run_id = str(gen.get("run_id") or "")

    if trend_state == "WATCH" and decision == "PASS":
        decision = "WATCH"
    if trend_state in ("NODATA", "HOLD") and decision == "PASS":
        decision = "WATCH"

    ref = run_id[:16] if run_id else "00000000"
    if not re.match(r"^[a-f0-9]{8,16}$", ref):
        ref = "00000000"

    return {
        "decision": decision if decision in ("PASS", "HOLD", "WATCH") else "WATCH",
        "audio_gate_report_ref": ref,
        "lens_alignment_pass": bool(metrics.get("lens_alignment_pass", False)),
        "loop_seamlessness_pass": bool(metrics.get("loop_seamlessness_pass", False)),
        "lufs_target_match": bool(metrics.get("lufs_target_match", False)),
        "commercial_license_verified": bool(metrics.get("commercial_license_verified", False)),
    }


def _resolve_lut_path(lut_path: Path | None) -> dict[str, Any]:
    if lut_path and lut_path.is_file():
        return _read_json(lut_path)
    if LUT_LATEST.is_file():
        return _read_json(LUT_LATEST)
    return _read_json(LUT_EXAMPLE)


def _ensure_lut_latest() -> dict[str, Any]:
    lut = _read_json(LUT_LATEST)
    if lut.get("schema") == "jemaai_lens_audio_playback_lut_v1":
        return lut
    lut = _read_json(LUT_EXAMPLE)
    if lut.get("schema") == "jemaai_lens_audio_playback_lut_v1":
        LUT_LATEST.parent.mkdir(parents=True, exist_ok=True)
        LUT_LATEST.write_text(json.dumps(lut, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return lut


def _pick_playback_id(
    lut: dict[str, Any],
    hp_pct: float,
    sasang: str,
    display_mode: str,
) -> str:
    entries = lut.get("entries") if isinstance(lut.get("entries"), dict) else {}
    preferred = _playback_id(hp_pct, sasang, display_mode, 1)
    if preferred in entries:
        return preferred

    hp_key = _hp_tag(hp_pct)
    sas_key = _sasang_upper(sasang)
    mode_key = _mode_upper(display_mode)
    for pid in entries:
        if pid.startswith(f"LM_{hp_key}_{sas_key}_"):
            return str(pid)

    for pid in entries:
        if _PLAYBACK_RE.match(str(pid)):
            return str(pid)

    return preferred


def build_lens_audio_observability(
    *,
    showroom_display_mode: str = "idle",
    lut_path: Path | None = None,
    sasang_primary: str | None = None,
) -> dict[str, Any]:
    trend = _read_json(TREND_PATH)
    sweep = _read_json(SWEEP_PATH)
    demo = _read_json(DEMO_PATH)
    lut = _resolve_lut_path(lut_path)
    _ensure_lut_latest()

    display_mode = showroom_display_mode.strip().lower() or "idle"
    if display_mode not in ("idle", "defend", "attack"):
        display_mode = "idle"

    default_sasang = str(sweep.get("sasang") or demo.get("inputs", {}).get("sasang") or "soyang").lower()
    if default_sasang not in _SASANG_ENUM:
        default_sasang = "soyang"

    hp_pct = _pick_hp_for_mode(display_mode)
    sasang = _pick_sasang_for_mode(display_mode, default_sasang)
    row = _find_sweep_row(sweep, hp_pct, sasang)
    if row:
        hp_pct = float(row.get("hp_pct", hp_pct))
        sasang = str(row.get("sasang") or sasang).lower()
    if sasang_primary:
        cand = sasang_primary.strip().lower()
        if cand == "taeum":
            cand = "taeeum"
        if cand in _SASANG_ENUM:
            sasang = cand

    trend_state = _trend_gate_state(trend)
    gate = _gate_from_row(row, demo, trend_state)
    playback_id = _pick_playback_id(lut, hp_pct, sasang, display_mode)
    lut_entries = lut.get("entries") if isinstance(lut.get("entries"), dict) else {}
    lut_row = lut_entries.get(playback_id) if isinstance(lut_entries.get(playback_id), dict) else {}
    if lut_row.get("gate_decision"):
        gate = {
            **gate,
            "decision": str(lut_row.get("gate_decision")).upper(),
            "source": "jemaai_lens_audio_playback_lut_v1",
        }
    lut_version = str(lut.get("version") or datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    numeric_mode = str(sweep.get("numeric_mode") or demo.get("inputs", {}).get("numeric_mode") or "melody")
    if numeric_mode not in ("melody", "bed"):
        numeric_mode = "melody"

    tempo_target = None
    bpm_observed = None
    if row:
        tempo_target = row.get("tempo_bpm_target")
        gm = row.get("gate_metrics") if isinstance(row.get("gate_metrics"), dict) else {}
        bpm_observed = gm.get("bpm_observed")
    elif isinstance(demo.get("conditioning"), dict):
        tempo_target = demo["conditioning"].get("tempo_bpm_target")
        gm = demo.get("gate", {}).get("metrics", {})
        if isinstance(gm, dict):
            bpm_observed = gm.get("bpm_observed")

    block: dict[str, Any] = {
        "schema": "public_event_lens_audio_thin_slice_v1",
        "hypothesis_class": "HYPO",
        "track_wall": "B_track_research_only",
        "non_gating": True,
        "clinical_claims": False,
        "playback_id": playback_id,
        "playback_lut_version": f"jemaai_lens_audio_playback_lut_v1@{lut_version}",
        "showroom_display_mode_bind": display_mode,
        "gate": gate,
        "conditioning_meta": {
            "hp_pct": hp_pct,
            "sasang_primary": sasang if sasang in _SASANG_ENUM else "soyang",
            "numeric_mode": numeric_mode,
        },
        "trend_meta": {
            "hormone_trend_state": trend_state,
            "gematria_trace_present": trend_state != "NODATA",
        },
        "disclaimer_ref": "jemaai_lens_audio_hypo_v1",
        "generated_at_utc": _utc_now_z(),
        "baked_asset_week": _iso_week(),
    }
    if tempo_target is not None:
        try:
            block["conditioning_meta"]["tempo_bpm_target"] = float(tempo_target)
        except (TypeError, ValueError):
            pass
    if bpm_observed is not None:
        try:
            block["conditioning_meta"]["bpm_observed"] = float(bpm_observed)
        except (TypeError, ValueError):
            block["conditioning_meta"]["bpm_observed"] = None

    return block


def build_thin_slice_doc(block: dict[str, Any], lut: dict[str, Any]) -> dict[str, Any]:
    pid = block.get("playback_id")
    entry = {}
    entries = lut.get("entries") if isinstance(lut.get("entries"), dict) else {}
    if pid in entries and isinstance(entries[pid], dict):
        entry = entries[pid]
    base = str(lut.get("assets_base_url") or "")
    file_name = str(entry.get("file") or "")
    public_url = f"{base}{file_name}" if base and file_name else None

    return {
        "schema": "showroom_lens_audio_thin_slice_v1",
        "hypothesis_tag": "[HYPO]",
        "track_wall": "B_track_research_only",
        "generated_at_utc": block.get("generated_at_utc"),
        "lens_audio_observability_v1": block,
        "playback_lut": {
            "version": lut.get("version"),
            "playback_id": pid,
            "public_asset_url": public_url,
            "entry": entry,
        },
        "boundary_note": (
            "Pre-baked static loop lookup only. Not live MusicGen. Not clinical. Not a trading signal. "
            "Logos/medical/live-trading walls remain NON_GATING / blocked."
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Build lens_audio_observability_v1 for public-event.v1")
    p.add_argument("--showroom-display-mode", default="idle", help="idle|defend|attack")
    p.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    p.add_argument("--slice-out", type=Path, default=SLICE_OUT)
    p.add_argument("--lut", type=Path, default=None)
    p.add_argument("--stdout-only", action="store_true")
    args = p.parse_args()

    block = build_lens_audio_observability(
        showroom_display_mode=args.showroom_display_mode,
        lut_path=args.lut,
    )
    lut = _ensure_lut_latest()
    slice_doc = build_thin_slice_doc(block, lut)

    if args.stdout_only:
        print(json.dumps(block, ensure_ascii=False, indent=2))
        return 0

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(block, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.slice_out.parent.mkdir(parents=True, exist_ok=True)
    args.slice_out.write_text(json.dumps(slice_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[lens-audio-obs] WROTE: {args.out_json}")
    print(f"[lens-audio-obs] WROTE: {args.slice_out}")
    print(f"[lens-audio-obs] playback_id={block.get('playback_id')} gate={block.get('gate', {}).get('decision')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
