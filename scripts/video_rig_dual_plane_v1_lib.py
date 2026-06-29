#!/usr/bin/env python3
"""Video rig dual-plane helpers — Option B hard project + TL gate (B-track [HYPO])."""

from __future__ import annotations

import copy
from typing import Any


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _vec3(row: Any) -> list[float]:
    if not isinstance(row, (list, tuple)) or len(row) != 3:
        raise ValueError("expected vec3")
    return [float(row[0]), float(row[1]), float(row[2])]


def rig_bounds(rig: dict[str, Any]) -> tuple[list[float], list[float]]:
    b = dict(rig.get("bounds") or {})
    lo = _vec3(b.get("min", [-10.0, -10.0, 0.0]))
    hi = _vec3(b.get("max", [10.0, 10.0, 10.0]))
    return lo, hi


def project_video_rig(rig: dict[str, Any]) -> dict[str, Any]:
    """Hard nearest-valid-node style repair for lightweight rig JSON (Option B)."""
    if rig.get("schema") != "mkm_video_rig_stub_v1":
        raise ValueError("expected schema mkm_video_rig_stub_v1")

    out = copy.deepcopy(rig)
    lo, hi = rig_bounds(out)
    clip_notes: list[str] = []

    for obj in out.get("objects") or []:
        if not isinstance(obj, dict):
            continue
        track = obj.get("bbox_3d_track") or []
        for row in track:
            if not isinstance(row, dict):
                continue
            center = _vec3(row.get("center", [0.0, 0.0, 0.0]))
            clipped = [
                _clamp(center[0], lo[0], hi[0]),
                _clamp(center[1], lo[1], hi[1]),
                _clamp(center[2], lo[2], hi[2]),
            ]
            if clipped != center:
                clip_notes.append(f"{obj.get('id')}:center_clipped@{row.get('t')}")
            row["center"] = clipped
            extent = row.get("extent")
            if isinstance(extent, list) and len(extent) == 3:
                row["extent"] = [
                    max(0.1, float(extent[0])),
                    max(0.1, float(extent[1])),
                    max(0.1, float(extent[2])),
                ]

    cam = dict(out.get("camera") or {})
    for row in cam.get("pose_track") or []:
        if not isinstance(row, dict):
            continue
        pos = _vec3(row.get("position", [0.0, -5.0, 1.5]))
        clipped_pos = [
            _clamp(pos[0], lo[0], hi[0]),
            _clamp(pos[1], lo[1], hi[1]),
            _clamp(pos[2], lo[2], hi[2]),
        ]
        if clipped_pos != pos:
            clip_notes.append(f"camera:position_clipped@{row.get('t')}")
        row["position"] = clipped_pos
        fov = float(row.get("fov", 60.0))
        fov_clipped = _clamp(fov, 30.0, 90.0)
        if fov_clipped != fov:
            clip_notes.append(f"camera:fov_clipped@{row.get('t')}")
        row["fov"] = fov_clipped

    out["projection_stage"] = {
        "schema": "video_rig_projection_v1",
        "policy": "hard_clamp_option_b",
        "clip_notes": clip_notes,
    }
    return out


def rig_to_event_seq(rig: dict[str, Any]) -> dict[str, Any]:
    """Flatten rig keyframes to a frame-wise event sequence for TL checks."""
    frames: list[dict[str, Any]] = []
    obj_map: dict[str, list[dict[str, Any]]] = {}
    for obj in rig.get("objects") or []:
        if isinstance(obj, dict) and obj.get("id"):
            obj_map[str(obj["id"])] = list(obj.get("bbox_3d_track") or [])

    cam_track = list((rig.get("camera") or {}).get("pose_track") or [])
    meta = dict(rig.get("meta") or {})
    total_frames = int(meta.get("total_frames") or 0)
    times = {int(row.get("t", 0)) for row in cam_track if isinstance(row, dict)}
    for tracks in obj_map.values():
        for row in tracks:
            if isinstance(row, dict):
                times.add(int(row.get("t", 0)))
    if not times and total_frames > 0:
        times = {0, total_frames}

    for t in sorted(times):
        frame: dict[str, Any] = {"t": t, "objects": {}, "camera": {}}
        for oid, tracks in obj_map.items():
            row = next((r for r in tracks if isinstance(r, dict) and int(r.get("t", -1)) == t), None)
            if row is not None:
                frame["objects"][oid] = {"center": list(row.get("center") or [0, 0, 0])}
        crow = next((r for r in cam_track if isinstance(r, dict) and int(r.get("t", -1)) == t), None)
        if crow is not None:
            frame["camera"] = {
                "position": list(crow.get("position") or [0, -5, 1.5]),
                "fov": float(crow.get("fov", 60.0)),
            }
        frames.append(frame)

    return {
        "schema": "video_event_seq_stub_v1",
        "source_rig_schema": rig.get("schema"),
        "frames": frames,
    }


