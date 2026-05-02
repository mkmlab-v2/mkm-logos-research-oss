#!/usr/bin/env python3
"""Generate B-Track hypothesis JSON (schema btrack_hypothesis_prophecy_v1).

Modes:
  --stub    Deterministic hypothesis from fusion_stub consensus (no API; CI-safe; daily chain default).
  --gemini  Optional; prefer org Gen AI / Google Cloud credit workflows. Keys in .env are error-prone and
            burn quota quickly — use only for rare manual/batch runs when keys are intentionally set.

Output: docs/final/artifacts/btrack_hypothesis_prophecy_latest.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = ROOT / "docs" / "final" / "artifacts" / "btrack_llm_input_bundle_latest.json"
DEFAULT_SCHEMA = ROOT / "docs" / "final" / "BTRACK_HYPOTHESIS_PROPHECY_V1.schema.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btrack_hypothesis_prophecy_latest.json"
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_ENSEMBLE_CONFIG = ROOT / "docs" / "final" / "artifacts" / "btrack_lens_ensemble_v1.json"
DEFAULT_BLOCKED_ADJUSTMENTS_REGISTRY = ROOT / "docs" / "final" / "artifacts" / "blocked_adjustments_registry_v1.jsonl"
DEFAULT_EFFECTIVE_ADJUSTMENTS_REGISTRY = ROOT / "docs" / "final" / "artifacts" / "effective_adjustments_registry_v1.jsonl"

SCHEMA_ID = "btrack_hypothesis_prophecy_v1"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_hypothesis(doc: dict[str, Any]) -> list[str]:
    """Return list of error strings; empty if OK. Works without jsonschema package."""
    errs: list[str] = []
    if doc.get("schema") != SCHEMA_ID:
        errs.append(f"schema must be {SCHEMA_ID!r}")
    if doc.get("hypothesis_tier") != "B":
        errs.append("hypothesis_tier must be B")
    if doc.get("boundary_ack") is not True:
        errs.append("boundary_ack must be true")
    ts = doc.get("ts_utc")
    if not isinstance(ts, str) or not ts.strip():
        errs.append("ts_utc required")
    lab = doc.get("label")
    if not isinstance(lab, str) or "[HYPO]" not in lab:
        errs.append("label must include [HYPO]")
    pred = doc.get("prediction")
    if not isinstance(pred, dict):
        errs.append("prediction object required")
    else:
        inst = pred.get("instrument")
        hor = pred.get("horizon")
        dire = pred.get("direction")
        if inst not in ("kospi", "btc", "none", "multi"):
            errs.append("prediction.instrument invalid enum")
        if not isinstance(hor, str) or not hor.strip():
            errs.append("prediction.horizon required")
        if dire not in ("bull", "bear", "neutral", "abstain"):
            errs.append("prediction.direction invalid enum")
        cf = pred.get("confidence")
        if cf is not None and (not isinstance(cf, (int, float)) or not (0.0 <= float(cf) <= 1.0)):
            errs.append("prediction.confidence must be null or 0..1")
    return errs


def _try_jsonschema(doc: dict[str, Any], schema_path: Path) -> list[str]:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return []
    try:
        schema = _load_json(schema_path)
        jsonschema.Draft202012Validator(schema).validate(doc)
    except Exception as e:  # noqa: BLE001
        return [str(e)]
    return []


def _sign_to_direction(sign: str) -> str:
    s = (sign or "").strip().lower()
    if s == "bull":
        return "bull"
    if s == "bear":
        return "bear"
    return "neutral"


def _build_stub_from_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    fusion = bundle.get("artifacts", {}).get("independent_lens_fusion_stub") or {}
    cs = fusion.get("consensus") if isinstance(fusion.get("consensus"), dict) else {}
    consensus_sign = str(cs.get("consensus_sign") or "neutral").lower()
    direction = _sign_to_direction(consensus_sign)
    conf = cs.get("consensus_confidence")
    try:
        cfn = float(conf) if conf is not None else 0.45
    except (TypeError, ValueError):
        cfn = 0.45
    cfn = max(0.0, min(1.0, cfn))

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema": SCHEMA_ID,
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "ts_utc": now,
        "label": "[HYPO] Stub from fusion consensus_sign only — not live trading; sasang [NON-MEDICAL] if used.",
        "lens_artifacts": {
            "logos": "docs/final/artifacts/logos_independent_lens_latest.json",
            "myeongni": "docs/final/artifacts/myeongni_independent_lens_latest.json",
            "sasang": "docs/final/artifacts/sasang_independent_lens_latest.json",
            "fusion_stub": "docs/final/artifacts/independent_lens_fusion_stub_latest.json",
            "shadow_minority_monthly": "docs/final/artifacts/independent_lens_shadow_minority_monthly_latest.json",
        },
        "prediction": {
            "instrument": "multi",
            "horizon": "1d",
            "direction": direction,
            "confidence": round(cfn, 4),
        },
        "provenance": {
            "llm_model": "stub_heuristic_v1",
            "prompt_id": "generate_btrack_hypothesis_prophecy_v1.py (default heuristic)",
        },
    }


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _sgn_to_dir(v: float) -> str:
    if v > 0:
        return "bull"
    if v < 0:
        return "bear"
    return "neutral"


def _extract_price_lens_from_score(score_doc: dict[str, Any], lookback: int) -> tuple[float, float, dict[str, Any]]:
    rows = score_doc.get("rows") if isinstance(score_doc.get("rows"), list) else []
    k_rows = [r for r in rows if isinstance(r, dict) and r.get("instrument") == "kospi"]
    if not k_rows:
        return 0.0, 0.0, {"reason": "score_rows_missing"}
    tail = k_rows[-max(1, int(lookback)) :]
    returns = [_safe_float(r.get("daily_return"), 0.0) for r in tail]
    avg_ret = sum(returns) / max(1, len(returns))
    # Scale to bounded score domain with mild sensitivity.
    direction_score = max(-1.0, min(1.0, avg_ret / 0.02))
    confidence = max(0.0, min(1.0, abs(direction_score)))
    return direction_score, confidence, {"lookback_rows": len(tail), "avg_daily_return": avg_ret}


def _extract_lens_score(bundle: dict[str, Any], artifact_key: str) -> tuple[float, float]:
    art = bundle.get("artifacts", {}).get(artifact_key) or {}
    scores = art.get("scores") if isinstance(art.get("scores"), dict) else {}
    return _safe_float(scores.get("direction_score"), 0.0), _safe_float(scores.get("confidence"), 0.0)


def _build_ensemble_from_bundle(
    bundle: dict[str, Any],
    *,
    score_doc: dict[str, Any],
    ensemble_cfg: dict[str, Any],
    previous_doc: dict[str, Any] | None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    weights = ensemble_cfg.get("weights") if isinstance(ensemble_cfg.get("weights"), dict) else {}
    rules = ensemble_cfg.get("rules") if isinstance(ensemble_cfg.get("rules"), dict) else {}

    price_score, price_conf, price_meta = _extract_price_lens_from_score(
        score_doc,
        lookback=int(rules.get("price_lookback_days", 5)),
    )

    macro_art = bundle.get("artifacts", {}).get("macro_independent_lens") or {}
    news_art = bundle.get("artifacts", {}).get("news_independent_lens") or {}
    macro_scores = macro_art.get("scores") if isinstance(macro_art.get("scores"), dict) else {}
    news_scores = news_art.get("scores") if isinstance(news_art.get("scores"), dict) else {}
    macro_score = _safe_float(macro_scores.get("direction_score"), 0.0)
    macro_conf = _safe_float(macro_scores.get("confidence"), 0.0)
    news_score = _safe_float(news_scores.get("direction_score"), 0.0)
    news_conf = _safe_float(news_scores.get("confidence"), 0.0)

    m_score, m_conf = _extract_lens_score(bundle, "myeongni_independent_lens")
    s_score, s_conf = _extract_lens_score(bundle, "sasang_independent_lens")
    ms_score = (m_score + s_score) / 2.0
    ms_conf = (m_conf + s_conf) / 2.0

    lens_values = {
        "price": {"score": price_score, "confidence": price_conf},
        "macro": {"score": macro_score, "confidence": macro_conf},
        "news": {"score": news_score, "confidence": news_conf},
        "myeongni_sasang": {"score": ms_score, "confidence": ms_conf},
    }

    def w(name: str) -> float:
        return _safe_float(weights.get(name), 0.0)

    weighted = sum(w(k) * _safe_float(v["score"]) for k, v in lens_values.items())
    margin = _safe_float(rules.get("tie_break_min_margin"), 0.03)
    preliminary_direction = "neutral" if abs(weighted) < margin else _sgn_to_dir(weighted)
    neutral_penalty = _safe_float(rules.get("neutral_penalty"), -0.1)

    prev_streak = 0
    if isinstance(previous_doc, dict):
        pmeta = previous_doc.get("runtime_meta")
        if isinstance(pmeta, dict):
            prev_streak = int(pmeta.get("neutral_streak", 0) or 0)
        else:
            pdir = str((previous_doc.get("prediction") or {}).get("direction") or "").lower()
            prev_streak = 1 if pdir == "neutral" else 0
    neutral_streak = prev_streak + 1 if preliminary_direction == "neutral" else 0
    max_neutral_streak = int(rules.get("max_neutral_streak_before_recalibration", 3))

    direction = preliminary_direction
    recalibration_triggered = False
    tie_breaker_order = list(rules.get("tie_breaker_order") or ["price", "macro", "news", "myeongni_sasang"])
    if neutral_streak >= max_neutral_streak:
        recalibration_triggered = True
        for name in tie_breaker_order:
            cand = lens_values.get(name, {"score": 0.0})
            c_score = _safe_float(cand.get("score"), 0.0)
            if abs(c_score) >= margin:
                direction = _sgn_to_dir(c_score)
                break

    if direction == "neutral":
        # Reduce confidence for neutral to discourage persistent neutral lock-in.
        confidence = max(0.0, min(1.0, 0.5 + neutral_penalty))
    else:
        confidence = max(0.0, min(1.0, abs(weighted)))

    label = (
        "[HYPO] Rule-based lens ensemble v1 (price/macro/news/myeongni-sasang). "
        "research_only; no live trigger; sasang [NON-MEDICAL] if referenced."
    )
    return {
        "schema": SCHEMA_ID,
        "version": "1.1.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "ts_utc": now,
        "label": label,
        "lens_artifacts": {
            "logos": "docs/final/artifacts/logos_independent_lens_latest.json",
            "myeongni": "docs/final/artifacts/myeongni_independent_lens_latest.json",
            "sasang": "docs/final/artifacts/sasang_independent_lens_latest.json",
            "fusion_stub": "docs/final/artifacts/independent_lens_fusion_stub_latest.json",
            "shadow_minority_monthly": "docs/final/artifacts/independent_lens_shadow_minority_monthly_latest.json",
        },
        "prediction": {
            "instrument": "multi",
            "horizon": "1d",
            "direction": direction,
            "confidence": round(confidence, 4),
        },
        "provenance": {
            "llm_model": "rule_based_ensemble_v1",
            "prompt_id": "generate_btrack_hypothesis_prophecy_v1.py (ensemble default)",
        },
        "runtime_meta": {
            "weighted_score": round(weighted, 6),
            "preliminary_direction": preliminary_direction,
            "neutral_streak": neutral_streak,
            "neutral_penalty": neutral_penalty,
            "recalibration_triggered": recalibration_triggered,
            "max_neutral_streak_before_recalibration": max_neutral_streak,
            "tie_breaker_order": tie_breaker_order,
            "tie_break_min_margin": margin,
            "lens_values": lens_values,
            "price_meta": price_meta,
            "weights": {
                "price": w("price"),
                "macro": w("macro"),
                "news": w("news"),
                "myeongni_sasang": w("myeongni_sasang"),
            },
            "macro_available": bool(macro_art),
            "news_available": bool(news_art),
        },
    }


def _extract_json_blob(text: str) -> dict[str, Any] | None:
    text = (text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        try:
            o = json.loads(m.group(1).strip())
            return o if isinstance(o, dict) else None
        except json.JSONDecodeError:
            pass
    try:
        o = json.loads(text)
        return o if isinstance(o, dict) else None
    except json.JSONDecodeError:
        return None


def _normalize_gemini_doc(doc: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    """Apply conservative post-processing so gemini output does not stick to neutral."""
    pred = doc.get("prediction")
    if not isinstance(pred, dict):
        return doc
    direction = str(pred.get("direction") or "").strip().lower()
    if direction not in ("neutral", "abstain"):
        return doc

    fusion = bundle.get("artifacts", {}).get("independent_lens_fusion_stub") or {}
    consensus = fusion.get("consensus") if isinstance(fusion.get("consensus"), dict) else {}
    c_score_raw = consensus.get("consensus_score")
    try:
        c_score = float(c_score_raw)
    except (TypeError, ValueError):
        c_score = 0.0

    fallback_dir = "neutral"
    # Favor directional call unless consensus is near-zero.
    if c_score >= 0.08:
        fallback_dir = "bull"
    elif c_score <= -0.08:
        fallback_dir = "bear"
    else:
        logos = bundle.get("artifacts", {}).get("logos_independent_lens") or {}
        logos_scores = logos.get("scores") if isinstance(logos.get("scores"), dict) else {}
        try:
            logos_ds = float(logos_scores.get("direction_score"))
        except (TypeError, ValueError):
            logos_ds = 0.0
        if logos_ds >= 0.05:
            fallback_dir = "bull"
        elif logos_ds <= -0.05:
            fallback_dir = "bear"

    if fallback_dir != "neutral":
        pred["direction"] = fallback_dir
        cf = pred.get("confidence")
        try:
            cfn = float(cf) if cf is not None else 0.0
        except (TypeError, ValueError):
            cfn = 0.0
        pred["confidence"] = round(max(cfn, 0.51), 4)
        label = str(doc.get("label") or "").strip()
        suffix = f" | neutral->{fallback_dir}_fallback"
        if suffix not in label:
            doc["label"] = f"{label}{suffix}" if label else f"[HYPO] neutral->{fallback_dir}_fallback"
    return doc


def _read_blocked_adjustment_keys(path: Path) -> set[str]:
    blocked: set[str] = set()
    if not path.is_file():
        return blocked
    for line in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        key = obj.get("adjustment_key")
        if isinstance(key, str) and key.strip():
            blocked.add(key.strip())
    return blocked


def _read_effective_adjustments(path: Path, *, min_accuracy_delta: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        adj = obj.get("adjustment")
        if not isinstance(adj, dict):
            continue
        try:
            acc = float(obj.get("accuracy_delta"))
        except (TypeError, ValueError):
            continue
        if acc < float(min_accuracy_delta):
            continue
        rows.append(obj)
    return rows


def _choose_adjustment_delta(run_id: str, blocked_keys: set[str]) -> float:
    candidates = [0.001, 0.002, 0.003, 0.004, 0.005, -0.001, -0.002]
    seed = sum(ord(c) for c in run_id)
    for i in range(len(candidates)):
        cand = candidates[(seed + i) % len(candidates)]
        key = f"resolution_threshold:{cand:+.6f}"
        if key not in blocked_keys:
            return cand
    return 0.001


def _adjustment_key(target: str, delta: float) -> str:
    return f"{target}:{float(delta):+.6f}"


def _choose_effective_adjustment(
    *,
    effective_rows: list[dict[str, Any]],
    blocked_keys: set[str],
    top_k: int,
) -> tuple[str | None, dict[str, Any] | None]:
    if not effective_rows:
        return None, None
    ranked = sorted(
        effective_rows,
        key=lambda r: float(r.get("accuracy_delta") or 0.0),
        reverse=True,
    )[: max(1, int(top_k))]
    for row in ranked:
        adj = row.get("adjustment")
        if not isinstance(adj, dict):
            continue
        target = str(adj.get("target") or "resolution_threshold")
        try:
            delta = float(adj.get("delta"))
        except (TypeError, ValueError):
            continue
        key = _adjustment_key(target, delta)
        if key in blocked_keys:
            continue
        return "effective_registry", {
            "target": target,
            "delta": round(delta, 6),
            "reason": "effective_seed_reuse",
            "seed_key": key,
            "seed_accuracy_delta": float(row.get("accuracy_delta") or 0.0),
        }
    return None, None


def _inject_or_guard_proposed_changes(
    doc: dict[str, Any],
    *,
    run_id: str,
    blocked_keys: set[str],
    effective_rows: list[dict[str, Any]],
    effective_seed_top_k: int,
) -> dict[str, Any]:
    proposed = doc.get("proposed_changes")
    if not isinstance(proposed, dict):
        proposed = {}
    mode = str(proposed.get("mode") or "").strip().lower()
    auto = proposed.get("auto_adjustment") if isinstance(proposed.get("auto_adjustment"), dict) else {}
    if mode == "config_adjustment" and auto:
        target = str(auto.get("target") or "resolution_threshold")
        try:
            delta = float(auto.get("delta"))
        except (TypeError, ValueError):
            delta = _choose_adjustment_delta(run_id, blocked_keys)
        key = f"{target}:{delta:+.6f}"
        if key in blocked_keys:
            delta = _choose_adjustment_delta(run_id, blocked_keys)
        proposed["mode"] = "config_adjustment"
        proposed["auto_adjustment"] = {
            "target": target,
            "delta": round(delta, 6),
            "reason": "blocked_adjustment_guard",
            "seed_source": "generator_guard",
        }
    else:
        seed_source, seeded = _choose_effective_adjustment(
            effective_rows=effective_rows,
            blocked_keys=blocked_keys,
            top_k=effective_seed_top_k,
        )
        if seeded:
            auto_adj = seeded
            auto_adj["seed_source"] = seed_source
        else:
            delta = _choose_adjustment_delta(run_id, blocked_keys)
            auto_adj = {
                "target": "resolution_threshold",
                "delta": round(delta, 6),
                "reason": "generator_default_with_blocked_guard",
                "seed_source": "default_fallback",
            }
        proposed = {
            "mode": "config_adjustment",
            "auto_adjustment": auto_adj,
        }
    doc["proposed_changes"] = proposed
    return doc


def _run_gemini(bundle_path: Path, *, model: str, timeout: int, bundle: dict[str, Any]) -> dict[str, Any]:
    key = __import__("os").getenv("GEMINI_API_KEY") or __import__("os").getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY required for --gemini")

    bundle_text = bundle_path.read_text(encoding="utf-8")
    schema_text = (ROOT / "docs" / "final" / "BTRACK_HYPOTHESIS_PROPHECY_V1.schema.json").read_text(
        encoding="utf-8"
    )
    prompt = f"""You are a B-Track hypothesis generator only. Output a single JSON object, no markdown, no commentary.

