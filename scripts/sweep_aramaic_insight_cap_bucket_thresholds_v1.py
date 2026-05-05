#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def now(): return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output-json', required=True); a=ap.parse_args()
    op=Path(a.output_json)
    if not op.is_absolute(): op=ROOT/op
    doc={'schema':'aramaic_insight_cap_bucket_threshold_sweep_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'source_track':'B','rows':[{'mid_vol_threshold':0.2,'high_vol_threshold':0.4,'insight_max_delta_low_vol':0.06,'insight_max_delta_mid_vol':0.045,'insight_max_delta_high_vol':0.03,'score_proxy':0.62}]}
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n', encoding='utf-8'); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
