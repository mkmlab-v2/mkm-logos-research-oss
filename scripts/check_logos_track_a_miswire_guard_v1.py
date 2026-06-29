#!/usr/bin/env python3
"""Static guard: Logos narrative/concept_bridge must not wire to Track A execution chokepoints.

Exit 0 = no miswire detected on Tier-A chokepoints + risk profile contract.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "reports/logos_track_a_miswire_guard_v1_latest.json"
SCHEMA = "logos_track_a_miswire_guard_v1"

# Tier-A: new miswire here is a hard fail (not legacy nitro surfaces).
TIER_A_CHOKEPOINTS = (
    "projects/bitcoin-trading/scripts/run_conditional_action_gate_v1.py",
    "projects/bitcoin-trading/scripts/execute_binance_usdm_single_order_v1.py",
    "projects/bitcoin-trading/scripts/poc_binance_signal_webhook_spike_v1.py",
    "scripts/run_track_a_metering_live_wire_v1.py",
    "scripts/check_track_a_metering_band_gate.py",
    "scripts/run_track_a_shadow_corpus_eval.py",
    "scripts/athena_run_v1.py",
)

TRACK_A_MANIFESTS = (
    "docs/final/artifacts/track_a_shadow_corpus_input_manifest_latest.json",
    "docs/final/artifacts/track_a_metering_live_wire_v1_latest.json",
)

LOGOS_ARTIFACT_PATH_MARKERS = (
    "logos_concept_bridge",
    "logos_narrative_inter_hop",
    "narrative_template",
    "logos_bible_advancement",
    "logos_insight_bundle",
)

FORBIDDEN_SOURCE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bfrom\s+scripts\.build_logos_", "logos_builder_import"),
    (r"\bimport\s+.*logos_concept_bridge", "concept_bridge_import"),
    (r"\blogos_narrative_inter_hop\b", "narrative_inter_hop_ref"),
    (r"\blogos_concept_bridge\b", "concept_bridge_ref"),
    (r"\bnarrative_template\b.*\btrigger\b", "narrative_template_trigger"),
    (r"\blogos_regime_score\s*[><=!]=", "logos_score_threshold"),
    (r"\bconcept_bridge\b.*\bfinal_action\b", "concept_bridge_final_action"),
    (r"\bnarrative_template\b.*\bfinal_action\b", "narrative_template_final_action"),
)

RISK_FORBIDDEN_KEYS = frozenset(
    {
        "logos_gating_enabled",
        "narrative_template_trigger",
        "concept_bridge_trigger",
        "logos_final_action",
        "logos_trigger_action",
        "logos_narrative_gating",
    }
)

LEGACY_LOGOS_TRADING_SURFACES = (
    "projects/bitcoin-trading/src/integration/unified_trading_monitor.py",
    "projects/bitcoin-trading/src/strategy/crypto_nitro_live_strategy.py",
)

TIER1_READINESS = ROOT / "docs/final/artifacts/logos_oracle_cursor_inject_tier1_readiness_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _code_lines(text: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append((i, raw))
    return out


def check_tier_a_chokepoints(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    for rel in TIER_A_CHOKEPOINTS:
        path = root / rel.replace("/", "\\")
        if not path.is_file():
            checks.append({"check_id": f"chokepoint_present::{rel}", "pass": False, "detail": "missing"})
            errors.append(f"missing chokepoint: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        hits: list[str] = []
        for lineno, line in _code_lines(text):
            for pattern, label in FORBIDDEN_SOURCE_PATTERNS:
                if re.search(pattern, line, flags=re.IGNORECASE):
                    hits.append(f"L{lineno}:{label}")
        ok = not hits
        checks.append(
            {
                "check_id": f"tier_a_clean::{rel}",
                "pass": ok,
                "detail": "clean" if ok else "; ".join(hits[:8]),
            }
        )
        if not ok:
            errors.append(f"{rel}: {hits[0]}")
    return checks, errors


def _flatten_keys(obj: Any, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            full = f"{prefix}.{k}" if prefix else str(k)
            keys.add(full)
            keys |= _flatten_keys(v, full)
    elif isinstance(obj, list):
        for item in obj:
            keys |= _flatten_keys(item, prefix)
    return keys


def check_risk_profile(root: Path, risk_path: Path) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    if not risk_path.is_file():
        return (
            {
                "check_id": "risk_profile_contract",
                "pass": False,
                "detail": f"missing {risk_path.relative_to(root).as_posix()}",
            },
            [f"missing risk profile: {risk_path}"],
        )

    doc = _load_json(risk_path)
    flat = _flatten_keys(doc)
    forbidden_hits = sorted(k for k in flat if any(k.endswith(f".{fk}") or k == fk for fk in RISK_FORBIDDEN_KEYS))
    if forbidden_hits:
        errors.append(f"risk profile forbidden keys: {forbidden_hits[:5]}")

    tg = doc.get("trinity_governor")
    mode = ""
    logos_ack = False
    has_logos_score = False
    if isinstance(tg, dict):
        mode = str(tg.get("mode") or "").strip().upper()
        logos_ack = tg.get("logos_non_gating_ack") is True
        has_logos_score = tg.get("logos_regime_score") is not None

    if has_logos_score and not logos_ack:
        errors.append("trinity logos_regime_score present without logos_non_gating_ack")

    gb = doc.get("governance_bridge")
    if isinstance(gb, dict):
        for key in ("final_action_source", "gating_lens", "primary_lens"):
            val = str(gb.get(key) or "").lower()
            if "logos" in val and "non_gating" not in val and "non-gating" not in val:
                errors.append(f"governance_bridge.{key} logos without non_gating tag")

    ok = not errors
    return (
        {
            "check_id": "risk_profile_contract",
            "pass": ok,
            "detail": {
                "path": risk_path.relative_to(root).as_posix(),
                "mode": mode or None,
                "has_logos_regime_score": has_logos_score,
                "logos_non_gating_ack": logos_ack,
                "forbidden_key_hits": forbidden_hits,
            },
        },
        errors,
    )


def check_track_a_manifests(root: Path) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    hits: list[str] = []
    for rel in TRACK_A_MANIFESTS:
        path = root / rel.replace("/", "\\")
        if not path.is_file():
            continue
        blob = path.read_text(encoding="utf-8").lower()
        for marker in LOGOS_ARTIFACT_PATH_MARKERS:
            if marker in blob:
                hits.append(f"{rel}:{marker}")
    if hits:
        errors.append(f"track_a manifest logos dependency: {hits[0]}")
    return (
        {
            "check_id": "track_a_manifests_clean",
            "pass": not hits,
            "detail": hits or "no logos artifact paths in Track A manifests",
        },
        errors,
    )


def check_oracle_tier1_blocks(root: Path) -> dict[str, Any]:
    path = TIER1_READINESS if TIER1_READINESS.is_file() else root / TIER1_READINESS
    if not path.is_file():
        return {"check_id": "oracle_tier1_upgrade_blocked", "pass": True, "detail": "tier1 artifact missing (skip)"}
    doc = _load_json(path)
    blockers = [str(b) for b in (doc.get("full_upgrade_blockers") or [])]
    send_gate = str(doc.get("send_gate") or "").upper()
    tier2_ready = doc.get("tier2_cursor_rules_full_upgrade_ready")
    tier3_ready = doc.get("tier3_constitution_narrative_full_upgrade_ready")
    has_permanent_wall = any(
        "promotion_cascade" in b.lower() or "track a" in b.lower() or "live" in b.lower()
        for b in blockers
    )
    if tier2_ready and send_gate == "OPEN":
        ok = has_permanent_wall
    else:
        has_track_blocker = any(
            "track a" in b.lower() or "send_gate" in b.lower() or "promotion_cascade" in b.lower()
            for b in blockers
        )
        ok = send_gate == "HOLD" and tier3_ready is False and has_track_blocker and len(blockers) >= 2
    return {
        "check_id": "oracle_tier1_upgrade_blocked",
        "pass": ok,
        "detail": {
            "send_gate": send_gate,
            "tier2_cursor_rules_full_upgrade_ready": tier2_ready,
            "tier3_constitution_narrative_full_upgrade_ready": tier3_ready,
            "blocker_count": len(blockers),
            "has_permanent_wall_blocker": has_permanent_wall,
        },
    }


def collect_legacy_warnings(root: Path) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    legacy_patterns = (
        (r"\blogos_risk_multiplier\b", "logos_risk_multiplier"),
        (r"\blogos_timeline\b", "logos_timeline"),
        (r"\bLogosNitroProtocol\b", "logos_nitro_protocol"),
    )
    for rel in LEGACY_LOGOS_TRADING_SURFACES:
        path = root / rel.replace("/", "\\")
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        found = [label for pat, label in legacy_patterns if re.search(pat, text)]
        if found:
            warnings.append(
                {
                    "surface": rel,
                    "patterns": found,
                    "note": "legacy coupling — observation/remediation tracked; not Tier-A chokepoint",
                }
            )
    return warnings


def build_report(root: Path, risk_path: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    errors: list[str] = []

    choke_checks, choke_errors = check_tier_a_chokepoints(root)
    checks.extend(choke_checks)
    errors.extend(choke_errors)

    risk_check, risk_errors = check_risk_profile(root, risk_path)
    checks.append(risk_check)
    errors.extend(risk_errors)

    manifest_check, manifest_errors = check_track_a_manifests(root)
    checks.append(manifest_check)
    errors.extend(manifest_errors)

    checks.append(check_oracle_tier1_blocks(root))

    legacy_warnings = collect_legacy_warnings(root)
    ok = len(errors) == 0 and all(c.get("pass") for c in checks)
    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "ok": ok,
        "status": "PASS" if ok else "FAIL",
        "checks": checks,
        "errors": errors,
        "legacy_warnings": legacy_warnings,
        "tier_a_chokepoint_count": len(TIER_A_CHOKEPOINTS),
        "reproducible_command": "py scripts/check_logos_track_a_miswire_guard_v1.py",
        "boundary_ack": "Tier-A chokepoint static guard — not a full repo AST ban on Logos Track C/B surfaces.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument(
        "--risk-profile",
        type=Path,
        default=ROOT / "projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json",
    )
    ap.add_argument("--output-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = args.workspace_root.resolve()
    risk = args.risk_profile if args.risk_profile.is_absolute() else root / args.risk_profile
    report = build_report(root, risk)

    out = args.output_json if args.output_json.is_absolute() else root / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"logos_track_a_miswire_guard={report['status']} ok={report['ok']} out={out}")
        if report["errors"]:
            for err in report["errors"]:
                print(f"FAIL: {err}", file=__import__("sys").stderr)
        if report["legacy_warnings"]:
            print(f"legacy_warnings={len(report['legacy_warnings'])} (acknowledged, non-blocking)")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
