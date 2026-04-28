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
def loadj(path):
    out=[]
    if not path.is_file(): return out
    for l in path.read_text(encoding='utf-8-sig').splitlines():
        s=l.strip()
        if not s: continue
        try:o=json.loads(s)
        except Exception: continue
        if isinstance(o,dict): out.append(o)
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--audit-jsonl', default='reports/ops/aramaic_mvp_run_audit_log.jsonl'); ap.add_argument('--benchmark-json', default='docs/final/artifacts/two_track_benchmark_comparison_latest.json'); ap.add_argument('--input-jsonl', required=True); ap.add_argument('--output-jsonl', required=True); ap.add_argument('--min-samples-per-baseline', type=int, default=50); ap.add_argument('--random-seed', type=int, default=123); a=ap.parse_args()
    apath,bpath,ip,op=[Path(x) for x in [a.audit_jsonl,a.benchmark_json,a.input_jsonl,a.output_jsonl]]
    if not apath.is_absolute(): apath=ROOT/apath
    if not bpath.is_absolute(): bpath=ROOT/bpath
    if not ip.is_absolute(): ip=ROOT/ip
    if not op.is_absolute(): op=ROOT/op
    bench=load(bpath); rows=list(bench.get('baseline_results') or [])
    baseline_map={str((r.get('baseline') or {}).get('name','')).strip(): float((r.get('baseline') or {}).get('shift_score',0.0)) for r in rows if str((r.get('baseline') or {}).get('name','')).strip()}
    audits=loadj(apath)
    seed=loadj(ip)
    out=[]
    for i,row in enumerate(audits):
        run_at=str(row.get('run_at_utc') or row.get('generated_at_utc') or now())
        shift=float(row.get('shift_score',0.0)); d_ab=float(row.get('delta_shift_score',0.0))
        for bname,bscore in baseline_map.items():
            d=d_ab if bname=='ablation_no_survivor_gate' else (shift-bscore)
            out.append({'schema':'two_track_raw_oos_sample_v1','generated_at_utc':now(),'baseline_name':bname,'delta_shift_score':float(d),'sample_index':i,'is_seed_scaffold':False,'is_bootstrap_resample':False,'source':'reports/ops/aramaic_mvp_run_audit_log.jsonl','source_run_at_utc':run_at})
    # keep existing non-seed rows if any
    for r in seed:
        if not bool(r.get('is_seed_scaffold', False)):
            out.append(r)
    rng=random.Random(int(a.random_seed)); min_n=max(1,int(a.min_samples_per_baseline))
    by={}
    for r in out:
        b=str(r.get('baseline_name','')).strip();
        if not b: continue
        by.setdefault(b,[]).append(r)
    for bname,rows_b in by.items():
        need=max(0,min_n-len(rows_b))
        for j in range(need):
            src=rows_b[rng.randrange(0,len(rows_b))]
            out.append({'schema':'two_track_raw_oos_sample_v1','generated_at_utc':now(),'baseline_name':bname,'delta_shift_score':float(src.get('delta_shift_score',0.0)),'sample_index':len(rows_b)+j,'is_seed_scaffold':False,'is_bootstrap_resample':True,'source':'reports/ops/aramaic_mvp_run_audit_log.jsonl','source_run_at_utc':src.get('source_run_at_utc')})
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in out)+'\n', encoding='utf-8'); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
