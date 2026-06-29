# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.8, K:0.6, M:0.55}
# Balance: 86
# Purpose: B-track 4AI role router — lexicon shadow tagging + 4D hint mismatch [HYPO].
# Keywords: sasang, 4ai, btrack, lexicon-shadow, role-router
"""B-track Sasang (4AI) role router — read-only lexicon, shadow sidecar only."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SASANG_ROLES = ("taeyang", "taeeum", "soyang", "soeumin")
ROLE_OPS_SEMANTICS: dict[str, str] = {
    "taeyang": "scale_out_expansion",
    "taeeum": "persistence_archive",
    "soyang": "execution_transition",
    "soeumin": "stability_cooling",
}

ALLOWED_ROLE_HANDOFFS: dict[str, frozenset[str]] = {
    "taeyang": frozenset({"soyang", "taeeum", "soeumin"}),
    "soyang": frozenset({"soeumin", "taeeum", "taeyang"}),
    "taeeum": frozenset({"soyang", "soeumin", "taeyang"}),
    "soeumin": frozenset({"taeeum", "soyang"}),
}

STRONG_RULE_IDS = frozenset(
    {"disambiguation_required", "morphhb_anchor", "high_frequency_expansion"}
)

PSI_TYPE_TO_SASANG: dict[str, str] = {
    "Antecedent": "taeyang",
    "Intermediary": "soyang",
    "Constraints": "soeumin",
    "Consequent": "taeeum",
}

OPS_ROLE_REGISTRY: list[dict[str, str]] = [
    {
        "path": "scripts/core/master_codebook_lexicon_v1_bridge.py",
        "sasang_role": "taeeum",
        "ops_semantic": ROLE_OPS_SEMANTICS["taeeum"],
    },
    {
        "path": "scripts/run_logos_track_b_hot_reload_v1.py",
        "sasang_role": "soyang",
        "ops_semantic": ROLE_OPS_SEMANTICS["soyang"],
    },
    {
        "path": "scripts/build_logos_psi_logic_extraction_v1.py",
        "sasang_role": "taeyang",
        "ops_semantic": ROLE_OPS_SEMANTICS["taeyang"],
    },
    {
        "path": "scripts/build_logos_path_verification_gate_v1.py",
        "sasang_role": "soeumin",
        "ops_semantic": ROLE_OPS_SEMANTICS["soeumin"],
    },
    {
        "path": "scripts/run_logos_b2b_deterministic_chain_v1.py",
        "sasang_role": "soyang",
        "ops_semantic": ROLE_OPS_SEMANTICS["soyang"],
    },
    {
        "path": "scripts/build_btrack_sasang_lexicon_shadow_v1.py",
        "sasang_role": "soeumin",
        "ops_semantic": ROLE_OPS_SEMANTICS["soeumin"],
    },
]


@dataclass(frozen=True)
class RoleAssignment:
    sasang_role: str
    rule_id: str


def percentile_threshold(values: list[int], pct: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * pct))))
    return ordered[idx]


def pseudo_4d_from_normalized_form(normalized_form: str) -> dict[str, float]:
    """Deterministic pseudo-4D from lexicon surface form — metadata hint only [HYPO]."""
    digest = hashlib.sha256(normalized_form.encode("utf-8")).digest()
    s = digest[0] / 255.0
    l = digest[1] / 255.0
    k = digest[2] / 255.0
    m = max(0.05, 1.0 - (0.35 * s + 0.35 * l + 0.30 * k))
    return {"S": round(s, 6), "L": round(l, 6), "K": round(k, 6), "M": round(m, 6)}


def role_hint_from_4d(vector_4d: dict[str, float]) -> str:
    """Hint role from pseudo-4D — aligned to assignment heuristics [HYPO]."""
    s = float(vector_4d.get("S", 0.0))
    l = float(vector_4d.get("L", 0.0))
    k = float(vector_4d.get("K", 0.0))
    m = float(vector_4d.get("M", 0.0))
    if s >= 0.55:
        return "taeyang"
    if m >= 0.40:
        return "taeeum"
    if l >= k:
        return "soyang"
    return "soeumin"


def classify_lexicon_entry(ent: dict[str, Any], *, high_occ_threshold: int) -> RoleAssignment:
    occ = int(ent.get("occurrences") or 0)
    disamb = ent.get("morphhb_disambiguation")
    morph = ent.get("morphhb_chosen")
    match = str(ent.get("lexicon_match_method") or "")
    lang = str(ent.get("lang") or "")

    if disamb:
        return RoleAssignment("soeumin", "disambiguation_required")
    if morph:
        return RoleAssignment("taeeum", "morphhb_anchor")
    if occ >= high_occ_threshold:
        return RoleAssignment("taeyang", "high_frequency_expansion")
    if occ <= 3:
        return RoleAssignment("soeumin", "low_frequency_rare")
    if match == "strongs_norm":
        return RoleAssignment("soyang", "strongs_execution_lookup")
    if lang == "greek":
        return RoleAssignment("soyang", "greek_default_execution")
    return RoleAssignment("taeeum", "hebrew_default_persistence")


def role_mismatch(
    assigned: str,
    hint: str,
    *,
    vector_4d: dict[str, float],
    mismatch_distance_threshold: float = 0.55,
) -> tuple[bool, float]:
    if assigned == hint:
        return False, 0.0
    vals = [float(vector_4d.get(k, 0.0)) for k in ("S", "L", "K", "M")]
    spread = max(vals) - min(vals)
    distance = spread if assigned != hint else 0.0
    return distance >= mismatch_distance_threshold, round(distance, 4)


def handoff_allowed(source_role: str, target_role: str) -> bool:
    if source_role == target_role:
        return True
    return target_role in ALLOWED_ROLE_HANDOFFS.get(source_role, frozenset())


def build_lexicon_shadow(
    entries: list[dict[str, Any]],
    *,
    codebook_path: Path,
    codebook_sha256: str,
    mismatch_distance_threshold: float = 0.55,
    align_strong_rule_hints: bool = True,
) -> dict[str, Any]:
    occ_values = [int(e.get("occurrences") or 0) for e in entries]
    high_occ = percentile_threshold(occ_values, 0.75)

    tagged: list[dict[str, Any]] = []
    role_counts = {r: 0 for r in SASANG_ROLES}
    mismatch_rows: list[dict[str, Any]] = []

    for ent in entries:
        if not isinstance(ent, dict):
            continue
        atom_id = str(ent.get("atom_id") or "")
        nf = str(ent.get("normalized_form") or "")
        if not atom_id or not nf:
            continue
        assignment = classify_lexicon_entry(ent, high_occ_threshold=high_occ)
        vector_4d = pseudo_4d_from_normalized_form(nf)
        if align_strong_rule_hints and assignment.rule_id in STRONG_RULE_IDS:
            hint = assignment.sasang_role
            hint_source = "strong_rule_aligned"
        else:
            hint = role_hint_from_4d(vector_4d)
            hint_source = "pseudo_4d"
        is_mismatch, distance = role_mismatch(
            assignment.sasang_role,
            hint,
            vector_4d=vector_4d,
            mismatch_distance_threshold=mismatch_distance_threshold,
        )
        role_counts[assignment.sasang_role] += 1
        row = {
            "atom_id": atom_id,
            "normalized_form": nf,
            "sasang_role": assignment.sasang_role,
            "sasang_code": assignment.sasang_role,
            "rule_id": assignment.rule_id,
            "pseudo_4d_hint_role": hint,
            "hint_source": hint_source,
            "pseudo_4d": vector_4d,
            "class_mismatch": is_mismatch,
            "mismatch_distance": distance,
        }
        tagged.append(row)
        if is_mismatch:
            mismatch_rows.append(
                {
                    "atom_id": atom_id,
                    "assigned": assignment.sasang_role,
                    "hint": hint,
                    "distance": distance,
                    "rule_id": assignment.rule_id,
                }
            )

    total = len(tagged)
    mismatch_count = len(mismatch_rows)
    mismatch_rate = round(mismatch_count / total, 4) if total else 0.0

    return {
        "schema": "btrack_sasang_lexicon_shadow_v1",
        "version": "1.0.0",
        "lane": "track_b_hypo",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "non_gating": True,
        "track_a_bridge": False,
        "live_trading_bridge": False,
        "theology_to_sales_forbidden": True,
        "codebook_read_only": True,
        "codebook_path": str(codebook_path.resolve()),
        "codebook_sha256": codebook_sha256,
        "codebook_entry_count": total,
        "high_occurrence_threshold": high_occ,
        "align_strong_rule_hints": align_strong_rule_hints,
        "role_counts": role_counts,
        "mismatch_summary": {
            "mismatch_count": mismatch_count,
            "mismatch_rate": mismatch_rate,
            "escalation_required": mismatch_count > 0,
        },
        "entries": tagged,
        "mismatch_sample": mismatch_rows[:24],
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_codebook_entries(path: Path) -> list[dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != "master_codebook_lexicon_v1":
        raise ValueError(f"unexpected schema: {doc.get('schema')}")
    entries = doc.get("entries") or []
    return [e for e in entries if isinstance(e, dict)]


def build_psi_role_bridge(psi_doc: dict[str, Any]) -> dict[str, Any]:
    graph = psi_doc.get("logic_graph") or {}
    nodes = graph.get("nodes") or []
    bridged: list[dict[str, Any]] = []
    by_type: dict[str, list[dict[str, Any]]] = {
        "Antecedent": [],
        "Intermediary": [],
        "Constraints": [],
        "Consequent": [],
    }
    for node in nodes:
        if not isinstance(node, dict):
            continue
        psi_type = str(node.get("type") or "")
        expected = PSI_TYPE_TO_SASANG.get(psi_type, "soyang")
        row = {
            "node_id": node.get("id"),
            "psi_type": psi_type,
            "sasang_role": expected,
            "description": node.get("description"),
            "handoff_ok": handoff_allowed(expected, expected),
        }
        bridged.append(row)
        if psi_type in by_type:
            by_type[psi_type].append(row)

    document_chain = [row["sasang_role"] for row in bridged]
    document_violations: list[dict[str, Any]] = []
    for i in range(len(document_chain) - 1):
        if not handoff_allowed(document_chain[i], document_chain[i + 1]):
            document_violations.append(
                {"from": document_chain[i], "to": document_chain[i + 1], "index": i, "mode": "document_order"}
            )

    canonical_roles: list[str] = []
    for psi_type in ("Antecedent", "Intermediary", "Constraints", "Consequent"):
        bucket = by_type.get(psi_type) or []
        if bucket:
            canonical_roles.append(bucket[0]["sasang_role"])

    canonical_violations: list[dict[str, Any]] = []
    for i in range(len(canonical_roles) - 1):
        if not handoff_allowed(canonical_roles[i], canonical_roles[i + 1]):
            canonical_violations.append(
                {
                    "from": canonical_roles[i],
                    "to": canonical_roles[i + 1],
                    "index": i,
                    "mode": "canonical_psi_chain",
                }
            )

    types_present = sum(1 for bucket in by_type.values() if bucket)
    bridge_ok = types_present >= 4 and not canonical_violations

    return {
        "schema": "btrack_sasang_psi_role_bridge_v1",
        "version": "1.0.0",
        "lane": "track_b_hypo",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "structure_transplant_only": True,
        "theology_to_sales_forbidden": True,
        "track_a_bridge": False,
        "psi_type_to_sasang": PSI_TYPE_TO_SASANG,
        "bridged_nodes": bridged,
        "document_chain_roles": document_chain,
        "canonical_chain_roles": canonical_roles,
        "document_order_violations": document_violations,
        "canonical_chain_violations": canonical_violations,
        "handoff_violations": canonical_violations,
        "bridge_ok": bridge_ok,
        "psi_types_present": types_present,
    }


def build_ops_registry_doc() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for item in OPS_ROLE_REGISTRY:
        rel = item["path"]
        p = ROOT / rel
        rows.append(
            {
                **item,
                "exists": p.is_file(),
                "ops_semantic": ROLE_OPS_SEMANTICS[item["sasang_role"]],
            }
        )
    return {
        "schema": "btrack_sasang_ops_role_registry_v1",
        "version": "1.0.0",
        "lane": "track_b_hypo",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_bridge": False,
        "allowed_handoffs": {k: sorted(v) for k, v in ALLOWED_ROLE_HANDOFFS.items()},
        "ops_entries": rows,
    }


def validate_ops_handoff_chain(chain: list[str]) -> dict[str, Any]:
    violations: list[dict[str, str]] = []
    for i in range(len(chain) - 1):
        src, dst = chain[i], chain[i + 1]
        if not handoff_allowed(src, dst):
            violations.append({"from": src, "to": dst, "error": "class_mismatch_handoff"})
    return {
        "chain": chain,
        "ok": not violations,
        "violations": violations,
    }
