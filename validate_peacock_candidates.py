#!/usr/bin/env python3
"""Read-only triage of EPG candidate matches; never auto-approves or republishes schedules."""
import argparse, csv
from collections import defaultdict
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--comparison',default='epg_source_comparison.csv')
    p.add_argument('--mapping',default='peacock_refresh_readiness_audit.csv')
    p.add_argument('--output',default='peacock_candidate_review.csv')
    p.add_argument('--summary',default='peacock_candidate_summary.csv')
    a=p.parse_args()
    with open(a.comparison,encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    with open(a.mapping,encoding='utf-8-sig',newline='') as f: targets=list(csv.DictReader(f))
    by=defaultdict(list)
    for r in rows: by[r['peacock_channel']].append(r)
    out=[]; stats=defaultdict(int)
    for t in targets:
        label=t['Peacock channel']; allrows=by[label]
        candidates=[r for r in allrows if r['candidate_source_id'] and int(r['programmes'] or 0)>0]
        exact=[r for r in candidates if r['match_type']=='exact_id']
        unique=[r for r in candidates if r['match_type']=='name_candidate']
        ambiguous=[r for r in candidates if r['match_type']=='ambiguous']
        if exact: status='EXACT_ID_REVIEW'; chosen=exact
        elif unique: status='NAME_REVIEW'; chosen=unique
        elif ambiguous: status='AMBIGUOUS_REVIEW'; chosen=ambiguous
        else: status='NO_SCHEDULE_CANDIDATE'; chosen=[]
        stats[status]+=1
        # Every row remains pending manual channel identity, time-zone and reuse permission checks.
        if not chosen: chosen=[{}]
        for r in chosen:
            out.append({'peacock_channel':label,'stream_id':t['Stream ID'],'master_xmltv_id':t['Master XMLTV ID'],
                'review_status':status,'source':r.get('source',''),'source_channel_id':r.get('candidate_source_id',''),
                'match_type':r.get('match_type',''),'programme_count':r.get('programmes',''),
                'earliest_start_raw':r.get('earliest_start_utc_or_local',''),
                'latest_stop_raw':r.get('latest_stop_utc_or_local',''),
                'identity_verified':'NO','programme_titles_verified':'NO','timezone_verified':'NO',
                'reuse_permission_verified':'NO','ready_to_publish':'NO'})
    cols=['peacock_channel','stream_id','master_xmltv_id','review_status','source','source_channel_id','match_type',
          'programme_count','earliest_start_raw','latest_stop_raw','identity_verified','programme_titles_verified',
          'timezone_verified','reuse_permission_verified','ready_to_publish']
    with open(a.output,'w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(out)
    with open(a.summary,'w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(['review_status','channels'])
        for status in ['EXACT_ID_REVIEW','NAME_REVIEW','AMBIGUOUS_REVIEW','NO_SCHEDULE_CANDIDATE']:
            w.writerow([status,stats[status]])
        w.writerow(['TOTAL',len(targets)])
    print('Audited',len(targets),'Peacock channels. Counts:',dict(stats))
    print('All matches require manual identity, programme, timezone and reuse verification before publishing.')
if __name__=='__main__': main()
