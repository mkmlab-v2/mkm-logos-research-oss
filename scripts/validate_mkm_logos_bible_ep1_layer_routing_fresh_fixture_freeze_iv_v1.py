#!/usr/bin/env python3
"""EP1 layer-routing fresh fixture freeze — independent validator (builder ≠ checker).

IV output is written outside the frozen root (read-only w.r.t. freeze_v2 bytes).
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FROZEN_ROOT = ROOT / "docs/research/logos/bible_adversarial/ep1_layer_routing_fresh_fixture_freeze_v2"
IV_OUT = ROOT / "docs/final/artifacts/mkm_logos_bible_ep1_layer_routing_fresh_fixture_freeze_iv_v1_latest.json"
EP1_PARENT = ROOT / "docs/research/logos/bible_adversarial/kim_hakchul_bad_question_ep1_v1"
PRIORITY_DIR = EP1_PARENT / "post_fresh_multiroot_priority_boundary_disposition_v1"

REQUIRED = [
    "BIBLE_EP1_LAYER_ROUTING_CONTRACT_V1.json",
    "BIBLE_EP1_LAYER_ROUTING_PARENT_INTEGRITY_LOCK_V1.json",
    "BIBLE_EP1_LAYER_ROUTING_FRESHNESS_CLASSIFICATION_V1.json",
    "BIBLE_EP1_LAYER_ROUTING_EVIDENCE_CEILING_V1.json",
    "BIBLE_EP1_LAYER_ROUTING_CLEAN_ROOM_AUDIT_V1.json",
    "BIBLE_EP1_LAYER_ROUTING_CONTAMINATION_AUDIT_V1.json",
    "BIBLE_EP1_LAYER_ROUTING_FIXTURE_MANIFEST_V1.json",
    "BIBLE_EP1_LAYER_ROUTING_LOGICAL_FIXTURES_V1.jsonl",
    "BIBLE_EP1_LAYER_ROUTING_HIDDEN_GOLD_V1.jsonl",
    "BIBLE_EP1_LAYER_ROUTING_FREEZE_SEAL_V1.json",
]

FAMILIES = tuple(f"LR{i}" for i in range(1, 17))
LAYER_IDS = ("TEXT", "HISTORY", "TRADITION", "INTERPRETATION", "THEOLOGY")
GOLD_REQUIRED = [
    "EXPECTED_PRIMARY_LAYER",
    "EXPECTED_SECONDARY_LAYERS",
    "EXPECTED_SOURCE_ROLE",
    "EXPECTED_CLAIM_ROLE",
    "EXPECTED_MULTI_LAYER_REQUIRED",
    "EXPECTED_LAYER_TRANSITION_FORBIDDEN",
    "EXPECTED_REGISTER",
    "EXPECTED_PROVENANCE_TYPE",
]
DECIDE_FROZEN = "LOGOS_BIBLE_EP1_LAYER_ROUTING_FRESH_FIXTURES_FROZEN"
FRESHNESS_REQUIRED = "NEW_GENERATION_FROM_PRIORITY_DISPOSITION"
FIXTURE_N = 32

PINNED_LOGICAL = "5f6321607f8ffd3af9f80c87492f7f8db6c085c3d37383309b1abbbf076c4931"
PINNED_GOLD = "2ea740f5b761cae68522fcdc4bb04612590572e534c1c229b26e2d8a94579cab"

PINNED_PARENT = {
    "ep1_logical_fixtures": "a4b513d8386288b9c77fa475bdcf9e6a2f89dd18aed5649c8097b2da578684cf",
    "ep1_hidden_gold": "b6d0b18268005039f5510e3c9f25f0e9da5152e77da255a30489b922006cacdc",
    "ep1_freeze_seal": "e40ad30c866b5e5e75f86cfb3064e627f86288e50a5f1cd6ebe0ca28ac6e8aef",
    "priority_result": "05643eb4965ddb6e04722b662bf73ab3dbe23647549bf86294b4b9baa014f119",
}

REQUIRED_MANIFEST_HASH_KEYS = (
    "logical_fixtures_jsonl",
    "hidden_gold_jsonl",
    "parent_integrity_lock",
)
REQUIRED_PARENT_INTEGRITY_KEYS = tuple(PINNED_PARENT.keys())

PARENT_FILES = {
    "ep1_logical_fixtures": EP1_PARENT / "BIBLE_EP1_LOGICAL_FIXTURES_V1.jsonl",
    "ep1_hidden_gold": EP1_PARENT / "BIBLE_EP1_HIDDEN_GOLD_V1.jsonl",
    "ep1_freeze_seal": EP1_PARENT / "BIBLE_EP1_FREEZE_SEAL_V1.json",
    "priority_result": PRIORITY_DIR / "BIBLE_EP1_PRIORITY_BOUNDARY_RESULT_V1.json",
}


@dataclass
class ValidationResult:
    iv_pass: bool
    decide: str
    defects: list[str] = field(default_factory=list)
    checks: list[dict[str, Any]] = field(default_factory=list)
    logical_hash: str | None = None
    gold_hash: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_jsonl(p: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def collect_frozen_file_hashes(frozen_root: Path) -> dict[str, str]:
    return {p.name: sha_file(p) for p in sorted(frozen_root.iterdir()) if p.is_file()}


def write_json(p: Path, obj: dict[str, Any]) -> str:
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    p.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def run_validation(
    frozen_root: Path,
    *,
    parent_files: dict[str, Path] | None = None,
    pinned_parent: dict[str, str] | None = None,
) -> ValidationResult:
    parent_files = parent_files or PARENT_FILES
    pinned_parent = pinned_parent or PINNED_PARENT
    checks: list[dict[str, Any]] = []
    defects: list[str] = []

    logical_path = frozen_root / "BIBLE_EP1_LAYER_ROUTING_LOGICAL_FIXTURES_V1.jsonl"
    gold_path = frozen_root / "BIBLE_EP1_LAYER_ROUTING_HIDDEN_GOLD_V1.jsonl"
    manifest_path = frozen_root / "BIBLE_EP1_LAYER_ROUTING_FIXTURE_MANIFEST_V1.json"
    seal_path = frozen_root / "BIBLE_EP1_LAYER_ROUTING_FREEZE_SEAL_V1.json"
    parent_lock_path = frozen_root / "BIBLE_EP1_LAYER_ROUTING_PARENT_INTEGRITY_LOCK_V1.json"
    freshness_path = frozen_root / "BIBLE_EP1_LAYER_ROUTING_FRESHNESS_CLASSIFICATION_V1.json"
    ceiling_path = frozen_root / "BIBLE_EP1_LAYER_ROUTING_EVIDENCE_CEILING_V1.json"
    contract_path = frozen_root / "BIBLE_EP1_LAYER_ROUTING_CONTRACT_V1.json"
    clean_path = frozen_root / "BIBLE_EP1_LAYER_ROUTING_CLEAN_ROOM_AUDIT_V1.json"
    contam_path = frozen_root / "BIBLE_EP1_LAYER_ROUTING_CONTAMINATION_AUDIT_V1.json"

    logical_hash: str | None = None
    gold_hash: str | None = None

    if not frozen_root.is_dir():
        checks.append({"check": "frozen_root", "pass": False, "detail": "missing"})
        defects.append("FROZEN_ROOT_MISSING")
        return _finalize(defects, checks, logical_hash, gold_hash)

    missing = [f for f in REQUIRED if not (frozen_root / f).is_file()]
    checks.append({"check": "required_artifacts", "pass": not missing, "missing": missing})
    if missing:
        defects.append("REQUIRED_ARTIFACTS_MISSING")

    # Parent immutability — fail-closed on missing or mismatch
    parent_errs: list[str] = []
    for key, path in parent_files.items():
        if not path.is_file():
            parent_errs.append(f"missing:{key}")
            continue
        actual = sha_file(path)
        expected = pinned_parent.get(key)
        if expected is None:
            parent_errs.append(f"unpinned:{key}")
        elif actual != expected:
            parent_errs.append(f"mutated:{key}")
    checks.append({"check": "parent_immutability", "pass": not parent_errs, "errors": parent_errs})
    if parent_errs:
        defects.append("PARENT_INTEGRITY_FAIL")

    # Manifest hash pin completeness
    manifest_pin_errs: list[str] = []
    manifest: dict[str, Any] = {}
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        declared = manifest.get("artifact_hashes", {})
        if not isinstance(declared, dict):
            manifest_pin_errs.append("artifact_hashes_not_object")
        else:
            for key in REQUIRED_MANIFEST_HASH_KEYS:
                if key not in declared:
                    manifest_pin_errs.append(f"missing_manifest_pin:{key}")
    else:
        manifest_pin_errs.append("manifest_missing")
    checks.append({"check": "manifest_hash_pin_completeness", "pass": not manifest_pin_errs, "errors": manifest_pin_errs})
    if manifest_pin_errs:
        defects.append("MANIFEST_PIN_INCOMPLETE")

    # Parent integrity lock pin completeness
    parent_lock_errs: list[str] = []
    parent_lock: dict[str, Any] = {}
    if parent_lock_path.is_file():
        parent_lock = json.loads(parent_lock_path.read_text(encoding="utf-8"))
        pinned = parent_lock.get("pinned_hashes", {})
        if not isinstance(pinned, dict):
            parent_lock_errs.append("pinned_hashes_not_object")
        else:
            for key in REQUIRED_PARENT_INTEGRITY_KEYS:
                if key not in pinned:
                    parent_lock_errs.append(f"missing_parent_pin:{key}")
                elif pinned[key] != pinned_parent.get(key):
                    parent_lock_errs.append(f"parent_pin_mismatch:{key}")
    else:
        parent_lock_errs.append("parent_lock_missing")
    checks.append({"check": "parent_integrity_lock_pins", "pass": not parent_lock_errs, "errors": parent_lock_errs})
    if parent_lock_errs:
        defects.append("PARENT_PIN_INCOMPLETE")

    # Logical / gold set integrity
    set_errs: list[str] = []
    contract_errs: list[str] = []
    if logical_path.is_file() and gold_path.is_file():
        logical = load_jsonl(logical_path)
        gold_rows = load_jsonl(gold_path)
        logical_hash = sha_file(logical_path)
        gold_hash = sha_file(gold_path)

        if len(logical) != FIXTURE_N:
            set_errs.append(f"logical_n={len(logical)}")
        if len(gold_rows) != FIXTURE_N:
            set_errs.append(f"gold_n={len(gold_rows)}")

        logical_ids = [r.get("fixture_id") for r in logical]
        gold_ids = [g.get("fixture_id") for g in gold_rows]
        if len(set(logical_ids)) != len(logical_ids):
            set_errs.append("duplicate_logical_id")
        if len(set(gold_ids)) != len(gold_ids):
            set_errs.append("duplicate_gold_id")
        if set(logical_ids) != set(gold_ids):
            set_errs.append("logical_gold_id_mismatch")

        fam_counts = Counter(r.get("family") for r in logical)
        for fam in FAMILIES:
            if fam_counts.get(fam, 0) != 2:
                contract_errs.append(f"family:{fam}={fam_counts.get(fam, 0)}")

        gold_by_id = {g["fixture_id"]: g for g in gold_rows}
        for row in logical:
            fid = row["fixture_id"]
            if str(fid).startswith("BA"):
                contract_errs.append(f"prior_id:{fid}")
            g = gold_by_id.get(fid)
            if not g:
                contract_errs.append(f"no_gold:{fid}")
                continue
            for field_name in GOLD_REQUIRED:
                if field_name not in g:
                    contract_errs.append(f"missing:{fid}:{field_name}")
            if g.get("EXPECTED_PRIMARY_LAYER") not in LAYER_IDS:
                contract_errs.append(f"bad_primary:{fid}")

    checks.append({"check": "logical_gold_set_integrity", "pass": not set_errs, "errors": set_errs})
    if set_errs:
        defects.append("SET_INTEGRITY_FAIL")
    checks.append({"check": "fixture_contract", "pass": not contract_errs, "errors": contract_errs})
    if contract_errs:
        defects.append("CONTRACT_FAIL")

    # Hash coherence manifest ↔ disk + pinned logical/gold
    hash_errs: list[str] = []
    if logical_path.is_file():
        lh = sha_file(logical_path)
        logical_hash = lh
        if lh != PINNED_LOGICAL:
            hash_errs.append("logical_hash_pinned_mismatch")
        declared_logical = manifest.get("artifact_hashes", {}).get("logical_fixtures_jsonl")
        if declared_logical and declared_logical != lh:
            hash_errs.append("logical_hash_manifest_mismatch")
    if gold_path.is_file():
        gh = sha_file(gold_path)
        gold_hash = gh
        if gh != PINNED_GOLD:
            hash_errs.append("gold_hash_pinned_mismatch")
        declared_gold = manifest.get("artifact_hashes", {}).get("hidden_gold_jsonl")
        if declared_gold and declared_gold != gh:
            hash_errs.append("gold_hash_manifest_mismatch")

    if manifest_path.is_file():
        declared = manifest.get("artifact_hashes", {})
        file_map = {
            "logical_fixtures_jsonl": logical_path,
            "hidden_gold_jsonl": gold_path,
            "parent_integrity_lock": parent_lock_path,
            "freshness_classification": freshness_path,
            "evidence_ceiling": ceiling_path,
            "layer_routing_contract": contract_path,
            "clean_room_audit": clean_path,
            "contamination_audit": contam_path,
        }
        for key, path in file_map.items():
            if key in declared and path.is_file():
                if sha_file(path) != declared[key]:
                    hash_errs.append(f"manifest_disk_mismatch:{key}")

    checks.append({"check": "hash_coherence", "pass": not hash_errs, "errors": hash_errs})
    if hash_errs:
        defects.append("HASH_MISMATCH")

    # Seal coherence — logical, gold, item_count, freeze status, parent artifact pins
    seal_errs: list[str] = []
    if seal_path.is_file():
        seal = json.loads(seal_path.read_text(encoding="utf-8"))
        if seal.get("FREEZE_STATUS") != "FROZEN":
            seal_errs.append("freeze_status_not_frozen")
        if seal.get("DECIDE_ONE") != DECIDE_FROZEN:
            seal_errs.append("decide_not_frozen")
        if logical_path.is_file():
            lh = sha_file(logical_path)
            if seal.get("logical_hash") != lh:
                seal_errs.append("seal_logical_hash_mismatch")
        seal_hashes = seal.get("artifact_hashes", {})
        if not isinstance(seal_hashes, dict):
            seal_errs.append("seal_artifact_hashes_missing")
        else:
            if logical_path.is_file():
                key = "logical_fixtures_jsonl"
                if key not in seal_hashes:
                    seal_errs.append(f"seal_missing_pin:{key}")
                elif seal_hashes[key] != sha_file(logical_path):
                    seal_errs.append("seal_logical_pin_mismatch")
            if gold_path.is_file():
                key = "hidden_gold_jsonl"
                if key not in seal_hashes:
                    seal_errs.append(f"seal_missing_pin:{key}")
                elif seal_hashes[key] != sha_file(gold_path):
                    seal_errs.append("seal_gold_pin_mismatch")
        item_count = manifest.get("fixture_n")
        if item_count != FIXTURE_N:
            seal_errs.append(f"item_count_mismatch:{item_count}")
        if manifest.get("fixture_ids") and len(manifest.get("fixture_ids", [])) != FIXTURE_N:
            seal_errs.append("fixture_ids_count_mismatch")
    else:
        seal_errs.append("seal_missing")
    checks.append({"check": "seal_coherence", "pass": not seal_errs, "errors": seal_errs})
    if seal_errs:
        defects.append("SEAL_COHERENCE_FAIL")

    # Freshness classification
    freshness_errs: list[str] = []
    if freshness_path.is_file():
        freshness = json.loads(freshness_path.read_text(encoding="utf-8"))
        if freshness.get("FRESHNESS_CLASS") != FRESHNESS_REQUIRED:
            freshness_errs.append("freshness_class_mismatch")
        if freshness.get("PRIOR_FAILURE_TUNING") is not False:
            freshness_errs.append("prior_failure_tuning_not_false")
        if freshness.get("PRIOR_BA_FIXTURE_BYTES_REUSED") is not False:
            freshness_errs.append("prior_ba_bytes_reused_not_false")
    else:
        freshness_errs.append("freshness_missing")
    checks.append({"check": "freshness_classification", "pass": not freshness_errs, "errors": freshness_errs})
    if freshness_errs:
        defects.append("FRESHNESS_CLASSIFICATION_FAIL")

    # Evidence ceiling + send gate
    ceiling_errs: list[str] = []
    if ceiling_path.is_file():
        ceiling = json.loads(ceiling_path.read_text(encoding="utf-8"))
        if ceiling.get("MODEL_EXECUTION_N") != 0:
            ceiling_errs.append("model_execution_n_nonzero")
        if ceiling.get("SEMANTIC_FRESH_EXECUTION_N") != 0:
            ceiling_errs.append("semantic_fresh_execution_n_nonzero")
    else:
        ceiling_errs.append("ceiling_missing")
    if manifest.get("send_gate") != "HOLD":
        ceiling_errs.append("manifest_send_gate_not_hold")
    if contract_path.is_file():
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        if contract.get("send_gate") != "HOLD":
            ceiling_errs.append("contract_send_gate_not_hold")
    checks.append({"check": "evidence_ceiling", "pass": not ceiling_errs, "errors": ceiling_errs})
    if ceiling_errs:
        defects.append("EVIDENCE_CEILING_VIOLATION")

    if clean_path.is_file():
        clean = json.loads(clean_path.read_text(encoding="utf-8"))
        ok = clean.get("clean_room_verified") is True
        checks.append({"check": "clean_room", "pass": ok})
        if not ok:
            defects.append("CLEAN_ROOM_FAIL")
    if contam_path.is_file():
        contam = json.loads(contam_path.read_text(encoding="utf-8"))
        ok = contam.get("contamination_clean") is True
        checks.append({"check": "contamination", "pass": ok})
        if not ok:
            defects.append("CONTAMINATION_FAIL")

    return _finalize(defects, checks, logical_hash, gold_hash)


def _finalize(
    defects: list[str],
    checks: list[dict[str, Any]],
    logical_hash: str | None,
    gold_hash: str | None,
) -> ValidationResult:
    defects = list(dict.fromkeys(defects))
    decide = DECIDE_FROZEN if not defects else ("MULTIPLE_DEFECTS" if len(defects) > 1 else defects[0])
    iv_pass = decide == DECIDE_FROZEN
    return ValidationResult(
        iv_pass=iv_pass,
        decide=decide,
        defects=defects,
        checks=checks,
        logical_hash=logical_hash,
        gold_hash=gold_hash,
    )


def build_iv_document(result: ValidationResult, *, frozen_root: Path, iv_out: Path) -> dict[str, Any]:
    return {
        "schema": "mkm.logos.bible_adversarial.layer_routing_iv.v1",
        "artifact_id": "BIBLE_EP1_LAYER_ROUTING_INDEPENDENT_VALIDATOR_IV_V1",
        "validated_at_utc": utc_now(),
        "IV_PASS": result.iv_pass,
        "DECIDE_ONE": result.decide,
        "defects": result.defects,
        "checks": result.checks,
        "frozen_root": str(frozen_root.relative_to(ROOT)).replace("\\", "/"),
        "logical_hash": result.logical_hash,
        "gold_hash": result.gold_hash,
        "FREEZE_ONLY": True,
        "MODEL_EXECUTION_N": 0,
        "SEMANTIC_FRESH_EXECUTION_N": 0,
        "SEND_GATE": "HOLD",
        "iv_output_path": str(iv_out.relative_to(ROOT)).replace("\\", "/"),
        "repro": {"command": "py scripts/validate_mkm_logos_bible_ep1_layer_routing_fresh_fixture_freeze_iv_v1.py"},
    }


def main() -> int:
    result = run_validation(FROZEN_ROOT)
    iv = build_iv_document(result, frozen_root=FROZEN_ROOT, iv_out=IV_OUT)
    write_json(IV_OUT, iv)
    print(
        json.dumps(
            {
                "IV_PASS": result.iv_pass,
                "DECIDE_ONE": result.decide,
                "defects": result.defects,
                "iv_output": str(IV_OUT.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )
    return 0 if result.iv_pass else 1


if __name__ == "__main__":
    sys.exit(main())
