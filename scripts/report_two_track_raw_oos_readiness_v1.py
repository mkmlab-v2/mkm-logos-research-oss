#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def now(): return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
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
def load(path):
    if not path.is_file(): return {}
    try:o=json.loads(path.read_text(encoding='utf-8'))
    except Exception:return {}
    return o if isinstance(o,dict) else {}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--raw-oos-jsonl', required=True); ap.add_argument('--benchmark-json', required=True); ap.add_argument('--output-json', required=True); ap.add_argument('--min-samples-per-baseline', type=int, default=50); ap.add_argument('--audit-log-jsonl', default='reports/ops/aramaic_mvp_run_audit_log.jsonl'); ap.add_argument('--expected-cadence-minutes', type=int, default=60); a=ap.parse_args()
    rp,bp,op,apath=[Path(x) for x in [a.raw_oos_jsonl,a.benchmark_json,a.output_json,a.audit_log_jsonl]]
    if not rp.is_absolute(): rp=ROOT/rp
    if not bp.is_absolute(): bp=ROOT/bp
    if not op.is_absolute(): op=ROOT/op
    if not apath.is_absolute(): apath=ROOT/apath
    rows=loadj(rp); bench=load(bp)
    by={}; seed=0; boot=0; scenario_adjusted=0
    for r in rows:
        b=str(r.get('baseline_name','')).strip();
        if not b: continue
        by[b]=by.get(b,0)+1
        if bool(r.get('is_seed_scaffold',False)): seed+=1
        if bool(r.get('is_bootstrap_resample',False)): boot+=1
        if bool(r.get('oos_scenario_adjusted',False)): scenario_adjusted+=1
    min_n=max(1,int(a.min_samples_per_baseline))
    low=[b for b,n in by.items() if n<min_n]
    expected=[]
    for r in list(bench.get('baseline_results') or []):
        bname=str(((r.get('baseline') or {}).get('name',''))).strip()
        if bname: expected.append(bname)
    miss=[b for b in expected if b not in by]
    use_seed=seed>0
    ready_internal=(not use_seed) and (len(low)==0) and (len(by)>0) and (len(miss)==0)
    ready_public=ready_internal and (boot==0)
    runs=sum(1 for l in apath.read_text(encoding='utf-8-sig').splitlines() if l.strip()) if apath.is_file() else 0
    add=max(0,min_n-runs); eta=None
    if add>0:
        from datetime import timedelta
        eta=(datetime.now(timezone.utc)+timedelta(minutes=add*max(1,int(a.expected_cadence_minutes)))).strftime('%Y-%m-%dT%H:%M:%SZ')
    doc={'schema':'two_track_raw_oos_readiness_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'source_track':'K','source':{'raw_oos_jsonl':str(rp),'benchmark_json':str(bp) if bp.is_file() else None,'audit_log_jsonl':str(apath) if apath.is_file() else None},'summary':{'total_rows':len(rows),'baseline_count':len(by),'seed_rows':seed,'bootstrap_rows':boot,'scenario_adjusted_rows':scenario_adjusted,'uses_seed_scaffold':use_seed,'min_samples_per_baseline':min_n,'low_sample_baselines':low,'missing_expected_baselines':miss,'ready_for_internal_significance':ready_internal,'ready_for_publication_claim':ready_public},'forecast':{'observed_audit_runs':runs,'expected_runs_for_min_sample':min_n,'additional_audit_runs_required':add,'expected_cadence_minutes':max(1,int(a.expected_cadence_minutes)),'estimated_ready_utc_if_cadence_kept':eta}}
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n', encoding='utf-8'); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
