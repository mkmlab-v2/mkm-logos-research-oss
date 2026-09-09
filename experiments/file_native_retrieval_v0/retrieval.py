"""Bounded, local locator prototype. Index only explicitly selected files."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.mkm_ops_memory_index_lib_v1 import query_match_tokens

WARNING = "locator only; verify actual source"


def resolve(root, relative):
    path = (root / relative).resolve()
    path.relative_to(root.resolve())
    return path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(root, paths, previous=()):
    old = {row['source_path']: row for row in previous}
    records = []
    for relative in sorted(set(paths)):
        path = resolve(root, relative)
        if path.suffix not in {'.py', '.md', '.json'}:
            raise ValueError('Only explicit py/md/json source files supported')
        source_hash = digest(path)
        if (set(old) == set(paths) and relative in old
                and old[relative]['source_hash'] == source_hash):
            records.append(old[relative])
            continue
        text = path.read_text(encoding='utf-8-sig')
        symbols = []
        if path.suffix == '.py':
            symbols = [dict(symbol=node.name, line_start=node.lineno, line_end=node.end_lineno)
                       for node in ast.walk(ast.parse(text))
                       if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        relations = [dict(target=target, kind='literal_path_reference')
                     for target in sorted(set(paths)) if target != relative and target in text]
        records.append(dict(id=relative, source_path=relative, source_hash=source_hash,
                            symbols=symbols, keywords=sorted(query_match_tokens(text)),
                            relations=relations, kind=path.suffix, state='LOCATOR_ONLY'))
    return records


def search(root, records, query, limit=10):
    if limit < 1:
        raise ValueError('limit must be positive')
    tokens = set(query_match_tokens(query))
    postings = {}
    for row in records:
        for token in row['keywords']:
            postings.setdefault(token, set()).add(row['id'])
    scores, reasons = {}, {}
    for row in records:
        exact = query in {row['source_path'], Path(row['source_path']).name, row['source_hash']} or any(
            item['symbol'] == query for item in row['symbols'])
        overlap = sum(row['id'] in postings.get(token, ()) for token in tokens)
        if exact or overlap:
            scores[row['id']] = (100 if exact else 0) + overlap
            reasons[row['id']] = 'exact' if exact else 'sparse_token_overlap'
    by_id = {row['id']: row for row in records}
    for source in sorted(scores):
        for edge in by_id[source]['relations']:
            target = edge['target']
            if target in by_id and target not in scores:
                scores[target] = 0.5
                reasons[target] = 'one_hop_literal_path_reference'
    hits = []
    for identity in sorted(scores, key=lambda identity: (-scores[identity], identity)):
        row = by_id[identity]
        try:
            verified = digest(resolve(root, row['source_path'])) == row['source_hash']
        except (OSError, ValueError):
            verified = False
        hits.append(dict(**row, score=scores[identity], match_reason=reasons[identity],
                         source_verified=verified, warning=WARNING))
    return hits[:limit]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--paths', type=Path, required=True, help='JSON array of approved relative paths')
    parser.add_argument('--query', required=True)
    args = parser.parse_args()
    records = build(args.root, json.loads(args.paths.read_text(encoding='utf-8')))
    print(json.dumps(search(args.root, records, args.query), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
