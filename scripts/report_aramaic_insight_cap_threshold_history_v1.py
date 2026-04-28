#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def now(): return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def load(path):
    try:o=json.loads(path.read_text(encoding='utf-8'))
    except Exception:return {}
    return o if isinstance(o,dict) else {}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--recommended-json', required=True); ap.add_argument('--history-jsonl', default='reports/ops/aramaic_insight_cap_bucket_threshold_history.jsonl'); a=ap.parse_args()
    rp=Path(a.recommended_json); hp=Path(a.history_jsonl)
    if not rp.is_absolute(): rp=ROOT/rp
    if not hp.is_absolute(): hp=ROOT/hp
    d=load(rp); row={'schema':'aramaic_insight_cap_bucket_threshold_history_row_v1','recorded_at_utc':now(),'recommended':d.get('recommended',{})}
    hp.parent.mkdir(parents=True, exist_ok=True)
    with hp.open('a', encoding='utf-8') as f: f.write(json.dumps(row,ensure_ascii=False)+'\n')
    print(str(hp)); return 0
if __name__=='__main__': raise SystemExit(main())
