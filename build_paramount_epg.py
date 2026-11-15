import argparse,datetime as dt,gzip,json,re,xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo
E=ZoneInfo('America/New_York')
SLOT=re.compile(r'PARAMOUNT\+\s*(?:PPV\s*)?(\d+)\b',re.I)
TIME=re.compile(r'\b(?:(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+)?(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}):(\d{2})\s*(EST|EDT|ET)?\b',re.I)
def xmltime(d):return d.astimezone(dt.timezone.utc).strftime('%Y%m%d%H%M%S +0000')
def add(tv,cid,a,b,title):
 if b<=a:return
 p=ET.SubElement(tv,'programme',{'channel':cid,'start':xmltime(a),'stop':xmltime(b)})
 ET.SubElement(p,'title',{'lang':'en'}).text=title
 ET.SubElement(p,'desc',{'lang':'en'}).text='Status estimated from scheduled time, not verified live result.'
def main():
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('output');p.add_argument('--event-hours',type=float,default=3);p.add_argument('--pre-hours',type=float,default=3);p.add_argument('--post-hours',type=float,default=2);a=p.parse_args()
 data=json.load(open(a.source,encoding='utf8'));cats=[c for c in data['categories'] if str(c.get('category_id'))=='1038' and 'PARAMOUNT' in c.get('category_name','').upper() and 'PPV' in c.get('category_name','').upper()]
 if len(cats)!=1:raise ValueError('Paramount PPV category 1038 not uniquely found')
 now=dt.datetime.now(E);tv=ET.Element('tv',{'generator-info-name':'Paramount PPV scheduled-status guide'});count=0;seen=set()
 for ch in cats[0]['channels']:
  name=str(ch.get('name',''));slot=SLOT.search(name);sid=ch.get('stream_id')
  if not slot or sid is None or sid in seen:continue
  seen.add(sid);cid='paramount-plus-ppv-'+str(sid)
  node=ET.SubElement(tv,'channel',{'id':cid});ET.SubElement(node,'display-name').text='US: PARAMOUNT+ PPV '+slot.group(1);ET.SubElement(node,'display-name').text=name
  m=TIME.search(name)
  if not m:continue
  weekday,day,month,hour,minute,zone=m.groups();month=dt.datetime.strptime(month.title(),'%b').month
  candidates=[]
  for year in (now.year-1,now.year,now.year+1):
   try:d=dt.datetime(year,month,int(day),int(hour),int(minute),tzinfo=E)
   except ValueError:continue
   if weekday and d.strftime('%a').lower()!=weekday.lower():continue
   if zone and zone.upper() in ('EST','EDT') and d.utcoffset()!=dt.timedelta(hours=-5 if zone.upper()=='EST' else -4):continue
   candidates.append(d)
  if not candidates:continue
  start=min(candidates,key=lambda d:abs((d-now).total_seconds()));title=name[:m.start()].strip(' |:-');title=re.sub(r'^(?:LIVE|NEXT|ENDED|UPCOMING)\s*\|\s*','',title,flags=re.I)
  if not title or title.startswith('#'):continue
  end=start+dt.timedelta(hours=a.event_hours)
  add(tv,cid,start-dt.timedelta(hours=a.pre_hours),start,'UPCOMING | '+title)
  add(tv,cid,start,end,'LIVE | '+title)
  add(tv,cid,end,end+dt.timedelta(hours=a.post_hours),'ENDED | '+title)
  count+=1
 if not count:raise ValueError('No event names/times parsed: refusing to publish empty guide')
 with gzip.open(a.output,'wb') as f:f.write(ET.tostring(tv,encoding='utf8',xml_declaration=True))
 print('Built',count,'events across',len(seen),'channels')
if __name__=='__main__':main()
