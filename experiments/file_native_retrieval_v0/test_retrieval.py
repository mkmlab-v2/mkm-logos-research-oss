import json
import pytest
from retrieval import build, search


def test_exact_relation_and_hash(tmp_path):
    (tmp_path / 'a.py').write_text('def alpha():\n    return "b.md"\n')
    (tmp_path / 'b.md').write_text('separate evidence')
    records = build(tmp_path, ['a.py', 'b.md'])
    hits = search(tmp_path, records, 'alpha')
    assert hits[0]['source_path'] == 'a.py'
    assert hits[0]['source_verified']
    assert hits[1]['match_reason'] == 'one_hop_literal_path_reference'
    assert search(tmp_path, records, records[0]['source_hash'])[0]['source_path'] == 'a.py'
    assert search(tmp_path, records, 'no_such_term') == []


def test_update_delete_stale_and_determinism(tmp_path):
    (tmp_path / 'a.md').write_text('alpha')
    old = build(tmp_path, ['a.md'])
    assert build(tmp_path, ['a.md'], old) == old
    (tmp_path / 'a.md').write_text('beta')
    assert not search(tmp_path, old, 'alpha')[0]['source_verified']
    updated = build(tmp_path, ['a.md'], old)
    assert search(tmp_path, updated, 'alpha') == []
    assert search(tmp_path, updated, 'beta')[0]['source_verified']
    assert json.dumps(updated, sort_keys=True) == json.dumps(build(tmp_path, ['a.md']), sort_keys=True)
    assert build(tmp_path, [], updated) == []
    (tmp_path / 'a.md').unlink()
    assert not search(tmp_path, updated, 'beta')[0]['source_verified']


def test_escape_rejected(tmp_path):
    with pytest.raises(ValueError):
        build(tmp_path, ['../outside.md'])


def test_korean_and_duplicate_paths(tmp_path):
    (tmp_path / 'a.md').write_text('상태 복원', encoding='utf-8')
    records = build(tmp_path, ['a.md', 'a.md'])
    assert len(records) == 1
    assert search(tmp_path, records, '복원')[0]['source_verified']


def test_incremental_relation_membership(tmp_path):
    (tmp_path / 'a.md').write_text('alpha b.md')
    (tmp_path / 'b.md').write_text('beta')
    old = build(tmp_path, ['a.md'])
    updated = build(tmp_path, ['a.md', 'b.md'], old)
    assert updated[0]['relations'] == [{'target': 'b.md', 'kind': 'literal_path_reference'}]
    assert build(tmp_path, ['a.md'], updated)[0]['relations'] == []


def test_comparator_contract():
    from dev_comparator import compare
    result = compare()
    assert result['external_api_calls'] == 0
    assert result['qdrant'] == 'NOT_ESTABLISHED'
    assert len(result['queries']) == 5
    assert result['deterministic_records']
