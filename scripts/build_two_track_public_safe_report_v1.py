#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def now(): return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def load(path):
    o=json.loads(path.read_text(encoding='utf-8'))
    return o if isinstance(o,dict) else {}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--academic-json', required=True); ap.add_argument('--benchmark-json', required=True); ap.add_argument('--significance-json', required=True); ap.add_argument('--output-json', required=True); a=ap.parse_args()
    apj,bp,sp,op=[Path(x) for x in [a.academic_json,a.benchmark_json,a.significance_json,a.output_json]]
    if not apj.is_absolute(): apj=ROOT/apj
    if not bp.is_absolute(): bp=ROOT/bp
    if not sp.is_absolute(): sp=ROOT/sp
    if not op.is_absolute(): op=ROOT/op
    ad,bd,sd=load(apj),load(bp),load(sp)
    pub={'schema':'two_track_public_safe_report_v1','generated_at_utc':now(),'public_safe':True,'proprietary_details_redacted':True,'disclosure_policy':{'open':['methodology_shape','safety_gates','artifact_paths'],'redacted':['core_formula','weight_tables','search_tuning']},'executive_summary':{'problem':((ad.get('abstract_scaffold') or {}).get('problem','')),'method':((ad.get('abstract_scaffold') or {}).get('method','')),'result':((ad.get('abstract_scaffold') or {}).get('result',''))},'public_metrics':{'primary_delta_shift_score':float((bd.get('delta') or {}).get('shift_score',0.0)),'significance_interpretation':sd.get('significance_interpretation','inconclusive')},'source_refs':{'academic_json':str(apj),'benchmark_json':str(bp),'significance_json':str(sp)}}
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text(json.dumps(pub,ensure_ascii=False,indent=2)+'\n', encoding='utf-8'); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
