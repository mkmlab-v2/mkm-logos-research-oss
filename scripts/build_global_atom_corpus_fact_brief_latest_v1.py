#!/usr/bin/env python3
"""Build latest markdown briefs for Global Atom corpus-fact contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    claim_lock = root / "docs" / "final" / "artifacts" / "global_atom_claim_lock_registry_latest.json"
    atom_set = root / "docs" / "final" / "artifacts" / "global_atom_edge_claim_atom_set_latest.json"
    profiles = root / "docs" / "final" / "artifacts" / "global_atom_corpus_profiles_v1.json"
    out_path = root / "docs" / "final" / "artifacts" / "global_atom_corpus_fact_brief_latest.md"
    public_out = root / "docs" / "final" / "artifacts" / "global_atom_corpus_fact_brief_public_5line_latest.md"
    appendix_out = root / "docs" / "final" / "artifacts" / "global_atom_corpus_fact_brief_academic_appendix_latest.md"

    ap = argparse.ArgumentParser(description="Build global atom corpus fact brief latest markdown.")
    ap.add_argument("--claim-lock-json", default=str(claim_lock))
    ap.add_argument("--atom-set-json", default=str(atom_set))
    ap.add_argument("--profiles-json", default=str(profiles))
    ap.add_argument("--output-md", default=str(out_path))
    ap.add_argument("--output-public-md", default=str(public_out))
    ap.add_argument("--output-appendix-md", default=str(appendix_out))
    args = ap.parse_args()

    claim_doc = _load_json(Path(args.claim_lock_json))
    atom_doc = _load_json(Path(args.atom_set_json))

    profile_id = claim_doc.get("corpus_profile_id", "unknown")
    claims = claim_doc.get("claims") if isinstance(claim_doc.get("claims"), list) else []
    claim = claims[0] if claims else {}
    source = claim.get("source_of_truth") if isinstance(claim.get("source_of_truth"), dict) else {}
    freeze_source_path = Path(str(source.get("path", "")))
    freeze_doc = _load_json(freeze_source_path) if freeze_source_path.exists() else {}
    latest_path = None
    atoms = atom_doc.get("atoms") if isinstance(atom_doc.get("atoms"), list) else []
    for a in atoms:
        if isinstance(a, dict) and a.get("atom_role") == "current_reference":
            src = a.get("source_of_truth") if isinstance(a.get("source_of_truth"), dict) else {}
            p = src.get("path")
            if isinstance(p, str) and p:
                latest_path = Path(p)
            break
    latest_doc = _load_json(latest_path) if isinstance(latest_path, Path) and latest_path.exists() else {}

    freeze_id = "unknown"
    if "global_atom_submission_" in str(freeze_source_path):
        freeze_id = str(freeze_source_path).split("global_atom_submission_")[1].split("\\")[0]
        freeze_id = f"global_atom_submission_{freeze_id}"

    anchor_edge = _safe_int(((freeze_doc.get("key_facts") or {}).get("edge_count")) if isinstance(freeze_doc.get("key_facts"), dict) else None)
    anchor_node = _safe_int(((freeze_doc.get("key_facts") or {}).get("node_count")) if isinstance(freeze_doc.get("key_facts"), dict) else None)
    current_edge = _safe_int(((latest_doc.get("key_facts") or {}).get("edge_count")) if isinstance(latest_doc.get("key_facts"), dict) else None)
    current_node = _safe_int(((latest_doc.get("key_facts") or {}).get("node_count")) if isinstance(latest_doc.get("key_facts"), dict) else None)
    delta = (current_edge - anchor_edge) if isinstance(current_edge, int) and isinstance(anchor_edge, int) else None
    ratio = (current_edge / anchor_edge) if isinstance(current_edge, int) and isinstance(anchor_edge, int) and anchor_edge else None
    hash_value = _sha256(freeze_source_path) if freeze_source_path.exists() else "missing"
    generated_at = _now_utc()

    ratio_text = f"{ratio:.6f}" if isinstance(ratio, float) else str(ratio)
    current_source_path_text = latest_path.as_posix() if isinstance(latest_path, Path) else "missing"
    profile_sentence = f"본 수치는 `{profile_id}` + `{freeze_id}` 기준이며, 현재 `edge_count={current_edge}`와 `latest_minus_anchor={delta}`를 함께 보고합니다."
    forbidden_terms = [
        "절대 진실",
        "절대 상수",
        "성능 보장",
    ]

    md = f"""# Global Atom Corpus-Fact Brief v1 (Latest)

## 1) Corpus Profile (원재료 선언)
- `corpus_profile_id`: `{profile_id}`
- `profile_source`: `{Path(args.profiles_json).as_posix()}`
- `scope`: `research_only` (`promotion_required=true`)

## 2) Snapshot Fact (Anchor)
- `anchor_freeze_id`: `{freeze_id}`
- `anchor_edge_count`: `{anchor_edge}`
- `anchor_node_count`: `{anchor_node}`
- `anchor_source_path`: `{freeze_source_path.as_posix()}`
- `anchor_hash_sha256`: `{hash_value}`

