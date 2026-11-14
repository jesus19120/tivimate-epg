#!/usr/bin/env python3
"""Read-only XMLTV source coverage comparison. Writes CSV reports; never modifies guides."""
import argparse,csv,gzip,io,re,urllib.request,xml.etree.ElementTree as ET
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
def norm(s):return re.sub(r'[^a-z0-9]','',s.lower())
def parse(src):
    data=urllib.request.urlopen(urllib.request.Request(src,headers={'User-Agent':'EPG-coverage-audit/1.0'}),timeout=90) if src.startswith('http') else open(src,'rb')
    with data as raw:
        buffered=io.BufferedReader(raw)
        head=buffered.peek(2)[:2]
        stream=gzip.GzipFile(fileobj=buffered) if head==b'\x1f\x8b' else buffered
        names=defaultdict(set);programmes=defaultdict(lambda:[0,'',''])
        for _,el in ET.iterparse(stream,events=('end',)):
            tag=el.tag.rsplit('}',1)[-1]
            if tag=='channel':
                cid=el.get('id','')
                names[cid].add(cid)
                for n in el.findall('display-name'):
                    if n.text:names[cid].add(n.text.strip())
                el.clear()
            elif tag=='programme':
                cid=el.get('channel','');start=el.get('start','')[:14];stop=el.get('stop','')[:14]
                a=programmes[cid];a[0]+=1
                if start and (not a[1] or start<a[1]):a[1]=start
                if stop and stop>a[2]:a[2]=stop
                el.clear()
        return names,programmes

def main():
    p=argparse.ArgumentParser();p.add_argument('--master',required=True);p.add_argument('--peacock',required=True);p.add_argument('--output',default='epg_source_comparison.csv');p.add_argument('--summary',default='epg_source_summary.csv');p.add_argument('--sources',nargs='*',default=list(SOURCES));args=p.parse_args()
    master,_=parse(args.master)
    with open(args.peacock,encoding='utf-8-sig',newline='') as f:peacock=list(csv.DictReader(f))
    targets=[(r['Peacock channel'],r['Master XMLTV ID']) for r in peacock]
    now=datetime.now(timezone.utc)
    def is_future(value):
        if not value:return False
        try:return datetime.strptime(value[:14],'%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)>now
        except ValueError:return False
    rows=[];summaries=[]
    for name in args.sources:
        url=SOURCES.get(name,name)
        try:
            names,progs=parse(url)
            by_name=defaultdict(set)
            for cid,aliases in names.items():
                for a in aliases:by_name[norm(a)].add(cid)
            matched=0;fresh=0;ambiguous=0
            for label,masterid in targets:
                candidates=[]
                if masterid in names:candidates=[masterid];kind='exact_id'
                else:
                    aliases=master.get(masterid,{masterid})|{label}
                    matches=set().union(*(by_name.get(norm(a),set()) for a in aliases))
                    candidates=sorted(matches)
                    kind='name_candidate' if len(candidates)==1 else ('ambiguous' if candidates else 'missing')
                if candidates:matched+=1
                if len(candidates)>1:ambiguous+=1
                for cid in candidates or ['']:
                    count,start,stop=progs.get(cid,[0,'',''])
                    if is_future(stop):fresh+=1
                    rows.append([name,label,masterid,kind,cid,count,start,stop,'approximate' if is_future(stop) else 'no'])
            summaries.append([name,'ok',len(names),len(progs),matched,ambiguous,fresh,''])
        except Exception as e:summaries.append([name,'failed',0,0,0,0,0,str(e)[:300]])
    with open(args.output,'w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['source','peacock_channel','master_xmltv_id','match_type','candidate_source_id','programmes','earliest_start_utc_or_local','latest_stop_utc_or_local','future_by_naive_UTC_approximation']);w.writerows(rows)
    with open(args.summary,'w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['source','status','channel_ids','ids_with_programmes','peacock_channels_with_candidate','ambiguous_channels','future_candidate_rows','error']);w.writerows(summaries)
    print('Wrote',args.output,args.summary)
if __name__=='__main__':main()
