#!/usr/bin/env python3
"""Build logos_vector_index_manifest_v1 — audit record before real embeddings/ANN.

Reads LOGOS_VECTOR_INDEX_POLICY_V1 + corpus manifest + graph bundle; records SHA-256
and dedupe keys. Does not compute embeddings or write vector storage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_POLICY = ROOT / "docs/final/artifacts/LOGOS_VECTOR_INDEX_POLICY_V1.json"
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/logos_corpus_manifest_v1_latest.json"
DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_vector_index_manifest_v1_latest.json"

ARTIFACT_SCHEMA = "logos_vector_index_manifest_v1"
VERSION = "1.0.0"


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve())


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--corpus-manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--bundle-json", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print summary; still writes output file.",
    )
    args = ap.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if not args.policy.is_file():
        print(f"Missing policy: {args.policy}", file=sys.stderr)
        return 2

    policy_doc = json.loads(args.policy.read_text(encoding="utf-8"))
    if policy_doc.get("schema") != "logos_vector_index_policy_v1":
        print("Policy schema field must be logos_vector_index_policy_v1.", file=sys.stderr)
        return 2

    cal = policy_doc.get("corpus_alignment") or {}
    req = cal.get("required_preconditions")
    if isinstance(req, list) and req:
        rel_manifest = _rel(args.corpus_manifest)
        rel_bundle = _rel(args.bundle_json)
        if rel_manifest not in req or rel_bundle not in req:
            print(
                "warning: --corpus-manifest / --bundle-json paths differ from "
                "policy.corpus_alignment.required_preconditions (continuing)",
                file=sys.stderr,
            )

    if not args.corpus_manifest.is_file():
        print(f"Missing corpus manifest: {args.corpus_manifest}", file=sys.stderr)
        return 2
    if not args.bundle_json.is_file():
        print(f"Missing bundle: {args.bundle_json}", file=sys.stderr)
        return 2

    man_doc = json.loads(args.corpus_manifest.read_text(encoding="utf-8"))
    if man_doc.get("schema") != "logos_corpus_manifest_v1":
        print("Corpus manifest schema must be logos_corpus_manifest_v1.", file=sys.stderr)
        return 2

    bundle_doc = json.loads(args.bundle_json.read_text(encoding="utf-8"))
    if bundle_doc.get("schema") != "logos_corpus_graph_bundle_v1":
        print("Bundle schema must be logos_corpus_graph_bundle_v1.", file=sys.stderr)
        return 2

    dedupe = bundle_doc.get("dedupe_bundle_key_sha256")
    if not isinstance(dedupe, str) or len(dedupe) != 64:
        print("Bundle missing valid dedupe_bundle_key_sha256.", file=sys.stderr)
        return 2

    emb = policy_doc.get("embedding") or {}
    model_id = emb.get("model_id") if isinstance(emb.get("model_id"), str) else None

    verse_count = man_doc.get("verse_count")
    if not isinstance(verse_count, int):
        verse_count = None

    policy_sha = _sha256_file(args.policy)

    doc: dict[str, Any] = {
        "schema": ARTIFACT_SCHEMA,
        "version": VERSION,
        "ts_utc": ts,
        "hypothesis_tier": "B",
        "non_gating_ack": True,
        "policy_snapshot": {
            "artifact_path": _rel(args.policy),
            "sha256_hex": policy_sha,
            "status": policy_doc.get("status"),
            "embedding_model_id": model_id,
            "policy_version": policy_doc.get("version"),
        },
        "corpus_alignment": {
            "corpus_manifest_path": _rel(args.corpus_manifest),
            "corpus_manifest_sha256_hex": _sha256_file(args.corpus_manifest),
            "verse_count": verse_count,
            "bundle_path": _rel(args.bundle_json),
            "bundle_dedupe_key_sha256": dedupe,
            "manifest_input_sha256": man_doc.get("input_sha256"),
        },
        "index_build": {
            "embeddings_computed": False,
            "vectors_written": 0,
            "backend": "manifest_only_stub",
            "notes": "Real ANN/index build only after policy.status=active and explicit builder.",
        },
        "notes": "No embedding API calls; Track B observation manifest.",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.dry_run:
        print(
            f"OK policy_sha={policy_sha[:16]}… bundle_dedupe={dedupe[:16]}… "
            f"write={_rel(args.output)}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
