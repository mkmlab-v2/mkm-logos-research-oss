#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def now(): return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def load(p):
    o=json.loads(p.read_text(encoding='utf-8'))
    return o if isinstance(o,dict) else {}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--knowledge-report-json', required=True); ap.add_argument('--regime-score-json', required=True); ap.add_argument('--survivor-json', required=True); ap.add_argument('--survivor-alert-json', required=True); ap.add_argument('--output-json', required=True); a=ap.parse_args()
    kp,rp,sp,apj,op=[Path(x) for x in [a.knowledge_report_json,a.regime_score_json,a.survivor_json,a.survivor_alert_json,a.output_json]]
    for var,name in [(kp,'kp'),(rp,'rp'),(sp,'sp'),(apj,'apj'),(op,'op')]:
        if not var.is_absolute():
            if name=='kp': kp=ROOT/var
            elif name=='rp': rp=ROOT/var
            elif name=='sp': sp=ROOT/var
            elif name=='apj': apj=ROOT/var
            else: op=ROOT/var
    k,sr,sv,al=load(kp),load(rp),load(sp),load(apj)
    doc={'schema':'two_track_fusion_report_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'tracks':{'K':{'purpose':'knowledge_ip','not_for_trading_signal':True,'summary':k.get('summary',{})},'T':{'purpose':'trading_filter','shift_score':sr.get('shift_score',0.0),'survivor_count':sv.get('survivor_count',0),'health_alert':al.get('should_alert',False)}},'sources':{'knowledge_report_json':str(kp),'regime_score_json':str(rp),'survivor_json':str(sp),'survivor_alert_json':str(apj)}}
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n', encoding='utf-8'); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
