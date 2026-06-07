#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate showroom_public_bundle_v1.json — structure + public redaction (no wallet fields)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

REQUIRED_EVENT_KEYS: List[str] = [
    "timestamp",
    "active_character_id",
    "risk_level",
    "public_signal_direction",
    "abstract_reason",
    "schema_version",
    "event_id",
    "source",
]

FORBIDDEN_SUBSTRINGS: List[str] = [
    "balance_total_usdt",
    "balance_available",
    "api_key",
    "secret",
    "private_key",
]

LOGOS_GRAPH_META_ALLOWED_KEYS: Set[str] = {
    "present",
    "schema",
    "hypothesis_tier",
    "source_schema",
    "dedupe_bundle_key_sha256",
    "ts_utc",
    "nodes_line_count",
    "edges_line_count",
}

LOGOS_GRAPH_META_FORBIDDEN_KEYS: Set[str] = {
    "rationale",
    "notes",
    "nodes",
    "edges",
    "manifest_snapshot",
    "graph_files",
    "alignment",
}

_TS_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_SHOWROOM_DISPLAY_MODES = frozenset({"idle", "defend", "attack"})
_SHOWROOM_TICKER_KEY_RE = re.compile(r"^[A-Z0-9_]{1,64}$")
_SHOWROOM_REACTION_ID_RE = re.compile(r"^R_[A-Z0-9_]{1,32}$")
_PLAYBACK_ID_RE = re.compile(
    r"^LM_HP(020|050|100)_(SOYANG|TAEYANG|TAEEUM|SOEUM)_(IDLE|DEFEND|ATTACK)_V[0-9]+$"
)
_VIDEO_PLAYBACK_ID_RE = re.compile(
    r"^LV_HP(020|050|100)_(SOYANG|TAEYANG|TAEEUM|SOEUM)_(IDLE|DEFEND|ATTACK)_V[0-9]+$"
)
_LENS_AUDIO_FORBIDDEN_SUBSTRINGS: List[str] = [
    "musicgen",
    "suno",
    "workspace/",
    "c:/",
    "soap",
    "cdss",
    "live_generation",
    "run_id",
]


def _flatten_strings(obj: Any, out: List[str]) -> None:
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _flatten_strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _flatten_strings(v, out)


