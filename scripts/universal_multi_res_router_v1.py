#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Universal multi-resolution router v1 — deterministic SSOT (B-track).

Ollama shallow router is an optional inference_adapter; keyword heuristics always available.
Commercial gateway hooks are pre-registered stubs (metering off, HOLD frozen).

  py scripts/universal_multi_res_router_v1.py --query "사상 stress 계산"
  py scripts/universal_multi_res_router_v1.py --query "Track A live trading 승격" 
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.logos_umr_lookup_context_v1 import build_logos_umr_lookup_context  # noqa: E402
from scripts.core.jema_os_domain_plugin_registry_v2_lib_v1 import (  # noqa: E402
    build_slot_overlay,
    known_umr_lanes,
    plugin_row_from_v2_slot,
    registry_v2_ref,
    resolve_slot_for_umr_domain,
)
DEFAULT_OUT = ROOT / "docs/final/artifacts/universal_multi_res_router_v1_latest.json"
PLUGIN_REGISTRY = ROOT / "docs/final/artifacts/universal_multi_res_plugin_registry_v1_latest.json"
SHALLOW_OUTPUT_SCHEMA = "ollama_shallow_router_output_v1"
SHALLOW_HANDOFF_SCHEMA = "ollama_shallow_router_handoff_v1"
DEFAULT_SHALLOW_CANDIDATES: tuple[Path, ...] = (
    ROOT / "docs/final/artifacts/mkm_research_router_shallow_v1_latest.json",
    ROOT / "reports/ollama_shallow_router_handoff_v1_latest.json",
    ROOT / "docs/final/schemas/ollama_shallow_router_output_v1.example.json",
)
VERSION = "1.1.0"
OLLAMA_MODEL_PIN = "mkm-shallow-router-v1"
OLLAMA_HOST_DEFAULT = "http://127.0.0.1:11434"

KERNEL_FIREWALL = [
    "production_gematria_kernel",
    "vector_4d_merge",
    "track_a_compression_floor",
    "start_live_trading.py",
    "patient_care_bundle_clinical_gating",
]

FORBIDDEN_RULES: tuple[tuple[str, str], ...] = (
    (r"track\s*a.*(promot|승격|go\b)", "track_a_auto_promotion"),
    (r"live\s*trad|실매매|start_live_trading", "live_trading_trigger"),
    (r"임상\s*(진단|처방)|clinical\s*diagnos", "clinical_diagnosis_output"),
    (r"dt\s*/\s*dx|역시간\s*통일", "forbidden_dt_dx_unification"),
    (r"75식\s*봉인\s*완료|99\.2%\s*전역", "forbidden_75_formula_global_claim"),
    (r"gematria\s*kernel\s*merge|vector_4d\s*합선", "production_gematria_kernel_merge"),
    (r"promotion_to_a_track_allowed\s*=\s*true", "explicit_a_track_promotion_flag"),
    (r"send_gate\s*:\s*send\b", "forbidden_send_gate_override"),
)

VISION_PAT = re.compile(
    r"완벽\s*통합|0%\s*환각|단일\s*대통합\s*이론|TOE\s*완성|우주\s*통일\s*수식",
    re.IGNORECASE,
)

DOMAIN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("sasang", re.compile(r"사상|sasang|체질|병증|금화교역|보명지주", re.I)),
    ("logos", re.compile(r"logos|성경|게마트리아|gematria|창세기|요한계시", re.I)),
    ("myeongni", re.compile(r"명리|사주|만세력|myeongni|십신|육친", re.I)),
    (
        "enterprise_herbs_formulas",
        re.compile(r"한방|본초|방제|탕액|herbs|formulas|처방전", re.I),
    ),
    ("science", re.compile(r"\buft\b|unified.?field|물리\s*엔진|geumhwa|금화교역\s*인덱스", re.I)),
    ("oracle", re.compile(r"oracle|예언|prophecy|brier", re.I)),
    ("compression", re.compile(r"압축|compression|token\s*api|prism", re.I)),
    ("design", re.compile(r"design|쇼룸|showroom|jemaai|ui\b", re.I)),
    ("devops", re.compile(r"ci\b|github\s*action|deploy|workflow|pytest", re.I)),
    ("infra", re.compile(r"infra|vps|ollama|gpu|스케줄", re.I)),
)

