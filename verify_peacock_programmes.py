#!/usr/bin/env python3
"""Read-only XMLTV programme sampling for Peacock candidates. No publishing or automatic approvals."""
import argparse,csv,gzip,io,urllib.request,xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path

SOURCES={
 'epgshare_us2':'https://epgshare01.online/epgshare01/epg_ripper_US2.xml.gz',
 'epgshare_sports':'https://epgshare01.online/epgshare01/epg_ripper_US_SPORTS1.xml.gz',
 'epgtalk_us':'https://raw.githubusercontent.com/acidjesuz/EPGTalk/master/US_guide.xml.gz',
 'epgtalk_freetv':'https://raw.githubusercontent.com/acidjesuz/EPGTalk/master/FreeTV_guide.xml.gz',
 'teleonline':'https://teleonline.github.io/epg/epg.xml.gz',
}

def stream_for(url):
    raw=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'EPG-identity-audit/1.0'}),timeout=100)
    buf=io.BufferedReader(raw)
    return raw, gzip.GzipFile(fileobj=buf) if buf.peek(2)[:2]==b'\x1f\x8b' else buf

def parse_source(url,needed):
    raw,stream=stream_for(url)
    programmes=defaultdict(list);names=defaultdict(list)
    try:
        for _,el in ET.iterparse(stream,events=('end',)):
            tag=el.tag.rsplit('}',1)[-1]
            if tag=='channel':
                cid=el.get('id','')
                if cid in needed:names[cid]=[(n.text or '').strip() for n in el.findall('display-name') if n.text]
                el.clear()
            elif tag=='programme':
                cid=el.get('channel','')
                if cid in needed:
                    title=el.find('title');subtitle=el.find('sub-title');desc=el.find('desc')
                    programmes[cid].append((el.get('start',''),el.get('stop',''),(title.text or '').strip() if title is not None else '',(subtitle.text or '').strip() if subtitle is not None else '',(desc.text or '').strip()[:120] if desc is not None else ''))
                el.clear()
    finally:raw.close()
    return names,programmes

def parse_date(s):
    try:
        # XMLTV dates can include +/-HHMM; missing offset is NOT assumed UTC.
        return datetime.strptime(s.strip(),'%Y%m%d%H%M%S %z') if ' ' in s.strip() else None
    except ValueError:return None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--review',default='peacock_candidate_review.csv')
    ap.add_argument('--samples',default='peacock_programme_samples.csv')
    ap.add_argument('--summary',default='peacock_programme_verification.csv')
    ap.add_argument('--source-status',default='peacock_source_fetch_status.csv')
    ap.add_argument('--max-samples',type=int,default=5)
    args=ap.parse_args()
    with open(args.review,encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    required={'peacock_channel','source','source_channel_id','review_status'}
    if not rows or not required.issubset(rows[0]):raise SystemExit('Missing required columns in candidate review CSV')
    wanted=defaultdict(set)
    for r in rows:
        if r['source'] and r['source_channel_id']:wanted[r['source']].add(r['source_channel_id'])
    sources={};statuses=[]
    for source,ids in wanted.items():
        try:
            names,progs=parse_source(SOURCES.get(source,source),ids)
            sources[source]=(names,progs)
            statuses.append([source,'ok',len(ids),sum(bool(progs.get(i)) for i in ids),''])
        except Exception as e:
            sources[source]=({}, {})
            statuses.append([source,'failed',len(ids),0,str(e)[:400]])
    now=datetime.now(timezone.utc)
    samples=[];summaries=[]
    for r in rows:
        source=r['source'];cid=r['source_channel_id'];label=r['peacock_channel']
        names,progs=sources.get(source,({},{}))
        entries=sorted(progs.get(cid,[]),key=lambda p:p[0]);dates=[(parse_date(p[0]),parse_date(p[1])) for p in entries]
        valid=[(a,b) for a,b in dates if a is not None and b is not None and b>a]
        future=sum(b>now for a,b in valid)
        gaps=0;overlaps=0
        for (a,b),(c,d) in zip(valid,valid[1:]):
            if c>b:gaps+=1
            elif c<b:overlaps+=1
        titles=[p[2] for p in entries if p[2]]
        unique=len(set(titles))
        status='SOURCE_FAILED' if source and any(s[0]==source and s[1]=='failed' for s in statuses) else ('NO_PROGRAMMES' if not entries else ('REVIEW_TIMES_NO_OFFSET' if len(valid)<len(entries) else 'MANUAL_IDENTITY_REVIEW'))
        summaries.append([label,r.get('stream_id',''),r['review_status'],source,cid,' | '.join(names.get(cid,[])),len(entries),unique,len(valid),future,gaps,overlaps,entries[0][0] if entries else '',entries[-1][1] if entries else '',status,'NO'])
        for start,stop,title,subtitle,desc in entries[:max(0,args.max_samples)]:
            samples.append([label,source,cid,start,stop,title,subtitle,desc])
    for filename,header,data in [
        (args.samples,['peacock_channel','source','source_channel_id','start_xmltv','stop_xmltv','title','subtitle','description_excerpt'],samples),
        (args.summary,['peacock_channel','stream_id','prior_match_status','source','source_channel_id','source_display_names','programme_count','distinct_titles','valid_offset_datetime_entries','future_entries_at_run','schedule_gaps','schedule_overlaps','first_start_raw','last_stop_raw','audit_status','identity_verified'],summaries),
        (args.source_status,['source','fetch_status','candidate_ids','ids_with_programmes','error'],statuses)]:
        with open(filename,'w',newline='',encoding='utf-8') as f:
            w=csv.writer(f);w.writerow(header);w.writerows(data)
    print(f'Checked {len(rows)} candidate rows; {len(samples)} programme samples; source statuses: {statuses}')
    print('Note: programme content and channel identity require human review; provider reuse rights not assessed.')
if __name__=='__main__':main()