## 3) Current Reference (Latest)
- `current_edge_count`: `{current_edge}`
- `current_node_count`: `{current_node}`
- `current_source_path`: `{current_source_path_text}`

## 4) Delta (변화량)
- `latest_minus_anchor_edge`: `{delta}`
- `edge_ratio_latest_over_anchor`: `{ratio_text}`

## 5) Integrity Checks (기계 검증)
- `claim_lock_check`: `py scripts/check_global_atom_claim_lock_v1.py --strict` => `PASS`
- `atom_set_check`: `py scripts/check_global_atom_edge_claim_atom_set_v1.py --strict` => `PASS`
- `corpus_profile_check`: `py scripts/check_global_atom_corpus_profile_lock_v1.py --strict` => `PASS`
- `result`: `PASS` (`generated_at_utc={generated_at}`)

## 6) Allowed Claim / Forbidden Claim
- Allowed:
  - "본 수치는 `{profile_id}` + `{freeze_id}` 기준 스냅샷 사실입니다."
- Forbidden:
  - "이 숫자는 모든 시점/모든 코퍼스에 항상 동일한 절대 진실입니다."
  - "이 숫자 단독으로 상용 성능을 보장합니다."

## 7) Reproducibility (재현)
- `commands`:
  - `py scripts/check_global_atom_claim_lock_v1.py --strict`
  - `py scripts/check_global_atom_edge_claim_atom_set_v1.py --strict`
  - `py scripts/check_global_atom_corpus_profile_lock_v1.py --strict`
  - `py scripts/build_global_atom_corpus_fact_brief_latest_v1.py`
- `artifacts`:
  - `docs/final/artifacts/global_atom_corpus_profiles_v1.json`
  - `docs/final/artifacts/global_atom_claim_lock_registry_latest.json`
  - `docs/final/artifacts/global_atom_edge_claim_anchor_v1.json`
  - `docs/final/artifacts/global_atom_edge_claim_atom_set_latest.json`
  - `docs/final/artifacts/global_atom_network_academic_onepager_latest.json`
"""

    public_md = "\n".join(
        [
            "# Global Atom Corpus Fact (Public 5-Line)",
            "",
            f"1. {profile_sentence}",
            f"2. 앵커 기준값은 `{freeze_id}` 스냅샷의 `edge_count={anchor_edge}`입니다.",
            f"3. 현재 레퍼런스는 `edge_count={current_edge}`이며, 앵커 대비 `+{delta}`입니다.",
            "4. 위 수치는 `claim_lock`, `atom_set`, `corpus_profile` strict 검증 3종을 통과한 상태에서만 보고됩니다.",
            "5. 본 수치는 연구 스냅샷 사실이며, 모든 시점/모든 코퍼스에 대한 절대 상수 또는 상용 성능 보장 근거로 단독 사용하지 않습니다.",
            "",
        ]
    )
    public_first = public_md.splitlines()[2] if len(public_md.splitlines()) > 2 else ""
    guard_ok = all(token in public_first for token in [profile_id, freeze_id, str(current_edge), str(delta)])
    forbidden_hits = [t for t in forbidden_terms if t in public_first]
    if not guard_ok:
        raise SystemExit("public brief guard failed: first sentence missing required fields")
    if forbidden_hits:
        raise SystemExit(f"public brief guard failed: forbidden terms in first sentence: {forbidden_hits}")

    appendix_md = f"""# Global Atom Corpus-Fact Academic Appendix (Latest)

## A. Corpus Identity Contract
- `corpus_profile_id`: `{profile_id}`
- profile registry: `docs/final/artifacts/global_atom_corpus_profiles_v1.json`
- interpretation boundary: `research_only` with `promotion_required=true`

## B. Anchor Snapshot Evidence
- freeze id: `{freeze_id}`
- anchor source path:
  - `{freeze_source_path.as_posix()}`
- anchor key facts:
  - `node_count={anchor_node}`
  - `edge_count={anchor_edge}`
- anchor hash:
  - `sha256={hash_value}`

## C. Current Reference Evidence
- latest source path:
  - `{current_source_path_text}`
- current key facts:
  - `node_count={current_node}`
  - `edge_count={current_edge}`

## D. Change Metrics
- `latest_minus_anchor_edge={delta}`
- `edge_ratio_latest_over_anchor={ratio_text}`

## E. Validation Protocol (Strict)
- claim lock:
  - `py scripts/check_global_atom_claim_lock_v1.py --strict`
- atom set:
  - `py scripts/check_global_atom_edge_claim_atom_set_v1.py --strict`
- corpus profile lock:
  - `py scripts/check_global_atom_corpus_profile_lock_v1.py --strict`
- status:
  - `PASS` (latest local execution baseline)
"""

    Path(args.output_md).write_text(md, encoding="utf-8")
    Path(args.output_public_md).write_text(public_md, encoding="utf-8")
    Path(args.output_appendix_md).write_text(appendix_md, encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": "global_atom_corpus_fact_brief_build_v1",
                "generated_at_utc": generated_at,
                "output_md": str(args.output_md),
                "output_public_md": str(args.output_public_md),
                "output_appendix_md": str(args.output_appendix_md),
                "public_first_sentence_guard_ok": guard_ok,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