LOW_RES_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"stress\s*계산|0\.6\s*\*\s*te|persona\s*grid|build_sasang_persona", re.I),
    re.compile(r"exit\s*0|pytest\b|run_lens_sasang", re.I),
    re.compile(r"\bcsv\b|ohlcv|jsonl|로그\s*파일|fixed\s*schema", re.I),
    re.compile(r"인벤토리\s*갱신|context_inventory", re.I),
    re.compile(r"geumhwa_index|unified_field_theory_engine|run_lens_", re.I),
    re.compile(r"^py\s+scripts/", re.I),
)

HIGH_RES_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"학파\s*충돌|symbolic\s*join|graphrag|deep\s*report", re.I),
    re.compile(r"908\s*자산|전수조사|장기기억|ltm\s*graph|digested_facts", re.I),
    re.compile(r"마르코프|베이지안|pre-?reg|oos\s*spot", re.I),
    re.compile(r"기대\s*vs\s*팩트|expectation_vs_fact", re.I),
)

_FALLBACK_PLUGINS: dict[str, dict[str, Any]] = {
    "sasang": {
        "plugin_id": "sasang_context_v1",
        "expectation_matrix_ref": "docs/final/artifacts/sasang_expectation_vs_fact_matrix_v1.md",
        "inventory_artifact_ref": "docs/final/artifacts/sasang_context_inventory_v1_latest.json",
        "agent_read_order": [
            "docs/final/artifacts/sasang_expectation_vs_fact_matrix_v1.md",
            "docs/final/artifacts/sasang_context_inventory_v1_latest.json",
            "docs/final/artifacts/SASANG_DYNAMICS_V1_CONTRACT.json",
            "docs/final/artifacts/sasang_dynamics_btrack_milestone_v1_latest.json",
            "docs/final/artifacts/sasang_interpretive_insight_bundle_v1_latest.json",
            "docs/final/artifacts/sasang_pyobyeong_insight_cards_v1_latest.json",
            "docs/research/IJEOMA_PYOBYEONG_BYEONGJEUNG_LIT_REVIEW_v1.md",
            "reports/sasang_ablation_matrix_signoff_v1_latest.json",
        ],
        "low_res_runners": [
            "scripts/build_sasang_persona_grid_v1.py",
            "scripts/run_lens_sasang.py",
            "scripts/sasang_context_inventory_v1.py",
            "scripts/build_ijeoma_pyobyeong_dr_pack_v1.py",
            "scripts/run_sasang_dynamics_unified_adapter_v1.py",
        ],
        "hold_flags": [],
        "u3_tier": "full",
    },
    "logos": {
        "plugin_id": "logos_lens_v1",
        "expectation_matrix_ref": "docs/final/artifacts/logos_expectation_vs_fact_matrix_v1_lite.md",
        "inventory_artifact_ref": "docs/final/artifacts/logos_context_inventory_v1_latest.json",
        "agent_read_order": [
            "docs/final/artifacts/logos_expectation_vs_fact_matrix_v1_lite.md",
            "docs/final/artifacts/logos_context_inventory_v1_latest.json",
            "docs/final/artifacts/LOGOS_INDEPENDENT_LENS_V0_CONTRACT.json",
            "docs/final/artifacts/logos_independent_lens_latest.json",
            "docs/final/artifacts/logos_verse_lexicon_join_sidecar_v2_corpus_full_latest.json",
            "reports/logos_graphrag_router_axis_order_regression_v1_latest.json",
        ],
        "sidecar_v2_corpus_full_ref": (
            "docs/final/artifacts/logos_verse_lexicon_join_sidecar_v2_corpus_full_latest.json"
        ),
        "graphrag_axis_order_audit_ref": (
            "reports/logos_graphrag_router_axis_order_regression_v1_latest.json"
        ),
        "low_res_runners": [
            "scripts/run_lens_logos.py",
            "scripts/logos_context_inventory_v1.py",
            "scripts/check_logos_graphrag_router_axis_order_regression_v1.py",
        ],
        "hold_flags": [],
        "u3_tier": "lite_plus",
    },
    "myeongni": {
        "plugin_id": "myeongni_lens_v1",
        "expectation_matrix_ref": "docs/final/artifacts/myeongni_expectation_vs_fact_matrix_v1_lite.md",
        "inventory_artifact_ref": "docs/final/artifacts/myeongni_context_inventory_v1_latest.json",
        "agent_read_order": [
            "docs/final/artifacts/myeongni_expectation_vs_fact_matrix_v1_lite.md",
            "docs/final/artifacts/myeongni_independent_lens_latest.json",
        ],
        "low_res_runners": ["scripts/run_lens_myeongni.py", "scripts/myeongni_context_inventory_v1.py"],
        "hold_flags": [],
        "u3_tier": "lite",
    },
    "science": {
        "plugin_id": "uft_core_v1_stub",
        "agent_read_order": ["tools/core/unified_field_theory_engine.py"],
        "low_res_runners": ["tools/core/unified_field_theory_engine.py"],
        "hold_flags": ["dt_dx_unified_field_equation"],
        "u3_tier": "stub",
    },
    "compression": {
        "plugin_id": "compression_track_a_observability_v1",
        "agent_read_order": ["docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md"],
        "low_res_runners": ["scripts/compression_token_api_v2_stub.py"],
        "hold_flags": [],
        "u3_tier": "lite",
    },
    "ops": {
        "plugin_id": "mkm_ops_default_v1",
        "agent_read_order": ["docs/final/artifacts/mkm_chat_resume_pack_latest.md"],
        "low_res_runners": ["scripts/mkm_intent_router_local_v1.py"],
        "hold_flags": [],
        "u3_tier": "lite",
    },
}


