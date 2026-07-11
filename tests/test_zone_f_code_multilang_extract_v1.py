"""zone_f_code multilang extract v1 — native fence languages + TS probe corpus."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARD = ROOT / "codebook/shards/zone_f_code.json"
TS_PROBE_JSONL = ROOT / "data/compression/fixtures/zone_f_code_native_typescript_probe_v1.jsonl"
TS_BUILDER = ROOT / "scripts/build_zone_f_code_native_typescript_probe_v1.py"


def test_detect_fence_lang_typescript_and_solidity() -> None:
    from scripts.zone_f_code_multilang_extract_v1_lib import detect_fence_lang

    assert detect_fence_lang("```typescript\nexport const x = 1\n```") == "typescript"
    assert detect_fence_lang("```ts\nexport const x = 1\n```") == "typescript"
    assert detect_fence_lang("```solidity\npragma solidity ^0.8;\n```") == "solidity"


def test_looks_like_native_snippets() -> None:
    from scripts.zone_f_code_multilang_extract_v1_lib import looks_like_code_snippet

    solidity = "pragma solidity ^0.8.20;\ncontract X {\n  function schemaJson(string endpoint) external pure returns (bool) { return true; }\n}"
    haskell = "module Health.Api.Schema where\nschemaHandler :: String -> Bool\nschemaHandler endpoint = not (null endpoint)"
    ts = "export async function handler(endpoint: string) {\n  return { api: 'x', endpoint, schema: 'v1', json: {} };\n}"
    assert looks_like_code_snippet(solidity, lang="solidity")
    assert looks_like_code_snippet(haskell, lang="haskell")
    assert looks_like_code_snippet(ts, lang="typescript")


def test_infer_snippet_language_wave5_languages() -> None:
    from scripts.zone_f_code_multilang_extract_v1_lib import infer_snippet_language

    blob_ts = "```typescript\nexport function x() {}\n```"
    assert infer_snippet_language("export function x() {}", blob_ts) == "typescript"
    assert infer_snippet_language("pragma solidity ^0.8;", "") == "solidity"
    assert infer_snippet_language("module Health where\nx :: Int", "") == "haskell"
    assert infer_snippet_language("(ns acme.api)\n(defn handler [e] e)", "") == "clojure"


def test_extract_candidates_typescript_fenced() -> None:
    from scripts.extract_zone_f_code_template_seeds_v1_lib import (
        extract_candidates_from_text,
        load_zone_f_code_shard,
        shard_keywords,
    )

    shard = load_zone_f_code_shard(SHARD)
    kws = shard_keywords(shard)
    text = (
        "Customer pasted SDK example:\n"
        "```typescript\n"
        "export async function validateBillingSchema(endpoint: string, payload: Record<string, unknown>) {\n"
        "  return { api: 'billing', endpoint, schema: 'v2', json: payload };\n"
        "}\n"
        "```"
    )
    cands = extract_candidates_from_text(text, keywords=kws)
    assert len(cands) == 1
    assert "endpoint" in cands[0]
    assert "schema" in cands[0]


def test_native_typescript_probe_builder_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, str(TS_BUILDER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert TS_PROBE_JSONL.is_file()
    lines = [ln for ln in TS_PROBE_JSONL.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 10
    report = json.loads(
        (ROOT / "reports/zone_f_code_native_typescript_probe_v1_latest.json").read_text(encoding="utf-8")
    )
    assert report["extract_success_count"] == 10
    assert report["extract_success_rate"] == 1.0
    assert report["inferred_languages"] == ["typescript"]