def _center_in_bounds(center: list[float], lo: list[float], hi: list[float]) -> bool:
    return all(lo[i] <= center[i] <= hi[i] for i in range(3))


def _eval_rule(rule: dict[str, Any], event_seq: dict[str, Any]) -> bool:
    kind = str(rule.get("kind") or "")
    frames = list(event_seq.get("frames") or [])
    if not frames:
        return kind == "noop"

    if kind == "always_in_bounds":
        oid = str(rule.get("object_id") or "")
        lo = _vec3(rule.get("min", [-10, -10, 0]))
        hi = _vec3(rule.get("max", [10, 10, 10]))
        for fr in frames:
            obj = dict(fr.get("objects") or {}).get(oid) or {}
            center = _vec3(obj.get("center", [0, 0, 0]))
            if not _center_in_bounds(center, lo, hi):
                return True
        return False

    if kind == "camera_fov_in_range":
        fmin = float(rule.get("min", 30.0))
        fmax = float(rule.get("max", 90.0))
        for fr in frames:
            cam = dict(fr.get("camera") or {})
            fov = float(cam.get("fov", 60.0))
            if fov < fmin or fov > fmax:
                return True
        return False

    if kind == "eventually_x_gt":
        oid = str(rule.get("object_id") or "")
        threshold = float(rule.get("x_gt", 0.0))
        deadline = int(rule.get("by_frame", 10**9))
        for fr in frames:
            t = int(fr.get("t", 0))
            if t > deadline:
                break
            obj = dict(fr.get("objects") or {}).get(oid) or {}
            center = _vec3(obj.get("center", [0, 0, 0]))
            if center[0] > threshold:
                return False
        return True

    if kind == "always_z_min":
        oid = str(rule.get("object_id") or "")
        zmin = float(rule.get("z_min", 0.0))
        for fr in frames:
            obj = dict(fr.get("objects") or {}).get(oid) or {}
            center = _vec3(obj.get("center", [0, 0, 0]))
            if center[2] < zmin:
                return True
        return False

    if kind == "camera_axis_in_range":
        axis = str(rule.get("axis") or "y")
        idx = {"x": 0, "y": 1, "z": 2}.get(axis, 1)
        vmax = rule.get("max")
        vmin = rule.get("min")
        for fr in frames:
            cam = dict(fr.get("camera") or {})
            pos = _vec3(cam.get("position", [0, -5, 1.5]))
            val = pos[idx]
            if vmin is not None and val < float(vmin):
                return True
            if vmax is not None and val > float(vmax):
                return True
        return False

    if kind == "monotonic_x_non_decreasing":
        oid = str(rule.get("object_id") or "")
        last_x: float | None = None
        for fr in frames:
            obj = dict(fr.get("objects") or {}).get(oid) or {}
            x = _vec3(obj.get("center", [0, 0, 0]))[0]
            if last_x is not None and x + 1e-9 < last_x:
                return True
            last_x = x
        return False

    raise ValueError(f"unknown tl rule kind: {kind}")


def evaluate_video_temporal_logic(
    event_seq: dict[str, Any],
    tl_spec: dict[str, Any],
) -> dict[str, Any]:
    """Return per-rule violations; dual metrics computed by caller."""
    rules = list(tl_spec.get("rules") or [])
    violations: list[dict[str, Any]] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        violated = _eval_rule(rule, event_seq)
        violations.append(
            {
                "id": str(rule.get("id") or ""),
                "kind": str(rule.get("kind") or ""),
                "violated": violated,
            }
        )
    total = len(violations)
    count = sum(1 for v in violations if v["violated"])
    rate = count / total if total else 0.0
    return {
        "schema": "video_tl_eval_v1",
        "rule_count": total,
        "violation_count": count,
        "violation_rate": round(rate, 4),
        "violations": violations,
        "collapsed_combined_score": None,
    }


def evaluate_dual_plane_tl_gate(
    *,
    raw_rig: dict[str, Any],
    tl_spec: dict[str, Any],
) -> dict[str, Any]:
    projected = project_video_rig(raw_rig)
    raw_eval = evaluate_video_temporal_logic(rig_to_event_seq(raw_rig), tl_spec)
    post_eval = evaluate_video_temporal_logic(rig_to_event_seq(projected), tl_spec)
    return {
        "schema": "video_tl_gate_report_v1",
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "raw": raw_eval,
        "post_project": post_eval,
        "delta_post_minus_raw_violation_rate": round(
            post_eval["violation_rate"] - raw_eval["violation_rate"], 4
        ),
        "collapsed_combined_score": None,
        "projected_rig": projected,
    }