def _load_plugin_registry() -> dict[str, dict[str, Any]]:
    if PLUGIN_REGISTRY.is_file():
        try:
            doc = json.loads(PLUGIN_REGISTRY.read_text(encoding="utf-8-sig"))
            plugins = doc.get("plugins")
            if isinstance(plugins, dict) and plugins:
                return {str(k): dict(v) for k, v in plugins.items() if isinstance(v, dict)}
        except (OSError, json.JSONDecodeError):
            pass
    return dict(_FALLBACK_PLUGINS)


def _plugin_registry_ref() -> str:
    return (
        str(PLUGIN_REGISTRY.relative_to(ROOT)).replace("\\", "/")
        if PLUGIN_REGISTRY.is_file()
        else "docs/final/artifacts/universal_multi_res_plugin_registry_v1_latest.json"
    )


DOMAIN_PLUGINS: dict[str, dict[str, Any]] = _load_plugin_registry()


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def detect_infrastructure_mode() -> str:
    explicit = (os.environ.get("MKM_INFRASTRUCTURE_MODE") or "").strip().lower()
    if explicit in {"local_pc", "headless_ci", "cloud_vps_api"}:
        return explicit
    if os.environ.get("CI", "").lower() in {"1", "true", "yes"} or os.environ.get("GITHUB_ACTIONS"):
        return "headless_ci"
    if os.environ.get("MKM_CLOUD_VPS_API", "").lower() in {"1", "true", "yes"}:
        return "cloud_vps_api"
    return "local_pc"