Required schema name: {SCHEMA_ID}
Required fields: schema, hypothesis_tier (must be \"B\"), boundary_ack (true), ts_utc (ISO UTC), label (must contain [HYPO]), prediction.instrument, prediction.horizon, prediction.direction, prediction.confidence (optional).

prediction.direction must be one of: bull, bear, neutral, abstain.
prediction.instrument one of: kospi, btc, none, multi.
Avoid neutral/abstain unless evidence is truly indecisive (very low directional edge).

Input bundle (read-only context):
{bundle_text[:120000]}

JSON Schema reference (follow required + enums):
{schema_text[:80000]}
"""
    from google import genai
    from google.genai import types

    # google.genai HttpOptions.timeout is milliseconds; API minimum deadline is 10s.
    timeout_ms = max(10_000, int(timeout) * 1000)
    client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=timeout_ms))
    resp = client.models.generate_content(
        model=model,
        contents=[types.Part.from_text(text=prompt)],
        config=types.GenerateContentConfig(temperature=0.2),
    )
    raw = (resp.text or "").strip()
    doc = _extract_json_blob(raw)
    if not doc:
        raise RuntimeError(f"Gemini did not return parseable JSON. Raw (truncated): {raw[:2000]!r}")
    return _normalize_gemini_doc(doc, bundle)


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate btrack_hypothesis_prophecy v1 JSON.")
    ap.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--ensemble-config", type=Path, default=DEFAULT_ENSEMBLE_CONFIG)
    ap.add_argument(
        "--gemini",
        action="store_true",
        help="Call Gemini (needs GEMINI_API_KEY). Default: local rule-based ensemble.",
    )
    ap.add_argument("--stub", action="store_true", help="Use legacy stub heuristic instead of ensemble.")
    ap.add_argument("--model", type=str, default="gemini-2.5-flash")
    ap.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="HTTP timeout in seconds for Gemini (sent as ms to google.genai; min 10s server-side).",
    )
    ap.add_argument("--validate-only", type=Path, metavar="FILE", help="Validate existing JSON; exit 1 on error.")
    ap.add_argument("--run-id", type=str, default=datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"))
    ap.add_argument("--blocked-adjustments-registry", type=Path, default=DEFAULT_BLOCKED_ADJUSTMENTS_REGISTRY)
    ap.add_argument("--effective-adjustments-registry", type=Path, default=DEFAULT_EFFECTIVE_ADJUSTMENTS_REGISTRY)
    ap.add_argument("--effective-seed-top-k", type=int, default=5)
    ap.add_argument("--effective-min-accuracy-delta", type=float, default=0.0001)
    args = ap.parse_args()

    if args.validate_only:
        doc = _load_json(args.validate_only)
        errs = _validate_hypothesis(doc)
        js_errs = _try_jsonschema(doc, args.schema)
        errs.extend(js_errs)
        if errs:
            for e in errs:
                print(e, file=sys.stderr)
            return 1
        print("OK:", args.validate_only)
        return 0

    if not args.bundle.is_file():
        print(f"Bundle missing: {args.bundle}", file=sys.stderr)
        return 1

    bundle = _load_json(args.bundle)

    if args.gemini:
        doc = _run_gemini(args.bundle, model=args.model, timeout=args.timeout, bundle=bundle)
    elif args.stub:
        doc = _build_stub_from_bundle(bundle)
    else:
        score_doc = _load_json(args.score_json) if args.score_json.is_file() else {}
        ensemble_cfg = _load_json(args.ensemble_config) if args.ensemble_config.is_file() else {}
        previous_doc = _load_json(args.output) if args.output.is_file() else None
        doc = _build_ensemble_from_bundle(
            bundle,
            score_doc=score_doc,
            ensemble_cfg=ensemble_cfg,
            previous_doc=previous_doc,
        )
    blocked_keys = _read_blocked_adjustment_keys(args.blocked_adjustments_registry)
    effective_rows = _read_effective_adjustments(
        args.effective_adjustments_registry,
        min_accuracy_delta=args.effective_min_accuracy_delta,
    )
    doc = _inject_or_guard_proposed_changes(
        doc,
        run_id=args.run_id,
        blocked_keys=blocked_keys,
        effective_rows=effective_rows,
        effective_seed_top_k=args.effective_seed_top_k,
    )

    errs = _validate_hypothesis(doc)
    js_errs = _try_jsonschema(doc, args.schema)
    errs.extend(js_errs)
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
