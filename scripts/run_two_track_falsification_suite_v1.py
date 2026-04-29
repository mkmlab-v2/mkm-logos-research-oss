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
def metric_map(experiment_table):
    out={}
    for row in (experiment_table or []):
        if not isinstance(row,dict): continue
        name=str(row.get('metric','')).strip()
        if not name: continue
        out[name]=row.get('value')
    return out
def all_qna_items(qa_doc):
    items=[]
    for block in (qa_doc.get('audience_qna') or []):
        if not isinstance(block,dict): continue
        for it in (block.get('items') or []):
            if isinstance(it,dict): items.append(it)
    return items
def suite_status_from_passes(pass_count,total):
    return 'pass' if pass_count == total else ('warning' if pass_count >= 3 else 'fail')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--academic-packet-json', required=True); ap.add_argument('--qa-json', required=True); ap.add_argument('--output-json', required=True); ap.add_argument('--sensitivity-json', default='docs/final/artifacts/two_track_falsification_sensitivity_latest.json'); ap.add_argument('--counterfactual-comparison-json', default='docs/final/artifacts/multi_symbol_counterfactual_comparison_latest.json'); ap.add_argument('--min-survivor-count', type=int, default=1); ap.add_argument('--min-shift-score', type=float, default=0.0); ap.add_argument('--min-ci-low-defense-contrib', type=float, default=0.0); a=ap.parse_args()
    apath,qpath,op=[Path(x) for x in [a.academic_packet_json,a.qa_json,a.output_json]]
    spath=Path(a.sensitivity_json)
    cfpath=Path(a.counterfactual_comparison_json)
    if not apath.is_absolute(): apath=ROOT/apath
    if not qpath.is_absolute(): qpath=ROOT/qpath
    if not op.is_absolute(): op=ROOT/op
    if not spath.is_absolute(): spath=ROOT/spath
    if not cfpath.is_absolute(): cfpath=ROOT/cfpath
    ad,qd=load(apath),load(qpath)
    cfd=load(cfpath) if cfpath.is_file() else {}
    required_fields=list((qd.get('defense_prompt_policy') or {}).get('require_evidence_fields') or [])
    qna_items=all_qna_items(qd)
    qna_count=len(qna_items)
    metric=metric_map(ad.get('experiment_table'))
    shift_score=float(metric.get('shift_score',0.0) or 0.0)
    survivor_count=int(metric.get('survivor_count',0) or 0)
    ci_low=float(metric.get('ci_low_defense_contrib',0.0) or 0.0)
    boundary=str(((ad.get('abstract_scaffold') or {}).get('claim_boundary',''))).lower()

    # F1: evidence contract completeness in all Q&A rows.
    missing_fields=0
    for it in qna_items:
        evidence=it.get('evidence') if isinstance(it.get('evidence'),dict) else {}
        for f in required_fields:
            if f not in evidence:
                missing_fields += 1
    f1_pass=(qna_count > 0) and (missing_fields == 0)

    # F2: gate contract validity (required keys + rollback coherence).
    bad_gate_rows=0
    for it in qna_items:
        evidence=it.get('evidence') if isinstance(it.get('evidence'),dict) else {}
        gate=evidence.get('gate_eval') if isinstance(evidence.get('gate_eval'),dict) else {}
        has_keys=all(k in gate for k in ('pass','should_trade','rollback','reasons'))
        rollback_coherent=(bool(gate.get('rollback',False)) is (not bool(gate.get('should_trade',False))))
        if (not has_keys) or (not rollback_coherent):
            bad_gate_rows += 1
    f2_pass=(qna_count > 0) and (bad_gate_rows == 0)

    # F3/F4/F5: minimal quantitative and disclosure boundary checks.
    f3_pass=survivor_count >= int(a.min_survivor_count)
    f4_pass=(shift_score > float(a.min_shift_score)) and (ci_low > float(a.min_ci_low_defense_contrib))
    f5_pass=('public-safe' in boundary) or ('public safe' in boundary)
    cf_gate=(cfd.get('gate_eval') or {}) if isinstance(cfd.get('gate_eval'),dict) else {}
    cf_metrics=(cfd.get('metrics') or {}) if isinstance(cfd.get('metrics'),dict) else {}
    f6_pass=bool(cf_gate.get('pass',False)) and (float(cf_metrics.get('mean_gap_base_minus_counterfactual',0.0) or 0.0) > 0.0)

    checks=[
        {'id':'F1','name':'defense_evidence_contract_complete','pass':f1_pass,'detail':{'qna_items':qna_count,'missing_fields':missing_fields}},
        {'id':'F2','name':'gate_eval_contract_valid','pass':f2_pass,'detail':{'qna_items':qna_count,'bad_gate_rows':bad_gate_rows}},
        {'id':'F3','name':'survivor_nonzero_floor','pass':f3_pass,'detail':{'survivor_count':survivor_count,'threshold':int(a.min_survivor_count)}},
        {'id':'F4','name':'score_and_defense_positive','pass':f4_pass,'detail':{'shift_score':shift_score,'ci_low_defense_contrib':ci_low,'threshold':{'min_shift_score':float(a.min_shift_score),'min_ci_low_defense_contrib':float(a.min_ci_low_defense_contrib)}}},
        {'id':'F5','name':'public_safe_claim_boundary_declared','pass':f5_pass,'detail':{'claim_boundary':boundary}},
        {'id':'F6','name':'counterfactual_gap_gate_pass','pass':f6_pass,'detail':{'counterfactual_gate_pass':cf_gate.get('pass'),'mean_gap_base_minus_counterfactual':cf_metrics.get('mean_gap_base_minus_counterfactual')}},
    ]
    pass_count=sum(1 for x in checks if x['pass'])
    total=len(checks)
    suite_status=suite_status_from_passes(pass_count,total)
    out={'schema':'two_track_falsification_suite_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'source_track':'K','checks':checks,'pass_count':pass_count,'total_checks':total,'rollback_gate_snapshot':{'should_trade':False,'rollback':True},'suite_status':suite_status}
    sensitivity=[]
    for min_survivor in [1,3,5,7]:
        for min_ci in [0.0,0.2,0.4,0.6]:
            s_f3=survivor_count >= min_survivor
            s_f4=(shift_score > float(a.min_shift_score)) and (ci_low > min_ci)
            p=(1 if f1_pass else 0)+(1 if f2_pass else 0)+(1 if s_f3 else 0)+(1 if s_f4 else 0)+(1 if f5_pass else 0)+(1 if f6_pass else 0)
            sensitivity.append({'min_survivor_count':min_survivor,'min_ci_low_defense_contrib':min_ci,'pass_count':p,'total_checks':6,'suite_status':suite_status_from_passes(p,6)})
    sdoc={'schema':'two_track_falsification_sensitivity_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'source_track':'K','fixed_inputs':{'qna_count':qna_count,'missing_fields':missing_fields,'bad_gate_rows':bad_gate_rows,'shift_score':shift_score,'ci_low_defense_contrib':ci_low,'claim_boundary':boundary,'counterfactual_gate_pass':cf_gate.get('pass'),'counterfactual_mean_gap':cf_metrics.get('mean_gap_base_minus_counterfactual')},'active_thresholds':{'min_survivor_count':int(a.min_survivor_count),'min_shift_score':float(a.min_shift_score),'min_ci_low_defense_contrib':float(a.min_ci_low_defense_contrib)},'grid':sensitivity}
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    spath.parent.mkdir(parents=True, exist_ok=True); spath.write_text(json.dumps(sdoc,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    print(str(op)); print(str(spath)); return 0
if __name__=='__main__': raise SystemExit(main())