def _normalize_shallow_packet(raw: dict[str, Any]) -> dict[str, Any] | None:
    schema = str(raw.get("schema") or "")
    if schema == SHALLOW_OUTPUT_SCHEMA:
        return raw
    if schema == SHALLOW_HANDOFF_SCHEMA:
        hint = raw.get("lens_route_hint") if isinstance(raw.get("lens_route_hint"), dict) else {}
        coords = raw.get("coordinates_slkm") if isinstance(raw.get("coordinates_slkm"), dict) else {}
        anchors = raw.get("anchor_ids") if isinstance(raw.get("anchor_ids"), list) else []
        nsm = raw.get("nsm_prime_tags") if isinstance(raw.get("nsm_prime_tags"), list) else []
        domain = str(hint.get("domain_tag") or "").strip().lower()
        if not domain:
            return None
        return {
            "schema": SHALLOW_OUTPUT_SCHEMA,
            "research_only": True,
            "send_gate": "HOLD",
            "hypothesis_class": "HYPO",
            "domain_tag": domain,
            "coordinates": coords,
            "anchor_ids": [str(x) for x in anchors[:3]],
            "nsm_prime_tags": [str(x) for x in nsm],
            "parse_status": "handoff_compat",
        }
    rows = raw.get("rows")
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            parsed = row.get("parsed_output")
            if isinstance(parsed, dict) and parsed.get("schema") == SHALLOW_OUTPUT_SCHEMA:
                return parsed
    return None


def _load_shallow_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    return _normalize_shallow_packet(raw)