def _collect_keys(obj: Any, prefix: str, keys: Set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(f"{prefix}.{k}" if prefix else k)
            _collect_keys(v, f"{prefix}.{k}" if prefix else k, keys)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _collect_keys(v, f"{prefix}[{i}]", keys)


_TOPOLOGY_RADAR_OBS_KEYS = frozenset(
    {
        "topology_radar_snapshot_present",
        "topology_radar_snapshot_generated_at_utc",
        "topology_radar_snapshot_stale_after_utc",
        "topology_radar_snapshot_hypo_banner",
        "topology_radar_snapshot_artifact_ref_count",
        "topology_radar_snapshot_no_trade_signals",
        "topology_radar_snapshot_disclaimer_ref",
        "topology_radar_snapshot_stub",
    }
)


def _validate_topology_radar_fields(obs: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    keys = [k for k in obs if isinstance(k, str) and k.startswith("topology_radar_snapshot_")]
    if not keys:
        return errs
    for k in keys:
        if k not in _TOPOLOGY_RADAR_OBS_KEYS:
            errs.append(f"observability unknown topology key: {k}")
    present = obs.get("topology_radar_snapshot_present")
    if present is None:
        errs.append("topology_radar_snapshot_* set but topology_radar_snapshot_present is missing")
        return errs
    if present is False:
        for k in keys:
            if k != "topology_radar_snapshot_present":
                errs.append(f"observability.{k} must not be set when topology_radar_snapshot_present is false")
        return errs
    if present is not True:
        errs.append("observability.topology_radar_snapshot_present must be boolean")
        return errs

    gen = obs.get("topology_radar_snapshot_generated_at_utc")
    if not isinstance(gen, str) or not _TS_UTC_RE.match(gen):
        errs.append(
            "observability.topology_radar_snapshot_generated_at_utc must match YYYY-MM-DDTHH:MM:SSZ when present=true"
        )
    stale = obs.get("topology_radar_snapshot_stale_after_utc")
    if not isinstance(stale, str) or not _TS_UTC_RE.match(stale):
        errs.append(
            "observability.topology_radar_snapshot_stale_after_utc must match YYYY-MM-DDTHH:MM:SSZ when present=true"
        )
    hypo = obs.get("topology_radar_snapshot_hypo_banner")
    if not isinstance(hypo, str) or len(hypo) < 8:
        errs.append("observability.topology_radar_snapshot_hypo_banner must be a non-trivial string when present=true")
    elif not hypo.lstrip().upper().startswith("[HYPO]"):
        errs.append("observability.topology_radar_snapshot_hypo_banner must start with [HYPO]")
    elif len(hypo) > 512:
        errs.append("observability.topology_radar_snapshot_hypo_banner max length 512")

    arc = obs.get("topology_radar_snapshot_artifact_ref_count")
    if not isinstance(arc, int) or arc < 1 or arc > 32:
        errs.append("observability.topology_radar_snapshot_artifact_ref_count must be int 1..32 when present=true")

    if obs.get("topology_radar_snapshot_no_trade_signals") is not True:
        errs.append("observability.topology_radar_snapshot_no_trade_signals must be true when present=true")

    disc = obs.get("topology_radar_snapshot_disclaimer_ref")
    if disc != "jemaai_showroom_v1":
        errs.append("observability.topology_radar_snapshot_disclaimer_ref must be jemaai_showroom_v1 when present=true")

    stub = obs.get("topology_radar_snapshot_stub")
    if stub is not None and not isinstance(stub, bool):
        errs.append("observability.topology_radar_snapshot_stub must be boolean if set")

    return errs


_MACRO_HORIZON_OBS_KEYS = frozenset(
    {
        "macro_horizon_2030_snapshot_present",
        "macro_horizon_2030_snapshot_generated_at_utc",
        "macro_horizon_2030_snapshot_stale_after_utc",
        "macro_horizon_2030_snapshot_hypo_banner",
        "macro_horizon_2030_snapshot_final_action",
        "macro_horizon_2030_snapshot_btc_base_weight",
        "macro_horizon_2030_snapshot_btc_stress_weight",
        "macro_horizon_2030_snapshot_no_trade_signals",
        "macro_horizon_2030_snapshot_disclaimer_ref",
    }
)


def _validate_macro_horizon_2030_fields(obs: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    keys = [k for k in obs if isinstance(k, str) and k.startswith("macro_horizon_2030_snapshot_")]
    if not keys:
        return errs
    for k in keys:
        if k not in _MACRO_HORIZON_OBS_KEYS:
            errs.append(f"observability unknown macro horizon key: {k}")
    present = obs.get("macro_horizon_2030_snapshot_present")
    if present is None:
        errs.append("macro_horizon_2030_snapshot_* set but macro_horizon_2030_snapshot_present is missing")
        return errs
    if present is False:
        for k in keys:
            if k != "macro_horizon_2030_snapshot_present":
                errs.append(f"observability.{k} must not be set when macro_horizon_2030_snapshot_present is false")
        return errs
    if present is not True:
        errs.append("observability.macro_horizon_2030_snapshot_present must be boolean")
        return errs

    gen = obs.get("macro_horizon_2030_snapshot_generated_at_utc")
    if not isinstance(gen, str) or not _TS_UTC_RE.match(gen):
        errs.append(
            "observability.macro_horizon_2030_snapshot_generated_at_utc must match YYYY-MM-DDTHH:MM:SSZ when present=true"
        )
    stale = obs.get("macro_horizon_2030_snapshot_stale_after_utc")
    if not isinstance(stale, str) or not _TS_UTC_RE.match(stale):
        errs.append(
            "observability.macro_horizon_2030_snapshot_stale_after_utc must match YYYY-MM-DDTHH:MM:SSZ when present=true"
        )
    hypo = obs.get("macro_horizon_2030_snapshot_hypo_banner")
    if not isinstance(hypo, str) or len(hypo) < 8:
        errs.append("observability.macro_horizon_2030_snapshot_hypo_banner must be a non-trivial string when present=true")
    elif not hypo.lstrip().upper().startswith("[HYPO]"):
        errs.append("observability.macro_horizon_2030_snapshot_hypo_banner must start with [HYPO]")
    elif len(hypo) > 512:
        errs.append("observability.macro_horizon_2030_snapshot_hypo_banner max length 512")

    final_action = obs.get("macro_horizon_2030_snapshot_final_action")
    if not isinstance(final_action, str) or not final_action.strip():
        errs.append("observability.macro_horizon_2030_snapshot_final_action must be a non-empty string when present=true")

    base_w = obs.get("macro_horizon_2030_snapshot_btc_base_weight")
    stress_w = obs.get("macro_horizon_2030_snapshot_btc_stress_weight")
    if not isinstance(base_w, (int, float)) or base_w < 0 or base_w > 1:
        errs.append("observability.macro_horizon_2030_snapshot_btc_base_weight must be number 0..1 when present=true")
    if not isinstance(stress_w, (int, float)) or stress_w < 0 or stress_w > 1:
        errs.append("observability.macro_horizon_2030_snapshot_btc_stress_weight must be number 0..1 when present=true")

    if obs.get("macro_horizon_2030_snapshot_no_trade_signals") is not True:
        errs.append("observability.macro_horizon_2030_snapshot_no_trade_signals must be true when present=true")

    disc = obs.get("macro_horizon_2030_snapshot_disclaimer_ref")
    if disc != "jemaai_showroom_v1":
        errs.append("observability.macro_horizon_2030_snapshot_disclaimer_ref must be jemaai_showroom_v1 when present=true")

    return errs


def _validate_lens_audio_observability_v1(block: Any, parent_sdm: Any) -> List[str]:
    errs: List[str] = []
    if block is None:
        return errs
    if not isinstance(block, dict):
        errs.append("public_event_v1.lens_audio_observability_v1 must be an object if present")
        return errs

    if block.get("schema") != "public_event_lens_audio_thin_slice_v1":
        errs.append("lens_audio_observability_v1.schema must be public_event_lens_audio_thin_slice_v1")
    if block.get("hypothesis_class") != "HYPO":
        errs.append("lens_audio_observability_v1.hypothesis_class must be HYPO")
    if block.get("track_wall") != "B_track_research_only":
        errs.append("lens_audio_observability_v1.track_wall must be B_track_research_only")
    if block.get("non_gating") is not True:
        errs.append("lens_audio_observability_v1.non_gating must be true")
    if block.get("clinical_claims") is not False:
        errs.append("lens_audio_observability_v1.clinical_claims must be false")
    if block.get("disclaimer_ref") != "jemaai_lens_audio_hypo_v1":
        errs.append("lens_audio_observability_v1.disclaimer_ref must be jemaai_lens_audio_hypo_v1")

    pid = block.get("playback_id")
    if not isinstance(pid, str) or not _PLAYBACK_ID_RE.match(pid):
        errs.append(
            "lens_audio_observability_v1.playback_id must match "
            "^LM_HP(020|050|100)_(SOYANG|TAEYANG|TAEEUM|SOEUM)_(IDLE|DEFEND|ATTACK)_V[0-9]+$"
        )

    plv = block.get("playback_lut_version")
    if not isinstance(plv, str) or not plv.startswith("jemaai_lens_audio_playback_lut_v1@"):
        errs.append("lens_audio_observability_v1.playback_lut_version must start with jemaai_lens_audio_playback_lut_v1@")

    gate = block.get("gate")
    if not isinstance(gate, dict):
        errs.append("lens_audio_observability_v1.gate must be an object")
    else:
        decision = gate.get("decision")
        if decision not in ("PASS", "HOLD", "WATCH"):
            errs.append("lens_audio_observability_v1.gate.decision must be PASS|HOLD|WATCH")
        for bk in (
            "lens_alignment_pass",
            "loop_seamlessness_pass",
            "lufs_target_match",
            "commercial_license_verified",
        ):
            if bk not in gate or not isinstance(gate[bk], bool):
                errs.append(f"lens_audio_observability_v1.gate.{bk} must be boolean")

    bind = block.get("showroom_display_mode_bind")
    if bind is not None:
        if not isinstance(bind, str) or bind.lower() not in _SHOWROOM_DISPLAY_MODES:
            errs.append("lens_audio_observability_v1.showroom_display_mode_bind must be idle|defend|attack if present")
        elif parent_sdm is not None and isinstance(parent_sdm, str) and bind.lower() != parent_sdm.lower():
            errs.append(
                "lens_audio_observability_v1.showroom_display_mode_bind must match public_event_v1.showroom_display_mode when both set"
            )

    value_strings: List[str] = []

    def _walk_lens_values(obj: Any, key: str | None = None) -> None:
        if key == "clinical_claims":
            return
        if isinstance(obj, str):
            value_strings.append(obj)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                _walk_lens_values(v, k)
        elif isinstance(obj, list):
            for v in obj:
                _walk_lens_values(v, key)

    _walk_lens_values(block)
    block_text = " ".join(value_strings).lower()
    for bad in _LENS_AUDIO_FORBIDDEN_SUBSTRINGS + FORBIDDEN_SUBSTRINGS:
        if bad in block_text:
            errs.append(f"lens_audio_observability_v1 contains forbidden token: {bad}")

    return errs


def _validate_lens_video_observability_v1(block: Any, parent_sdm: Any, audio_block: Any) -> List[str]:
    errs: List[str] = []
    if block is None:
        return errs
    if not isinstance(block, dict):
        errs.append("public_event_v1.lens_video_observability_v1 must be an object if present")
        return errs

    if block.get("schema") != "public_event_lens_video_thin_slice_v1":
        errs.append("lens_video_observability_v1.schema must be public_event_lens_video_thin_slice_v1")
    if block.get("hypothesis_class") != "HYPO":
        errs.append("lens_video_observability_v1.hypothesis_class must be HYPO")
    if block.get("track_wall") != "B_track_research_only":
        errs.append("lens_video_observability_v1.track_wall must be B_track_research_only")
    if block.get("non_gating") is not True:
        errs.append("lens_video_observability_v1.non_gating must be true")
    if block.get("clinical_claims") is not False:
        errs.append("lens_video_observability_v1.clinical_claims must be false")
    if block.get("disclaimer_ref") != "jemaai_lens_video_hypo_v1":
        errs.append("lens_video_observability_v1.disclaimer_ref must be jemaai_lens_video_hypo_v1")

    vpid = block.get("video_playback_id")
    if not isinstance(vpid, str) or not _VIDEO_PLAYBACK_ID_RE.match(vpid):
        errs.append(
            "lens_video_observability_v1.video_playback_id must match "
            "^LV_HP(020|050|100)_(SOYANG|TAEYANG|TAEEUM|SOEUM)_(IDLE|DEFEND|ATTACK)_V[0-9]+$"
        )

    plv = block.get("playback_lut_version")
    if not isinstance(plv, str) or not plv.startswith("jemaai_lens_video_playback_lut_v1@"):
        errs.append("lens_video_observability_v1.playback_lut_version must start with jemaai_lens_video_playback_lut_v1@")

    mirror = block.get("audio_playback_id_mirror")
    if isinstance(audio_block, dict) and audio_block.get("playback_id"):
        if mirror != audio_block.get("playback_id"):
            errs.append("lens_video_observability_v1.audio_playback_id_mirror must match lens_audio playback_id")

    gate = block.get("gate")
    if not isinstance(gate, dict):
        errs.append("lens_video_observability_v1.gate must be an object")
    else:
        decision = gate.get("decision")
        if decision not in ("PASS", "HOLD", "WATCH"):
            errs.append("lens_video_observability_v1.gate.decision must be PASS|HOLD|WATCH")
        for bk in ("loop_seamlessness_pass", "visual_alignment_pass", "commercial_license_verified"):
            if bk not in gate or not isinstance(gate[bk], bool):
                errs.append(f"lens_video_observability_v1.gate.{bk} must be boolean")

    bind = block.get("showroom_display_mode_bind")
    if bind is not None:
        if not isinstance(bind, str) or bind.lower() not in _SHOWROOM_DISPLAY_MODES:
            errs.append("lens_video_observability_v1.showroom_display_mode_bind must be idle|defend|attack if present")
        elif parent_sdm is not None and isinstance(parent_sdm, str) and bind.lower() != parent_sdm.lower():
            errs.append(
                "lens_video_observability_v1.showroom_display_mode_bind must match public_event_v1.showroom_display_mode when both set"
            )

    return errs


def _validate_logos_graph_meta(meta: Any, prefix: str) -> List[str]:
    errs: List[str] = []
    if meta is None:
        return errs
    if not isinstance(meta, dict):
        errs.append(f"{prefix} must be an object")
        return errs
    for fk in LOGOS_GRAPH_META_FORBIDDEN_KEYS:
        if fk in meta:
            errs.append(f"{prefix} forbidden key: {fk}")
    for k in meta:
        if k not in LOGOS_GRAPH_META_ALLOWED_KEYS:
            errs.append(f"{prefix} unknown key: {k}")
    for k, v in meta.items():
        if isinstance(v, (dict, list)):
            errs.append(f"{prefix}.{k} must not be nested object or array")
            continue
        if isinstance(v, str) and len(v) > 256:
            errs.append(f"{prefix}.{k} string too long (max 256)")
        if isinstance(v, str):
            low = v.lower()
            for bad in FORBIDDEN_SUBSTRINGS:
                if bad in low:
                    errs.append(f"{prefix}.{k} contains forbidden token: {bad}")
    present = meta.get("present")
    if present is True:
        d = meta.get("dedupe_bundle_key_sha256")
        if not isinstance(d, str) or not _SHA256_RE.match(d):
            errs.append(f"{prefix}.dedupe_bundle_key_sha256 must be 64 lowercase hex when present=true")
        ts = meta.get("ts_utc")
        if ts is not None and (not isinstance(ts, str) or not _TS_UTC_RE.match(ts)):
            errs.append(f"{prefix}.ts_utc must match YYYY-MM-DDTHH:MM:SSZ when present")
        for nk in ("nodes_line_count", "edges_line_count"):
            val = meta.get(nk)
            if val is not None and (not isinstance(val, int) or val < 0):
                errs.append(f"{prefix}.{nk} must be non-negative int if present")
    elif present is not False and present is not None:
        errs.append(f"{prefix}.present must be boolean if set")
    return errs


def validate_bundle(path: Path) -> List[str]:
    errors: List[str] = []
    raw = path.read_text(encoding="utf-8-sig")
    doc = json.loads(raw)
    if doc.get("schema") != "showroom_public_bundle_v1":
        errors.append("schema must be showroom_public_bundle_v1")

    obs = doc.get("observability")
    if isinstance(obs, dict):
        errors.extend(_validate_topology_radar_fields(obs))
        errors.extend(_validate_macro_horizon_2030_fields(obs))
        if "logos_graph_meta" in obs:
            errors.extend(_validate_logos_graph_meta(obs.get("logos_graph_meta"), "observability.logos_graph_meta"))
            if obs.get("track_b_non_gating") is not True:
                errors.append("observability.track_b_non_gating must be true when logos_graph_meta is present")
        fst = obs.get("logos_freshness_staleness_seconds")
        if fst is not None and (not isinstance(fst, int) or fst < 0):
            errors.append("observability.logos_freshness_staleness_seconds must be non-negative int if present")
        fgen = obs.get("logos_freshness_generated_at_utc")
        if fgen is not None and (not isinstance(fgen, str) or not _TS_UTC_RE.match(fgen)):
            errors.append("observability.logos_freshness_generated_at_utc must match YYYY-MM-DDTHH:MM:SSZ if present")
        obs_text = json.dumps(obs, ensure_ascii=False).lower()
        for bad in FORBIDDEN_SUBSTRINGS:
            if bad in obs_text:
                errors.append(f"observability contains forbidden token: {bad}")

    pub = doc.get("public_event_v1")
    if not isinstance(pub, dict):
        errors.append("public_event_v1 must be an object")
        return errors

    for k in REQUIRED_EVENT_KEYS:
        if k not in pub:
            errors.append(f"public_event_v1 missing required key: {k}")

    if pub.get("schema_version") != "public-event.v1":
        errors.append("public_event_v1.schema_version must be public-event.v1")

    if pub.get("disclaimer_ref") != "jemaai_showroom_v1":
        errors.append("public_event_v1.disclaimer_ref must be jemaai_showroom_v1")

    sdm = pub.get("showroom_display_mode")
    if sdm is not None:
        if not isinstance(sdm, str) or str(sdm).lower() not in _SHOWROOM_DISPLAY_MODES:
            errors.append("public_event_v1.showroom_display_mode must be idle|defend|attack if present")

    stk = pub.get("showroom_ticker_key")
    if stk is not None:
        if not isinstance(stk, str) or not _SHOWROOM_TICKER_KEY_RE.match(stk):
            errors.append("public_event_v1.showroom_ticker_key must match ^[A-Z0-9_]{1,64}$ if present")

    srids = pub.get("showroom_reaction_line_ids")
    if srids is not None:
        if not isinstance(srids, list):
            errors.append("public_event_v1.showroom_reaction_line_ids must be an array if present")
        elif len(srids) > 3:
            errors.append("public_event_v1.showroom_reaction_line_ids max length is 3")
        else:
            for i, rid in enumerate(srids):
                if not isinstance(rid, str) or not _SHOWROOM_REACTION_ID_RE.match(rid):
                    errors.append(
                        f"public_event_v1.showroom_reaction_line_ids[{i}] must match ^R_[A-Z0-9_]{{1,32}}$"
                    )

    errors.extend(_validate_lens_audio_observability_v1(pub.get("lens_audio_observability_v1"), sdm))
    errors.extend(
        _validate_lens_video_observability_v1(
            pub.get("lens_video_observability_v1"), sdm, pub.get("lens_audio_observability_v1")
        )
    )

    dm = pub.get("delayed_metrics")
    if isinstance(dm, dict):
        ds = dm.get("delay_seconds")
        if ds is not None and not isinstance(ds, int):
            errors.append("delayed_metrics.delay_seconds must be int if present")
        if "pnl_pct_vs_start" in dm and dm["pnl_pct_vs_start"] is not None:
            p = dm["pnl_pct_vs_start"]
            if not isinstance(p, (int, float)):
                errors.append("delayed_metrics.pnl_pct_vs_start must be numeric if present")
        lx = dm.get("logos_x_index_0_100")
        if lx is not None and (not isinstance(lx, int) or lx < 0 or lx > 100):
            errors.append("delayed_metrics.logos_x_index_0_100 must be int 0..100 if present")
        lb = dm.get("logos_x_band")
        if lb is not None and str(lb) not in ("LOW", "MID", "HIGH"):
            errors.append("delayed_metrics.logos_x_band must be LOW|MID|HIGH if present")
        lq = dm.get("logos_quadrant")
        if lq is not None and str(lq) not in ("Q1", "Q2", "Q3", "Q4"):
            errors.append("delayed_metrics.logos_quadrant must be Q1|Q2|Q3|Q4 if present")

        lgp = dm.get("logos_graph_bundle_present")
        if lgp is not None and not isinstance(lgp, bool):
            errors.append("delayed_metrics.logos_graph_bundle_present must be bool if present")
        if lgp is True:
            dsha = dm.get("logos_graph_bundle_dedupe_sha256")
            if dsha is not None:
                if not isinstance(dsha, str) or not _SHA256_RE.match(dsha):
                    errors.append(
                        "delayed_metrics.logos_graph_bundle_dedupe_sha256 must be 64 lowercase hex if present"
                    )
            tsb = dm.get("logos_graph_bundle_ts_utc")
            if tsb is not None and (not isinstance(tsb, str) or not _TS_UTC_RE.match(tsb)):
                errors.append("delayed_metrics.logos_graph_bundle_ts_utc must match YYYY-MM-DDTHH:MM:SSZ if present")
            for nk in ("logos_graph_nodes_line_count", "logos_graph_edges_line_count"):
                v = dm.get(nk)
                if v is not None and (not isinstance(v, int) or v < 0):
                    errors.append(f"delayed_metrics.{nk} must be non-negative int if present")

        st = dm.get("logos_graph_staleness_seconds")
        if st is not None and (not isinstance(st, int) or st < 0):
            errors.append("delayed_metrics.logos_graph_staleness_seconds must be non-negative int if present")
        lfg = dm.get("logos_freshness_sidecar_generated_at_utc")
        if lfg is not None and (not isinstance(lfg, str) or not _TS_UTC_RE.match(lfg)):
            errors.append(
                "delayed_metrics.logos_freshness_sidecar_generated_at_utc must match YYYY-MM-DDTHH:MM:SSZ if present"
            )

    obs2 = doc.get("observability")
    if isinstance(obs2, dict) and isinstance(pub, dict):
        lg_meta = obs2.get("logos_graph_meta")
        dm2 = pub.get("delayed_metrics")
        if isinstance(lg_meta, dict) and isinstance(dm2, dict):
            om = lg_meta.get("present")
            dm_p = dm2.get("logos_graph_bundle_present")
            if om is not None and dm_p is not None and bool(om) != bool(dm_p):
                errors.append(
                    "observability.logos_graph_meta.present and delayed_metrics.logos_graph_bundle_present must agree"
                )

    # Redaction: no obvious wallet leakage in public_event_v1 JSON text
    pub_text = json.dumps(pub, ensure_ascii=False)
    lower = pub_text.lower()
    for bad in FORBIDDEN_SUBSTRINGS:
        if bad in lower:
            errors.append(f"public_event_v1 contains forbidden token: {bad}")

    strings: List[str] = []
    _flatten_strings(pub, strings)
    for s in strings:
        if re.search(r"\b1[0-9]{3}\.[0-9]{4,}\b", s):
            errors.append("public_event_v1 may contain large decimal resembling balance (redaction)")

    keys: Set[str] = set()
    _collect_keys(pub, "", keys)
    forbidden_key_fragments = ("balance", "position_size", "unrealized", "available_usdt")
    for fk in forbidden_key_fragments:
        if any(fk in k.lower() for k in keys):
            errors.append(f"public_event_v1 must not expose key containing: {fk}")

    pui = doc.get("public_ui")
    if pui is not None:
        if not isinstance(pui, dict):
            errors.append("public_ui must be an object if present")
        else:
            if pui.get("schema") != "showroom_public_ui_v1":
                errors.append("public_ui.schema must be showroom_public_ui_v1")
            pui_text = json.dumps(pui, ensure_ascii=False).lower()
            for bad in FORBIDDEN_SUBSTRINGS:
                if bad in pui_text:
                    errors.append(f"public_ui contains forbidden token: {bad}")

    return errors


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "path",
        nargs="?",
        default="docs/final/artifacts/showroom_public_bundle_v1.json",
        help="Path to showroom_public_bundle_v1.json",
    )
    args = p.parse_args()
    path = Path(args.path)
    if not path.is_file():
        print(f"[validate-showroom] FAIL: file not found: {path}", file=sys.stderr)
        return 2
    errs = validate_bundle(path)
    if errs:
        for e in errs:
            print(f"[validate-showroom] FAIL: {e}", file=sys.stderr)
        return 1
    print(f"[validate-showroom] OK: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
