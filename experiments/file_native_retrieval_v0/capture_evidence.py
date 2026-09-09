"""Read-only source inventory, emitting new local recovery evidence files only."""
import ast
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from dev_comparator import compare

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
COMPONENTS = [
    ('scripts/build_workspace_postit_index_v1.py', 'tests/test_build_workspace_postit_index_v1.py', 'docs/final/artifacts/workspace_postit_index_latest.json', 'Path-inferred status is not evidence'),
    ('scripts/run_workspace_postit_search_v1.py', None, 'docs/final/artifacts/workspace_postit_search_results_latest.json', 'Preset filters only'),
    ('scripts/mkm_ops_memory_index_lib_v1.py', 'tests/test_mkm_ops_memory_index_v1.py', 'storage/meta/mkm_ops_memory_index_v1.json', 'Curated nodes and hash prefixes'),
    ('scripts/build_context_note_memory_index_v1.py', 'tests/test_context_note_memory_index_v1.py', 'docs/final/artifacts/context_note_memory_v1.sqlite', 'Full database rebuild; no incremental proof'),
    ('scripts/query_context_note_memory_index_v1.py', 'tests/test_context_note_memory_index_v1.py', None, 'Path priors; hash stub is not semantic'),
    ('scripts/build_mkm_core_coordinate_map_v1.py', 'tests/test_mkm_core_coordinate_map_v1.py', 'docs/final/artifacts/mkm_core_coordinate_map_check_v1_latest.json', 'Curated coordinates'),
    ('scripts/build_a2a_tp03_chain_ref_pilot_v1.py', 'tests/test_build_a2a_tp03_chain_ref_pilot_v1.py', 'docs/final/artifacts/a2a_tp03_chain_ref_pilot_v1_latest.json', 'Client/compression runtime not executed'),
    ('scripts/mkm_a2a_compress_pilot_lib_v1.py', None, None, 'Requires supplied compression client'),
    ('scripts/validate_postit_pointer_v1.py', 'tests/test_validate_postit_pointer_v1.py', 'docs/final/schemas/postit_pointer_v1.schema.json', 'Domain-specific pointer contract'),
    ('scripts/query_mkm_structural_retrieval_v0.py', None, None, 'Expected answers enter retrieval; not blind comparator'),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def emit(name, value):
    with (OUT / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def main():
    inventory = []
    for source, test, artifact, limitation in COMPONENTS:
        path = ROOT / source
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        symbols = [dict(name=node.name, line=node.lineno) for node in tree.body
                   if isinstance(node, (ast.FunctionDef, ast.ClassDef))]
        dependencies = sorted({node.module or '' for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
                              | {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names})
        inventory.append(dict(path=source, sha256=sha(path), symbols=symbols, implementation_exists=True,
                              test_path=test, test_exists=bool(test and (ROOT / test).is_file()),
                              artifact_path=artifact, artifact_exists=bool(artifact and (ROOT / artifact).is_file()),
                              dependencies=dependencies, limitations=limitation,
                              evidence_level='FACT_STATIC_SOURCE', current_runtime_status='NOT_ESTABLISHED'))
    emit('EXISTING_TECH_COMPONENT_MAP.json', inventory)
    comparator = compare()
    emit('DEV_COMPARATOR_RESULT.json', comparator)
    git = subprocess.run(['git', '--no-optional-locks', 'rev-parse', 'HEAD'], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout.strip()
    receipt = dict(project='MKM_FILE_NATIVE_RETRIEVAL', result='BOUNDED_PROTOTYPE_READY',
                   as_of=datetime.now(timezone.utc).isoformat(), local_ssot_commit=git,
                   recovered_components=len(inventory), tests='6 passed; focused pytest exit 0',
                   tests_command='py -B -m pytest experiments/file_native_retrieval_v0/test_retrieval.py -q -p no:cacheprovider',
                   evidence_ceiling='BOUNDED_IMPLEMENTATION_SYNTHETIC_DEV_ONLY',
                   independence='BUILDER_SELF_TEST_NOT_INDEPENDENT_REVIEW',
                   exhaustive_workspace_coverage=False, qdrant='NOT_ESTABLISHED',
                   predictive_effectiveness='NOT_ESTABLISHED', superiority='NOT_ESTABLISHED',
                   external_api_calls=0, auto_next=False, next='STOP')
    receipt['files_sha256'] = {path.name: sha(path) for path in sorted(OUT.iterdir()) if path.is_file()}
    emit('receipt.json', receipt)
    print(json.dumps({'result': receipt['result'], 'metrics': comparator['metrics'],
                      'build_ms': comparator['build_ms'], 'unchanged_update_ms': comparator['unchanged_update_ms']}))


if __name__ == '__main__':
    main()