def resolve_shallow_packet(
    explicit: Path | None = None,
    *,
    infrastructure_mode: str | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    if explicit is not None:
        path = explicit if explicit.is_absolute() else (ROOT / explicit)
        shallow = _load_shallow_json(path)
        if shallow:
            try:
                ref = str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
            except ValueError:
                ref = str(path).replace("\\", "/")
            return shallow, ref
        return None, None
    if infrastructure_mode not in {None, "local_pc"}:
        return None, None
    if os.environ.get("MKM_UNIVERSAL_ROUTER_AUTO_SHALLOW", "").lower() in {"0", "false", "no"}:
        return None, None
    for candidate in DEFAULT_SHALLOW_CANDIDATES:
        shallow = _load_shallow_json(candidate)
        if shallow:
            return shallow, str(candidate.relative_to(ROOT)).replace("\\", "/")
    return None, None


def ollama_reachable(host: str = OLLAMA_HOST_DEFAULT, timeout_sec: float = 0.8) -> bool:
    if os.environ.get("MKM_OLLAMA_ROUTER_DISABLED", "").lower() in {"1", "true", "yes"}:
        return False
    url = host.rstrip("/") + "/api/tags"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def classify_domain(query: str, shallow: dict[str, Any] | None) -> str:
    v2_lanes = known_umr_lanes()
    if shallow and shallow.get("domain_tag"):
        tag = str(shallow["domain_tag"]).strip().lower()
        if tag in DOMAIN_PLUGINS or tag in v2_lanes or tag in {
            "oracle",
            "infra",
            "devops",
            "design",
            "science",
        }:
            return tag
    for name, pat in DOMAIN_PATTERNS:
        if pat.search(query):
            return name
    return "unclassified"


def scan_forbidden(query: str) -> list[str]:
    hits: list[str] = []
    for pat, rule_id in FORBIDDEN_RULES:
        if re.search(pat, query, re.IGNORECASE):
            hits.append(rule_id)
    return hits


def complexity_score(query: str, *, high_signals: int, low_signals: int, forbidden: bool) -> float:
    if forbidden:
        return 1.0
    base = min(1.0, len(query) / 400.0)
    base += 0.15 * high_signals
    base -= 0.12 * low_signals
    return max(0.0, min(1.0, base))


def resolve_plugin(domain: str) -> dict[str, Any]:
    lane = "logos" if domain == "oracle" else domain
    v2_slot = resolve_slot_for_umr_domain(lane)
    if lane in DOMAIN_PLUGINS:
        plug = dict(DOMAIN_PLUGINS[lane])
    elif v2_slot:
        plug = plugin_row_from_v2_slot(v2_slot)
    else:
        plug = dict(DOMAIN_PLUGINS["ops"])
        plug["plugin_id"] = f"ops_fallback_for_{domain or 'unclassified'}"
    out: dict[str, Any] = {
        "plugin_id": plug["plugin_id"],
        "agent_read_order": list(plug.get("agent_read_order") or []),
        "low_res_runners": list(plug.get("low_res_runners") or []),
        "hold_flags": list(plug.get("hold_flags") or []),
        "u3_tier": str(plug.get("u3_tier") or "lite"),
    }
    for k, v in plug.items():
        if k.endswith("_ref") and v:
            out[k] = v
        if k in {"slot_id", "slot_kind"} and v:
            out[k] = v
    return out


def route_query(
    query: str,
    *,
    command: str | None = None,
    shallow: dict[str, Any] | None = None,
    shallow_artifact_ref: str | None = None,
    infrastructure_mode: str | None = None,
    generated_at_utc: str | None = None,
) -> dict[str, Any]:
    text = f"{query} {command or ''}".strip()
    forbidden_hits = scan_forbidden(text)
    infra = infrastructure_mode or detect_infrastructure_mode()

    ollama_live = infra == "local_pc" and ollama_reachable()
    shallow_active = bool(shallow and shallow.get("schema") == SHALLOW_OUTPUT_SCHEMA)
    use_ollama_adapter = shallow_active or ollama_live
    provider = "ollama" if use_ollama_adapter else "keyword_heuristics"
    fallback = not use_ollama_adapter

    domain = classify_domain(text, shallow)
    high_signals = sum(1 for p in HIGH_RES_PATTERNS if p.search(text))
    low_signals = sum(1 for p in LOW_RES_PATTERNS if p.search(text))

    if forbidden_hits:
        resolution_tier = "hold_gate"
        epistemic_grade = "FORBIDDEN"
        fixed_schema_pass = False
        ltm_depth = 0.0
    elif VISION_PAT.search(text):
        resolution_tier = "hold_gate"
        epistemic_grade = "VISION"
        fixed_schema_pass = False
        ltm_depth = 0.0
        forbidden_hits = forbidden_hits + ["vision_overclaim_pattern"]
    elif low_signals >= 1 and high_signals == 0 and len(text) < 220:
        resolution_tier = "low_res"
        epistemic_grade = "FACT"
        fixed_schema_pass = True
        ltm_depth = 0.0
    elif high_signals >= 1 or len(text) >= 220:
        resolution_tier = "high_res"
        epistemic_grade = "HYPO" if VISION_PAT.search(text) is None else "VISION"
        fixed_schema_pass = False
        ltm_depth = min(1.0, 0.45 + 0.1 * high_signals)
    else:
        resolution_tier = "high_res"
        epistemic_grade = "HYPO"
        fixed_schema_pass = False
        ltm_depth = 0.35

    plugin = resolve_plugin(domain if domain != "unclassified" else "ops")
    low_res_action: dict[str, Any] | None = None
    if resolution_tier == "low_res" and plugin["low_res_runners"]:
        low_res_action = {
            "runner": plugin["low_res_runners"][0],
            "reason_ko": "canon §9 고정 스키마·결정론 runner 매칭",
        }

    shallow_compat: dict[str, Any] | None = None
    if shallow:
        shallow_compat = {
            "domain_tag": shallow.get("domain_tag"),
            "coordinates": shallow.get("coordinates"),
            "anchor_ids": shallow.get("anchor_ids"),
        }
        if shallow_artifact_ref:
            shallow_compat["artifact_ref"] = shallow_artifact_ref
        if shallow.get("domain_tag") and resolution_tier != "hold_gate":
            domain = str(shallow["domain_tag"])
            plugin = resolve_plugin(domain)

    doc: dict[str, Any] = {
        "schema": "universal_multi_res_router_v1",
        "version": VERSION,
        "generated_at_utc": generated_at_utc or _utc_now(),
        "rail": "B_TRACK",
        "research_only": True,
        "send_gate": "HOLD",
        "promotion_to_a_track_allowed": False,
        "input": {"query": query, **({"command": command} if command else {})},
        "infrastructure_mode": infra,
        "inference_adapter": {
            "provider": provider,
            "model_version_pin": OLLAMA_MODEL_PIN if provider == "ollama" else "keyword_heuristics_v1",
            "fallback_triggered": fallback,
            **({"ollama_host": OLLAMA_HOST_DEFAULT} if provider == "ollama" else {}),
            **(
                {"shallow_router_schema_compat": SHALLOW_OUTPUT_SCHEMA}
                if provider == "ollama"
                else {}
            ),
        },
        "commercial_gateway_hooks": {
            "api_route": "/api/v1/lens/route",
            "metering_enabled": False,
            "quota_limit_bypass": False,
            "stub_status": "pre_registration_only",
        },
        "governance_override": {
            "send_gate": "HOLD",
            "promotion_to_a_track_allowed": False,
            "human_review_required": True,
        },
        "resolution_tier": resolution_tier,
        "epistemic_grade": epistemic_grade,
        "domain_tag": domain if domain != "unclassified" else "ops",
        "fixed_schema_pass": fixed_schema_pass,
        "required_ltm_depth": ltm_depth,
        "complexity_score": complexity_score(
            text, high_signals=high_signals, low_signals=low_signals, forbidden=bool(forbidden_hits)
        ),
        "forbidden_hits": forbidden_hits,
        "routing_overlay_policy": {
            "mode": "routing_hints_only",
            "must_not_merge_into_kernel": list(KERNEL_FIREWALL),
            "sidecar_schema_ref": "docs/final/schemas/sasang_routing_sidecar_on_gematria_path_v1.schema.json",
        },
        "domain_plugin": plugin,
        "plugin_registry_ref": _plugin_registry_ref(),
        "jema_os_plugin_registry_v2_ref": registry_v2_ref(),
        "domain_plugin_slot_v2": build_slot_overlay(domain if domain != "unclassified" else "ops"),
        "reproduce_command": (
            f'py scripts/universal_multi_res_router_v1.py --query "{query.replace(chr(34), "")}"'
        ),
    }
    if shallow_compat:
        doc["shallow_router_compat"] = shallow_compat
    if low_res_action:
        doc["low_res_action"] = low_res_action
    if domain in ("logos", "oracle"):
        doc["logos_lookup_context"] = build_logos_umr_lookup_context()
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query", required=True, help="User query or command intent text")
    ap.add_argument("--command", default=None, help="Optional shell command context")
    ap.add_argument("--shallow-json", type=Path, help="Optional ollama_shallow_router_output_v1 JSON")
    ap.add_argument(
        "--infrastructure-mode",
        choices=["local_pc", "headless_ci", "cloud_vps_api"],
        default=None,
    )
    ap.add_argument("-o", "--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--append-replay",
        action="store_true",
        help="Append validated audit row to universal_multi_res_router replay JSONL",
    )
    ap.add_argument(
        "--replay-jsonl",
        type=Path,
        default=None,
        help="Replay JSONL path (default: reports/universal_multi_res_router_replay_v1.jsonl)",
    )
    args = ap.parse_args()

    infra = args.infrastructure_mode or detect_infrastructure_mode()
    shallow, shallow_ref = resolve_shallow_packet(args.shallow_json, infrastructure_mode=infra)

    doc = route_query(
        args.query,
        command=args.command,
        shallow=shallow,
        shallow_artifact_ref=shallow_ref,
        infrastructure_mode=infra,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    if args.append_replay:
        import importlib.util

        replay_lib_path = Path(__file__).resolve().parent / "universal_multi_res_router_replay_lib_v1.py"
        spec = importlib.util.spec_from_file_location(
            "universal_multi_res_router_replay_lib_v1", replay_lib_path
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"failed to load replay lib: {replay_lib_path}")
        replay_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(replay_mod)
        row = replay_mod.append_replay_row(
            doc,
            source_artifact_path=args.out,
            jsonl_path=args.replay_jsonl,
        )
        replay_path = args.replay_jsonl or (
            Path(__file__).resolve().parents[1] / "reports/universal_multi_res_router_replay_v1.jsonl"
        )
        print(f"REPLAY: {replay_path} event_id={row['event_id']}")
    print(
        json.dumps(
            {
                "resolution_tier": doc["resolution_tier"],
                "epistemic_grade": doc["epistemic_grade"],
                "domain_tag": doc["domain_tag"],
                "inference_adapter": doc["inference_adapter"]["provider"],
                "fallback_triggered": doc["inference_adapter"]["fallback_triggered"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
