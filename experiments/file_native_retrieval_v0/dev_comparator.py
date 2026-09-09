"""Synthetic DEV comparator: no expected answers passed to retrieval."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from retrieval import build, search

CASES = [('alpha', ['a.py']), ('beta', ['b.py']), ('복원', ['notes.md']),
         ('a.py', ['a.py']), ('no_such_term', [])]


def compare():
    with TemporaryDirectory() as directory:
        root = Path(directory)
        texts = {'a.py': 'def alpha():\n    return 1\n',
                 'b.py': 'def beta():\n    return 2\n', 'notes.md': '상태 복원'}
        for path, text in texts.items():
            (root / path).write_text(text, encoding='utf-8')
        started = perf_counter()
        records = build(root, list(texts))
        build_ms = (perf_counter() - started) * 1000
        started = perf_counter()
        unchanged = build(root, list(texts), records)
        update_ms = (perf_counter() - started) * 1000
        results = []
        for query, gold in CASES:
            started = perf_counter()
            baseline = sorted(path for path, text in texts.items()
                              if query.lower() in (path + '\n' + text).lower())
            baseline_ms = (perf_counter() - started) * 1000
            started = perf_counter()
            hits = search(root, records, query)
            latency = (perf_counter() - started) * 1000
            ranked = [row['source_path'] for row in hits]
            results.append(dict(query=query, gold=gold, baseline=baseline, prototype=ranked,
                                baseline_ms=baseline_ms, prototype_ms=latency))
        metrics = {}
        for system in ('baseline', 'prototype'):
            positive = [row for row in results if row['gold']]
            metrics[system] = {f'recall_at_{limit}': sum(
                len(set(row[system][:limit]) & set(row['gold'])) / len(row['gold'])
                for row in positive) / len(positive) for limit in (1, 5, 10)}
            metrics[system]['negative_query_empty'] = all(not row[system] for row in results if not row['gold'])
        return dict(ceiling='SYNTHETIC_DEV_ONLY', queries=results, metrics=metrics,
                    build_ms=build_ms, unchanged_update_ms=update_ms,
                    deterministic_records=records == unchanged,
                    index_serialized_bytes=len(json.dumps(records).encode()),
                    external_api_calls=0, qdrant='NOT_ESTABLISHED',
                    context_tokens='NOT_MEASURED', authoritative_hit_rate='NOT_ESTABLISHED')


if __name__ == '__main__':
    print(json.dumps(compare(), ensure_ascii=False, indent=2))
