#!/usr/bin/env python3
"""Read independent lens artifacts + observation sidecars; emit consensus/conflict (fusion stub v0)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "independent_lens_fusion_stub_latest.json"

DEFAULT_MYEONGNI = ROOT / "docs" / "final" / "artifacts" / "myeongni_independent_lens_latest.json"
DEFAULT_SASANG = ROOT / "docs" / "final" / "artifacts" / "sasang_independent_lens_latest.json"
DEFAULT_LOGOS = ROOT / "docs" / "final" / "artifacts" / "logos_independent_lens_latest.json"
DEFAULT_MARKET_SASANG = ROOT / "docs" / "final" / "artifacts" / "market_sasang_lens_latest.json"
DEFAULT_MARKET_MYEONGNI = ROOT / "docs" / "final" / "artifacts" / "market_myeongni_lens_latest.json"
DEFAULT_NEWS = ROOT / "docs" / "final" / "artifacts" / "news_independent_lens_latest.json"
DEFAULT_MACRO = ROOT / "docs" / "final" / "artifacts" / "macro_independent_lens_latest.json"
DEFAULT_OVERNIGHT = ROOT / "docs" / "final" / "artifacts" / "global_market_overnight_signals_v1_latest.json"

STUB_VERSION = "0.5.0"
BEAR_SIGN_THRESHOLD = 0.08
OVERNIGHT_SHOCK_MOVE_PCT = 3.0
HUMANIST_LENS_IDS = frozenset({"myeongni", "sasang", "market_sasang", "market_myeongni"})


def resolve_fusion_headline_v1(fusion: dict[str, Any] | None) -> dict[str, Any]:
    """Operator headline from fusion stub v0.5+ (falls back to raw consensus for older artifacts)."""
    if not fusion:
        return {
            "headline_sign": "unknown",
            "raw_consensus_sign": "unknown",
            "effective_consensus_sign": "unknown",
            "non_gating": False,
            "demote_active": False,
            "headline_source": "missing",
        }
    hg = fusion.get("headline_gating") if isinstance(fusion.get("headline_gating"), dict) else {}
    cs = fusion.get("consensus") if isinstance(fusion.get("consensus"), dict) else {}
    ce = fusion.get("consensus_effective") if isinstance(fusion.get("consensus_effective"), dict) else {}
    headline_sign = str(
        hg.get("headline_sign") or ce.get("consensus_sign") or cs.get("consensus_sign") or "unknown"
    )
    return {
        "headline_sign": headline_sign,
        "raw_consensus_sign": str(cs.get("consensus_sign") or "unknown"),
        "effective_consensus_sign": str(ce.get("consensus_sign") or cs.get("consensus_sign") or "unknown"),
        "non_gating": bool(hg.get("non_gating")),
        "demote_active": bool(fusion.get("demote_active")),
        "headline_source": str(hg.get("headline_source") or "consensus_fallback"),
    }


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _pick_sign(v: float, *, threshold: float = BEAR_SIGN_THRESHOLD) -> str:
    if v > threshold:
        return "bull"
    if v < -threshold:
        return "bear"
    return "neutral"


def _load_lens(path: Path, lens_name: str) -> dict[str, Any]:
    doc = _read_json(path)
    if not doc:
        return {
            "lens_id": lens_name,
            "available": False,
            "direction_score": 0.0,
            "confidence": 0.0,
            "direction_sign": "neutral",
        }
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    ds = float(scores.get("direction_score", 0.0))
    cf = float(scores.get("confidence", 0.0))
    return {
        "lens_id": str(doc.get("lens_id") or lens_name),
        "available": True,
        "direction_score": ds,
        "confidence": max(0.0, min(1.0, cf)),
        "direction_sign": _pick_sign(ds),
        "artifact_path": str(path.resolve()),
        "artifact_ts_utc": doc.get("ts_utc") or doc.get("generated_at_utc"),
        "schema": doc.get("schema"),
    }


def _max_overnight_move_pct(overnight: dict[str, Any]) -> float | None:
    moves: list[float] = []
    for row in overnight.get("indices") or []:
        if not isinstance(row, dict):
            continue
        ch = row.get("change_pct")
        if isinstance(ch, (int, float)):
            moves.append(abs(float(ch)))
    return max(moves) if moves else None


def _load_overnight_sidecar(path: Path) -> dict[str, Any]:
    doc = _read_json(path)
    if not doc:
        return {
            "lens_id": "overnight",
            "role": "observation_only_sidecar",
            "non_voting": True,
            "available": False,
            "direction_score": 0.0,
            "confidence": 0.0,
            "direction_sign": "neutral",
        }
    tilt = str(doc.get("composite_tilt") or "")
    max_move = _max_overnight_move_pct(doc)
    shock = tilt == "risk_off_overnight" and (
        max_move is not None and max_move >= OVERNIGHT_SHOCK_MOVE_PCT
    )
    if tilt == "risk_off_overnight":
        if max_move is not None and max_move > 0:
            ds = -min(0.85, max_move / 10.0)
        else:
            ds = -0.35
        cf = 0.65 if shock else 0.45
    elif tilt == "risk_on_overnight":
        ds = 0.25
        cf = 0.45
    else:
        ds = 0.0
        cf = 0.35
    return {
        "lens_id": "overnight",
        "role": "observation_only_sidecar",
        "non_voting": True,
        "available": True,
        "direction_score": round(ds, 6),
        "confidence": round(cf, 6),
        "direction_sign": _pick_sign(ds),
        "artifact_path": str(path.resolve()),
        "artifact_ts_utc": doc.get("generated_at_utc"),
        "schema": doc.get("schema"),
        "overnight_meta": {
            "composite_tilt": tilt,
            "max_abs_index_change_pct": max_move,
            "shock_overnight": shock,
        },
    }


def _load_sidecar_lens(path: Path, lens_id: str) -> dict[str, Any]:
    row = _load_lens(path, lens_id)
    row["role"] = "observation_only_sidecar"
    row["non_voting"] = True
    return row


def _load_market_sasang_lens(path: Path) -> dict[str, Any] | None:
    doc = _read_json(path)
    if not doc or doc.get("schema") != "market_sasang_lens_v1":
        return None
    fb = doc.get("fusion_bridge") if isinstance(doc.get("fusion_bridge"), dict) else {}
    ds = float(fb.get("score_hint") or 0.0)
    ds = max(-1.0, min(1.0, ds))
    unc = doc.get("uncertainty") if isinstance(doc.get("uncertainty"), dict) else {}
    comp = float(unc.get("composite_uncertainty") or 0.5)
    comp = max(0.0, min(1.0, comp))
    cf = max(0.0, min(1.0, 1.0 - comp))
    veto = doc.get("veto") if isinstance(doc.get("veto"), dict) else {}
    if veto.get("force_hold"):
        cf *= 0.25
    row: dict[str, Any] = {
        "lens_id": "market_sasang",
        "available": True,
        "direction_score": ds,
        "confidence": max(0.0, min(1.0, cf)),
        "direction_sign": _pick_sign(ds),
        "artifact_path": str(path.resolve()),
        "artifact_ts_utc": doc.get("ts_utc"),
        "schema": doc.get("schema"),
        "market_sasang_lens_v1": {
            "state_vector_sasang_softmax": doc.get("state_vector_sasang_softmax"),
            "composite_uncertainty": round(comp, 8),
            "veto_force_hold": bool(veto.get("force_hold")),
            "veto_reason_codes": list(veto.get("reason_codes") or []),
            "direction_hint": fb.get("direction_hint"),
            "human_commander_gate_v1": doc.get("human_commander_gate_v1"),
        },
    }
    return row


def _load_market_myeongni_lens(path: Path) -> dict[str, Any] | None:
    doc = _read_json(path)
    if not doc or doc.get("schema") != "market_myeongni_lens_v1":
        return None
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    ds = float(scores.get("direction_score") or 0.0)
    ds = max(-1.0, min(1.0, ds))
    cf = float(scores.get("confidence") or 0.0)
    cf = max(0.0, min(1.0, cf))
    overlay = doc.get("overlay") if isinstance(doc.get("overlay"), dict) else {}
    applied = overlay.get("applied") if isinstance(overlay.get("applied"), dict) else {}
    sign = str(doc.get("direction_sign") or _pick_sign(ds))
    return {
        "lens_id": "market_myeongni",
        "available": True,
        "direction_score": ds,
        "confidence": cf,
        "direction_sign": sign,
        "artifact_path": str(path.resolve()),
        "artifact_ts_utc": doc.get("ts_utc"),
        "schema": doc.get("schema"),
        "market_myeongni_lens_v1": {
            "base_direction_score": overlay.get("base_direction_score"),
            "base_confidence": overlay.get("base_confidence"),
            "applied": applied,
            "upstream_lens_id": overlay.get("upstream_lens_id"),
        },
    }


def _consensus(
    summary: list[dict[str, Any]],
    vote_weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    vote_weights = vote_weights or {}
    active = [x for x in summary if x.get("available")]
    voting: list[dict[str, Any]] = []
    for row in active:
        w = float(vote_weights.get(str(row.get("lens_id")), 1.0))
        if w <= 0:
            continue
        voting.append({**row, "_vote_weight": w})

    if not voting:
        return {
            "available_count": 0,
            "agreement_rate": 0.0,
            "conflict_count": 0,
            "consensus_sign": "neutral",
            "consensus_score": 0.0,
            "consensus_confidence": 0.0,
        }

    sign_counts = {"bull": 0, "bear": 0, "neutral": 0}
    for row in voting:
        sign_counts[str(row["direction_sign"])] += 1
    majority_sign = max(sign_counts, key=sign_counts.get)
    agreement_rate = sign_counts[majority_sign] / len(voting)
    conflict_count = len(voting) - sign_counts[majority_sign]

    weighted_num = sum(
        float(r["direction_score"]) * float(r["confidence"]) * float(r["_vote_weight"])
        for r in voting
    )
    weighted_den = sum(float(r["confidence"]) * float(r["_vote_weight"]) for r in voting)
    consensus_score = weighted_num / weighted_den if weighted_den > 0 else 0.0
    mean_conf = sum(float(r["confidence"]) for r in voting) / len(voting)

    return {
        "available_count": len(voting),
        "agreement_rate": round(agreement_rate, 6),
        "conflict_count": conflict_count,
        "consensus_sign": majority_sign,
        "consensus_score": round(consensus_score, 6),
        "consensus_confidence": round(mean_conf, 6),
    }


def _sidecar_consensus(sidecar_rails: list[dict[str, Any]]) -> dict[str, Any]:
    active = [x for x in sidecar_rails if x.get("available")]
    if not active:
        return {
            "consensus_sign": "neutral",
            "consensus_score": 0.0,
            "consensus_confidence": 0.0,
        }
    num = sum(float(r["direction_score"]) * float(r["confidence"]) for r in active)
    den = sum(float(r["confidence"]) for r in active)
    score = num / den if den > 0 else 0.0
    conf = sum(float(r["confidence"]) for r in active) / len(active)
    return {
        "consensus_sign": _pick_sign(score),
        "consensus_score": round(score, 6),
        "consensus_confidence": round(conf, 6),
    }


def _evaluate_demote(
    cs_raw: dict[str, Any],
    sidecar_rails: list[dict[str, Any]],
) -> tuple[bool, list[str], dict[str, float]]:
    trace: list[str] = []
    weights: dict[str, float] = {}

    conflict_count = int(cs_raw.get("conflict_count") or 0)
    if conflict_count >= 2:
        trace.append("R1_conflict_count_ge_2: lens-only conflict_count>=2")

    news = next((r for r in sidecar_rails if r.get("lens_id") == "news" and r.get("available")), None)
    macro = next((r for r in sidecar_rails if r.get("lens_id") == "macro" and r.get("available")), None)
    overnight = next(
        (r for r in sidecar_rails if r.get("lens_id") == "overnight" and r.get("available")), None
    )

    news_bear = bool(news and news.get("direction_sign") == "bear")
    macro_bear = bool(macro and macro.get("direction_sign") == "bear")
    shock_overnight = False
    if overnight:
        meta = overnight.get("overnight_meta") if isinstance(overnight.get("overnight_meta"), dict) else {}
        shock_overnight = bool(meta.get("shock_overnight"))

    if shock_overnight:
        trace.append("R2_shock_overnight: risk_off + index move >=3%")
    if news_bear and macro_bear:
        trace.append("R3_sidecar_dual_bear: news and macro both bear")
    elif shock_overnight and (news_bear or macro_bear):
        trace.append("R4_shock_plus_sidecar_bear: overnight shock + news/macro bear")

    demote = bool(trace)
    if demote:
        for lid in HUMANIST_LENS_IDS:
            weights[lid] = 0.0
        trace.append("R5_humanist_vote_weight_zero: myeongni/sasang/market_* capped")

    return demote, trace, weights


def _apply_effective_consensus(
    lens_rows: list[dict[str, Any]],
    cs_raw: dict[str, Any],
    sidecar_rails: list[dict[str, Any]],
    demote_active: bool,
    vote_weights: dict[str, float],
) -> dict[str, Any]:
    cs_lens = _consensus(lens_rows, vote_weights)
    if not demote_active:
        return cs_lens

    sidecar_cs = _sidecar_consensus(sidecar_rails)
    raw_sign = str(cs_raw.get("consensus_sign") or "neutral")
    side_sign = str(sidecar_cs.get("consensus_sign") or "neutral")

    if raw_sign == "bull" and side_sign == "bear":
        return {
            **cs_lens,
            "consensus_sign": "bear",
            "consensus_score": sidecar_cs["consensus_score"],
            "consensus_confidence": max(
                float(cs_lens.get("consensus_confidence") or 0.0),
                float(sidecar_cs.get("consensus_confidence") or 0.0),
            ),
            "sidecar_override": True,
        }
    if raw_sign == "bull" and side_sign == "neutral":
        return {
            **cs_lens,
            "consensus_sign": "neutral",
            "consensus_score": round(
                (float(cs_lens.get("consensus_score") or 0.0) + float(sidecar_cs.get("consensus_score") or 0.0))
                / 2.0,
                6,
            ),
            "sidecar_override": True,
        }
    return {**cs_lens, "sidecar_override": False}


def _build_conflict_summary(
    lens_rows: list[dict[str, Any]],
    cs: dict[str, Any],
    logos_doc: dict[str, Any] | None,
    *,
    demote_trace: list[str] | None = None,
    headline_gating: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active = [x for x in lens_rows if x.get("available")]
    maj = str(cs.get("consensus_sign") or "neutral")
    minority_ids: list[str] = []
    for r in active:
        if r.get("direction_sign") != maj:
            minority_ids.append(str(r.get("lens_id", "?")))

    parts: list[str] = []
    parts.append(
        f"Lens direction alignment: majority_sign={maj}, agreement_rate={cs.get('agreement_rate')}, "
        f"conflict_count={cs.get('conflict_count')}."
    )
    if minority_ids:
        parts.append(
            "Minority vs majority: "
            + ", ".join(minority_ids)
            + f" differ from majority_sign={maj}."
        )
    else:
        parts.append("No direction_sign conflict among active lenses.")

    breakdown: list[str] = []
    for r in active:
        breakdown.append(
            f"{r['lens_id']}: sign={r['direction_sign']}, "
            f"score={float(r['direction_score']):.6f}, conf={float(r['confidence']):.6f}"
        )
    parts.append("Breakdown: " + "; ".join(breakdown) + ".")

    if demote_trace:
        parts.append("Demote trace: " + "; ".join(demote_trace) + ".")
    if headline_gating and headline_gating.get("non_gating"):
        parts.append(
            "Headline gating: raw consensus non-gating; use headline_sign="
            + str(headline_gating.get("headline_sign"))
            + "."
        )

    verse_ids: list[str] = []
    if logos_doc and isinstance(logos_doc.get("evidence_refs"), list):
        for er in logos_doc["evidence_refs"]:
            if isinstance(er, dict):
                vid = er.get("verse_id")
                if vid:
                    verse_ids.append(str(vid))
    if verse_ids:
        parts.append(
            "Logos evidence verse_id anchors (batch-bound): " + ", ".join(verse_ids) + "."
        )
    ns = logos_doc.get("narrative_snippet_guarded") if logos_doc else None
    if isinstance(ns, str) and ns.strip():
        clip = ns.strip()
        if len(clip) > 320:
            clip = clip[:319] + "…"
        parts.append("Logos hash-tagged snippet (clipped): " + clip)

    return {
        "conflict_narrative_guarded": " ".join(parts),
        "minority_lens_ids": minority_ids,
        "majority_sign": maj,
        "logos_evidence_verse_ids": verse_ids,
        "narrative_policy": (
            "Deterministic template from lens signs/scores and optional Logos "
            "evidence_refs/narrative_snippet_guarded only; no LLM paraphrase; "
            "observation_only; not an A-track action."
        ),
    }


def build_fusion_stub_document(
    *,
    myeongni: Path,
    sasang: Path,
    logos: Path,
    market_sasang: Path,
    market_myeongni: Path,
    news: Path,
    macro: Path,
    overnight: Path,
    include_market_sasang: bool,
    include_market_myeongni: bool,
) -> dict[str, Any]:
    lens_rows = [
        _load_lens(myeongni, "myeongni"),
        _load_lens(sasang, "sasang"),
        _load_lens(logos, "logos"),
    ]
    if include_market_sasang:
        ms = _load_market_sasang_lens(market_sasang)
        if ms is not None:
            lens_rows.append(ms)
    if include_market_myeongni:
        mm = _load_market_myeongni_lens(market_myeongni)
        if mm is not None:
            lens_rows.append(mm)

    sidecar_rails = [
        _load_sidecar_lens(news, "news"),
        _load_sidecar_lens(macro, "macro"),
        _load_overnight_sidecar(overnight),
    ]

    cs_raw = _consensus(lens_rows)
    demote_active, demote_trace, vote_weights = _evaluate_demote(cs_raw, sidecar_rails)
    cs_effective = _apply_effective_consensus(
        lens_rows, cs_raw, sidecar_rails, demote_active, vote_weights
    )

    raw_sign = str(cs_raw.get("consensus_sign") or "neutral")
    eff_sign = str(cs_effective.get("consensus_sign") or "neutral")
    headline_gating = {
        "non_gating": bool(demote_active and raw_sign == "bull" and eff_sign != "bull"),
        "headline_sign": eff_sign,
        "headline_source": "consensus_effective",
        "raw_consensus_sign": raw_sign,
    }

    logos_doc = _read_json(logos)
    conflict_summary = _build_conflict_summary(
        lens_rows,
        cs_raw,
        logos_doc,
        demote_trace=demote_trace if demote_active else None,
        headline_gating=headline_gating if demote_active else None,
    )

    return {
        "schema": "independent_lens_fusion_stub_v0",
        "version": STUB_VERSION,
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "mode": "observation_only",
        "inputs": lens_rows,
        "sidecar_rails": sidecar_rails,
        "consensus": cs_raw,
        "consensus_effective": cs_effective,
        "demote_trace": demote_trace,
        "demote_active": demote_active,
        "headline_gating": headline_gating,
        "conflict_summary": conflict_summary,
        "note": (
            "Read-only comparison of independent lens outputs; not A-track auto-fusion or live sizing trigger. "
            "v0.5.0: sidecar_rails (news/macro/overnight, non-voting) + consensus_effective demote when "
            "shock_overnight+sidecar bear or conflict_count>=2; humanist lens vote_weight=0 on demote. "
            "consensus field remains raw lens-only (v0.4 compat); use headline_gating.headline_sign for operator view. "
            "Optional market_sasang/market_myeongni via --no-market-sasang / --no-market-myeongni."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Fusion stub v0 for independent lens outputs.")
    ap.add_argument("--myeongni", type=Path, default=DEFAULT_MYEONGNI)
    ap.add_argument("--sasang", type=Path, default=DEFAULT_SASANG)
    ap.add_argument("--logos", type=Path, default=DEFAULT_LOGOS)
    ap.add_argument("--market-sasang", type=Path, default=DEFAULT_MARKET_SASANG)
    ap.add_argument(
        "--no-market-sasang",
        action="store_true",
        help="Exclude market_sasang_lens_v1 (legacy 3-lens consensus only).",
    )
    ap.add_argument("--market-myeongni", type=Path, default=DEFAULT_MARKET_MYEONGNI)
    ap.add_argument(
        "--no-market-myeongni",
        action="store_true",
        help="Exclude market_myeongni_lens_v1 overlay row.",
    )
    ap.add_argument("--news", type=Path, default=DEFAULT_NEWS)
    ap.add_argument("--macro", type=Path, default=DEFAULT_MACRO)
    ap.add_argument("--overnight", type=Path, default=DEFAULT_OVERNIGHT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    out = build_fusion_stub_document(
        myeongni=args.myeongni,
        sasang=args.sasang,
        logos=args.logos,
        market_sasang=args.market_sasang,
        market_myeongni=args.market_myeongni,
        news=args.news,
        macro=args.macro,
        overnight=args.overnight,
        include_market_sasang=not args.no_market_sasang,
        include_market_myeongni=not args.no_market_myeongni,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    demote = out.get("demote_active")
    hg = out.get("headline_gating") or {}
    print(
        f"raw={((out.get('consensus') or {}).get('consensus_sign'))} "
        f"effective={((out.get('consensus_effective') or {}).get('consensus_sign'))} "
        f"demote={demote} headline={hg.get('headline_sign')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
