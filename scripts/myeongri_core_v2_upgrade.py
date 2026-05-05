#!/usr/bin/env python3
"""MKM Myeongri core v2 upgrade skeleton (Fact-Lock safe)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROBE_16_STATE_PATH = ROOT / "data" / "myeongni" / "16_STATE_MASTER_PROBE_v1.json"
DEFAULT_IN = ROOT / "reports" / "commander_myeongni_lens_latest.json"
DEFAULT_OUT = ROOT / "reports" / "myeongri_core_v2_upgrade_latest.json"
DEFAULT_SCHEMA = ROOT / "docs" / "final" / "artifacts" / "schemas" / "myeongri_core_v2_upgrade_v1.schema.json"

GAN_TO_ELEMENT = {
    "갑": "wood",
    "을": "wood",
    "병": "fire",
    "정": "fire",
    "무": "earth",
    "기": "earth",
    "경": "metal",
    "신": "metal",
    "임": "water",
    "계": "water",
}

PILLAR_WEIGHT = {"year": 0.20, "month": 0.30, "day": 0.30, "hour": 0.20}
HIDDEN_ORDER_WEIGHT = [0.60, 0.30, 0.10]

B_TRACK_NOTICE = (
    "[MKM-B-TRACK-NOTICE] These Myeongri metrics are [HYPOTHESIS] overlays derived from traditional "
    "structure heuristics; they are not market price, fill, or liquidity facts. They must not drive "
    "live kill-switches or direction; use only as operator-side observation and optional size-only "
    "advisory where explicitly gated."
)

# 地支六冲 (unordered pairs, 한글 지지)
_JI_CHONG = frozenset(
    {
        frozenset({"자", "오"}),
        frozenset({"축", "미"}),
        frozenset({"인", "신"}),
        frozenset({"묘", "유"}),
        frozenset({"진", "술"}),
        frozenset({"사", "해"}),
    }
)
# 地支六合
_JI_LIUHE = frozenset(
    {
        frozenset({"자", "축"}),
        frozenset({"인", "해"}),
        frozenset({"묘", "술"}),
        frozenset({"진", "유"}),
        frozenset({"사", "신"}),
        frozenset({"오", "미"}),
    }
)
# 天干五合 (한글 간)
_STEM_HE = frozenset(
    {
        frozenset({"갑", "기"}),
        frozenset({"을", "경"}),
        frozenset({"병", "신"}),
        frozenset({"정", "임"}),
        frozenset({"무", "계"}),
    }
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _extract_hidden_gans(doc: dict[str, Any]) -> dict[str, list[str]]:
    adv = doc.get("advanced") if isinstance(doc.get("advanced"), dict) else {}
    slots = adv.get("slots") if isinstance(adv.get("slots"), dict) else {}
    sij = slots.get("sajeong_interpolation")
    sij = sij if isinstance(sij, dict) else {}
    if not sij:
        ins = adv.get("input_summary") if isinstance(adv.get("input_summary"), dict) else {}
        sij = ins.get("sajeong_interpolation")
        sij = sij if isinstance(sij, dict) else {}
    out: dict[str, list[str]] = {}
    for k in ("year", "month", "day", "hour"):
        item = sij.get(k) if isinstance(sij.get(k), dict) else {}
        gans = item.get("hidden_gans")
        out[k] = [str(x) for x in gans] if isinstance(gans, list) else []
    return out


def _pillar_gan_ji(pillar: str) -> tuple[str, str]:
    s = str(pillar).strip()
    if len(s) >= 2:
        return s[0], s[1]
    return "", ""


def _structural_tension_v1(pillars: dict[str, str]) -> tuple[float, str]:
    """Neutral B-track score from stem/stem five-he and branch chong/liuhe counts."""
    order = ("year", "month", "day", "hour")
    gans: list[str] = []
    jis: list[str] = []
    for k in order:
        gan, ji = _pillar_gan_ji(str(pillars.get(k, "") or ""))
        if gan:
            gans.append(gan)
        if ji:
            jis.append(ji)
    n_chong = 0
    n_lh = 0
    for i in range(len(jis)):
        for j in range(i + 1, len(jis)):
            pair = frozenset({jis[i], jis[j]})
            if pair in _JI_CHONG:
                n_chong += 1
            if pair in _JI_LIUHE:
                n_lh += 1
    n_stem_he = 0
    for i in range(len(gans)):
        for j in range(i + 1, len(gans)):
            if frozenset({gans[i], gans[j]}) in _STEM_HE:
                n_stem_he += 1
    raw = 0.48 + 0.14 * float(n_chong) - 0.11 * float(n_lh) - 0.07 * float(n_stem_he)
    return round(_clamp(raw, 0.0, 1.0), 6), (
        "branch_chong_liuhe_counts + stem_wuhe_counts on surface gan/ji from commander pillars; "
        "B-track neutral only."
    )


def _latent_energy_vector_4d(elements: dict[str, float]) -> tuple[list[float], list[str], str]:
    """Four-vector mnemonic: [wood, fire, earth, metal+water] renormalized — not MKM seed S,L,K,M."""
    w = float(elements.get("wood", 0.0) or 0.0)
    f = float(elements.get("fire", 0.0) or 0.0)
    e = float(elements.get("earth", 0.0) or 0.0)
    m = float(elements.get("metal", 0.0) or 0.0)
    wa = float(elements.get("water", 0.0) or 0.0)
    fourth = m + wa
    tot = w + f + e + fourth
    if tot <= 0:
        return [0.25, 0.25, 0.25, 0.25], ["S_proxy", "L_proxy", "K_proxy", "M_proxy"], (
            "Equal fallback; do not equate with MKM 4D seed axes."
        )
    vec = [w / tot, f / tot, e / tot, fourth / tot]
    return [round(x, 6) for x in vec], ["S_proxy", "L_proxy", "K_proxy", "M_proxy"], (
        "Projection of normalized five-element jijangan blend into four slots (metal+water merged); "
        "mnemonic S/L/K/M labels are not MKM commercial 4D seed semantics."
    )


def _shinsal_detection_logs(
    pillars: dict[str, str], detected: list[dict[str, Any]]
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for d in detected:
        if not isinstance(d, dict):
            continue
        rid = str(d.get("id", "") or "")
        pillar_key = ""
        pillar_text = ""
        if rid == "gwaegang_like":
            pillar_key, pillar_text = "day", str(pillars.get("day", "") or "")
        elif rid == "baekho_like":
            pillar_key, pillar_text = "year", str(pillars.get("year", "") or "")
        entries.append(
            {
                "id": rid,
                "pillar_key": pillar_key,
                "pillar_text": pillar_text,
                "evidence_tag": str(d.get("evidence_tag", "") or ""),
            }
        )
    return {"schema": "shinsal_detection_logs_v1", "entries": entries}


def _calc_jijangan_vector(hidden: dict[str, list[str]]) -> dict[str, float]:
    element_score = {"wood": 0.0, "fire": 0.0, "earth": 0.0, "metal": 0.0, "water": 0.0}
    for pillar, gans in hidden.items():
        p_w = PILLAR_WEIGHT.get(pillar, 0.0)
        for idx, gan in enumerate(gans[: len(HIDDEN_ORDER_WEIGHT)]):
            h_w = HIDDEN_ORDER_WEIGHT[idx]
            elem = GAN_TO_ELEMENT.get(gan)
            if not elem:
                continue
            element_score[elem] += p_w * h_w
    total = sum(element_score.values())
    if total <= 0:
        return {k: 0.0 for k in element_score}
    return {k: round(v / total, 6) for k, v in element_score.items()}


def _detect_shinsal_candidates(pillars: dict[str, str]) -> list[dict[str, Any]]:
    # Research-only deterministic candidates (small subset only).
    rules = [
        {
            "id": "gwaegang_like",
            "evidence_tag": "day_pillar_exact_match",
            "trigger": pillars.get("day") == "경진",
            "effect": {"confidence_multiplier": 1.08, "size_cap_delta": 0.03},
            "note": "Research-only candidate from exact day pillar match.",
        },
        {
            "id": "baekho_like",
            "evidence_tag": "year_pillar_exact_match",
            "trigger": pillars.get("year") == "계축",
            "effect": {"confidence_multiplier": 0.97, "size_cap_delta": -0.04},
            "note": "Research-only candidate from exact year pillar match.",
        },
    ]
    detected: list[dict[str, Any]] = []
    for r in rules:
        if r["trigger"]:
            detected.append(
                {
                    "id": r["id"],
                    "evidence_tag": r["evidence_tag"],
                    "confidence_multiplier": r["effect"]["confidence_multiplier"],
                    "size_cap_delta": r["effect"]["size_cap_delta"],
                    "note": r["note"],
                }
            )
    return detected


def _safe_size_multiplier(commander_conf: float, fire_weight: float, shinsal: list[dict[str, Any]]) -> float:
    # fire gate: limited band; cannot explode size.
    fire_gate = _clamp((0.55 + (fire_weight - 0.2) * 0.8), 0.75, 1.05)
    overlay_mult = 1.0
    overlay_delta = 0.0
    for s in shinsal:
        overlay_mult *= float(s.get("confidence_multiplier", 1.0))
        overlay_delta += float(s.get("size_cap_delta", 0.0))
    core = commander_conf * fire_gate * _clamp(overlay_mult, 0.9, 1.1)
    out = core + overlay_delta
    return round(_clamp(out, 0.1, 1.0), 6)


def _validate_against_schema(obj: dict[str, Any], schema_path: Path) -> tuple[bool, str]:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return True, "jsonschema_not_installed_skip"
    schema = _read_json(schema_path)
    jsonschema.validate(obj, schema)
    return True, "ok"


_PROBE_STATES_CACHE: list[dict[str, Any]] | None = None


def _load_probe_states() -> list[dict[str, Any]]:
    global _PROBE_STATES_CACHE
    if _PROBE_STATES_CACHE is not None:
        return _PROBE_STATES_CACHE
    if not PROBE_16_STATE_PATH.is_file():
        _PROBE_STATES_CACHE = []
        return _PROBE_STATES_CACHE
    doc = json.loads(PROBE_16_STATE_PATH.read_text(encoding="utf-8"))
    st = doc.get("states")
    _PROBE_STATES_CACHE = st if isinstance(st, list) else []
    return _PROBE_STATES_CACHE


def _commander_vec4_slkm(elements: dict[str, float]) -> list[float]:
    """Normalized 4-vector aligned to probe axes S,L,K,M: wood→S, fire→L, earth→K, metal+water→M."""
    w = float(elements.get("wood", 0.0) or 0.0)
    f = float(elements.get("fire", 0.0) or 0.0)
    e = float(elements.get("earth", 0.0) or 0.0)
    m = float(elements.get("metal", 0.0) or 0.0)
    wa = float(elements.get("water", 0.0) or 0.0)
    fourth = m + wa
    tot = w + f + e + fourth
    if tot <= 0:
        return [0.25, 0.25, 0.25, 0.25]
    return [round(w / tot, 6), round(f / tot, 6), round(e / tot, 6), round(fourth / tot, 6)]


def _nearest_probe_state_id(elements: dict[str, float]) -> tuple[int | None, float, str]:
    """Nearest ``state_id`` in ``16_STATE_MASTER_PROBE_v1`` by L2 vs ``vector_4d`` (research alignment only)."""
    states = _load_probe_states()
    if not states:
        return None, -1.0, "probe_missing"
    v = _commander_vec4_slkm(elements)
    best_id: int | None = None
    best_d = float("inf")
    for s in states:
        if not isinstance(s, dict):
            continue
        vd = s.get("vector_4d")
        if not isinstance(vd, dict):
            continue
        p = [
            float(vd.get("S", 0.0) or 0.0),
            float(vd.get("L", 0.0) or 0.0),
            float(vd.get("K", 0.0) or 0.0),
            float(vd.get("M", 0.0) or 0.0),
        ]
        d = sum((v[i] - p[i]) ** 2 for i in range(4)) ** 0.5
        if d < best_d:
            best_d = d
            sid = s.get("state_id")
            try:
                best_id = int(sid) if sid is not None else None
            except (TypeError, ValueError):
                best_id = None
    if best_id is None:
        return None, -1.0, "no_match"
    return best_id, round(best_d, 6), "ok"


def build_upgrade_doc(doc: dict[str, Any], *, source_path: str = "") -> dict[str, Any]:
    """Build v2 upgrade dict from a commander-shaped lens document (no file I/O)."""
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    commander_conf = float(scores.get("confidence", 0.5) or 0.5)
    dir_score = float(scores.get("direction_score", 0.0) or 0.0)

    adv = doc.get("advanced") if isinstance(doc.get("advanced"), dict) else {}
    input_summary = adv.get("input_summary") if isinstance(adv.get("input_summary"), dict) else {}
    pillars = input_summary.get("pillars") if isinstance(input_summary.get("pillars"), dict) else {}
    if not pillars or not any(str(v).strip() for v in pillars.values()):
        slots = adv.get("slots") if isinstance(adv.get("slots"), dict) else {}
        sp = slots.get("pillars") if isinstance(slots.get("pillars"), dict) else {}
        if sp:
            pillars = sp

    hidden = _extract_hidden_gans(doc)
    vector = _calc_jijangan_vector(hidden)
    pillar_map = {k: str(v) for k, v in pillars.items()}
    shinsal = _detect_shinsal_candidates(pillar_map)
    size_reco = _safe_size_multiplier(commander_conf, vector.get("fire", 0.0), shinsal)
    tension, tension_method = _structural_tension_v1(pillar_map)
    latent_vec, latent_axes, latent_note = _latent_energy_vector_4d(vector)
    shinsal_logs = _shinsal_detection_logs(pillar_map, shinsal)

    nearest_sid, nearest_dist, nearest_stat = _nearest_probe_state_id(vector)
    probe_nearest: dict[str, Any] = {
        "contract": "btrack_16state_master_probe_nearest_v1",
        "probe_path": "data/myeongni/16_STATE_MASTER_PROBE_v1.json",
        "nearest_state_id": nearest_sid,
        "l2_distance": nearest_dist,
        "status": nearest_stat,
        "vector_layout": "[wood,fire,earth,metal+water]_normalized vs probe vector_4d S,L,K,M",
    }

    return {
        "schema": "myeongri_core_v2_upgrade_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "labels": {"fact": "[FACT]", "hypothesis": "[HYPOTHESIS]", "research_only": "[RESEARCH_ONLY]"},
        "b_track_notice": B_TRACK_NOTICE,
        "input": {
            "source_path": source_path or "(inline)",
            "pillars": pillars,
            "commander_confidence": round(commander_conf, 6),
            "direction_score": round(dir_score, 6),
        },
        "jijangan_weighted_vector": {
            "method": "pillar_weight * hidden_order_weight normalized",
            "pillar_weight": PILLAR_WEIGHT,
            "hidden_order_weight": HIDDEN_ORDER_WEIGHT,
            "elements": vector,
            "hidden_gans": hidden,
        },
        "neutral_structure_metrics_v1": {
            "contract": "btrack_neutral_structure_v1",
            "structural_tension_v1": tension,
            "structural_tension_method": tension_method,
            "latent_energy_vector_4d": latent_vec,
            "latent_energy_axes": latent_axes,
            "latent_energy_note": latent_note,
        },
        "shinsal_impact_overlay": {
            "mode": "research_subset_only",
            "detected": shinsal,
            "policy": "No direct trade trigger; overlay applies to size recommendation only.",
        },
        "shinsal_detection_logs": shinsal_logs,
        "execution_guardrail": {
            "size_only_overlay": True,
            "direction_override_allowed": False,
            "auto_bridge_allowed": False,
            "note": "A-track direction must remain external to myeongri module.",
        },
        "output": {
            "size_multiplier_recommended": size_reco,
            "commander_overlay_multiplier": size_reco,
            "direction_override_allowed": False,
            "policy": "Apply as advisory risk-size cap only.",
        },
        "myeongni_16state_probe_nearest_v1": probe_nearest,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--schema-path", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--validate-schema", action="store_true")
    args = ap.parse_args()

    doc = _read_json(args.input)
    out = build_upgrade_doc(doc, source_path=str(args.input.resolve()))

    if args.validate_schema:
        ok, msg = _validate_against_schema(out, args.schema_path)
        out["schema_validation"] = {"ok": ok, "message": msg, "schema_path": str(args.schema_path.resolve())}

    size_reco = float(out["output"]["size_multiplier_recommended"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"size_multiplier_recommended: {size_reco}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
