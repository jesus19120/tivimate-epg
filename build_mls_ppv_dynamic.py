#!/usr/bin/env python3
"""Build an MLS PPV XMLTV guide from a fresh Xtream-style player_api JSON list.
Only category 607 (regular MLS PPV) is included; VIP/BK excluded.
Usage: python build_mls_ppv_dynamic.py player_api.json output.xml.gz
"""
import sys,json,re,gzip,datetime as dt,xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo
ETZONE=ZoneInfo('America/New_York')
CAT='607'
PAT=re.compile(r'^(.*?)\s*@\s*(?:([A-Za-z]{3,9})\s+)?(\d{1,2})\s+(\d{1,2}):(\d{2})\s*(AM|PM)\s*:MLS\s*(\d+)\s*$',re.I)
MONTHS={m.lower():i for i,m in enumerate(['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']) if m}
def parse_event(name,now):
 m=PAT.match(name.strip())
 if not m:return None
 title,mon,day,hr,minute,amp,num=m.groups()
 if not mon or mon[:3].lower() not in MONTHS:return None
 h=int(hr)%12+(12 if amp.upper()=='PM' else 0)
 # Pick nearest year, to handle year-end playlists. Do not infer that a stale event is current.
 candidates=[]
 for year in (now.year-1,now.year,now.year+1):
  try:candidates.append(dt.datetime(year,MONTHS[mon[:3].lower()],int(day),h,int(minute),tzinfo=ETZONE))
  except ValueError:pass
 if not candidates:return None
 start=min(candidates,key=lambda x:abs((x-now).total_seconds()))
 duration=dt.timedelta(minutes=60 if re.search(r'countdown|pregame|pre-game|postgame|post-game',title,re.I) else 150)
 return title.strip(),start,start+duration,int(num)
def build(input_path,output_path):
 with open(input_path,encoding='utf-8') as f:items=json.load(f)
 now=dt.datetime.now(ETZONE)
 tv=ET.Element('tv',{'generator-info-name':'MLS PPV event-title XMLTV generator'})
 selected=[];stale=[];unparsed=[]
 for item in items:
  if str(item.get('category_id'))!=CAT:continue
  name=str(item.get('name',''))
  m=re.search(r':MLS\s*(\d+)\s*$',name,re.I)
  if not m:continue
  number=int(m.group(1))
  if not 1<=number<=20:continue
  selected.append((number,name,item))
 for number,name,item in sorted(selected):
  cid=f'mls.ppv.{number:02d}'
  ch=ET.SubElement(tv,'channel',{'id':cid})
  for alias in (name,f'MLS {number:02d}',f'MLS PPV {number:02d}'):
   ET.SubElement(ch,'display-name').text=alias
  parsed=parse_event(name,now)
  if not parsed:
   unparsed.append((number,name));continue
  title,start,end,n=parsed
  if end<now-dt.timedelta(hours=12) or start>now+dt.timedelta(days=14):
   stale.append((number,title,start.isoformat()));continue
  prog=ET.SubElement(tv,'programme',{'start':start.strftime('%Y%m%d%H%M%S %z'),'stop':end.strftime('%Y%m%d%H%M%S %z'),'channel':cid})
  ET.SubElement(prog,'title',{'lang':'en'}).text=title
  ET.SubElement(prog,'desc',{'lang':'en'}).text='Start time extracted from provider channel name (Eastern Time). End time estimated from event type; not an official end time.'
 data=ET.tostring(tv,encoding='utf-8',xml_declaration=True)
 with gzip.open(output_path,'wb') as f:f.write(data)
 print(json.dumps({'channels':len(selected),'programmes':len(tv.findall('programme')),'stale_events':len(stale),'unparsed':len(unparsed),'stale_examples':stale[:3],'unparsed_examples':unparsed[:3]},indent=2))
if __name__=='__main__':
 if len(sys.argv)!=3:sys.exit('Usage: python build_mls_ppv_dynamic.py player_api.json output.xml.gz')
 build(sys.argv[1],sys.argv[2])
