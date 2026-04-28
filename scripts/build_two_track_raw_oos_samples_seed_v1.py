#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, random
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def now(): return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def load(p):
    o=json.loads(p.read_text(encoding='utf-8'))
    return o if isinstance(o,dict) else {}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--benchmark-json', required=True); ap.add_argument('--output-jsonl', required=True); ap.add_argument('--samples-per-baseline', type=int, default=10); ap.add_argument('--seed', type=int, default=42); a=ap.parse_args()
    bp,op=Path(a.benchmark_json),Path(a.output_jsonl)
    if not bp.is_absolute(): bp=ROOT/bp
    if not op.is_absolute(): op=ROOT/op
    b=load(bp); rows=list(b.get('baseline_results') or [])
    rng=random.Random(int(a.seed)); out=[]
    for row in rows:
        base=((row.get('baseline') or {}).get('name','unknown'))
        delta=float((row.get('delta') or {}).get('shift_score',0.0))
        for i in range(max(1,int(a.samples_per_baseline))):
            out.append({'schema':'two_track_raw_oos_sample_v1','generated_at_utc':now(),'baseline_name':base,'delta_shift_score':float(delta + rng.uniform(-0.08,0.08)),'sample_index':i,'is_seed_scaffold':True,'is_bootstrap_resample':False,'source':'benchmark_seed'})
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in out)+'\n', encoding='utf-8'); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
