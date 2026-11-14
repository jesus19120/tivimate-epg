import sys,json,re,gzip,xml.etree.ElementTree as ET
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
src=sys.argv[1] if len(sys.argv)>1 else 'soccer_ppv_live_channels.json'
dst=sys.argv[2] if len(sys.argv)>2 else 'soccer_ppv_live.xml.gz'
channels=json.load(open(src))
root=ET.Element('tv',{'generator-info-name':'SOCCER PPV dynamic Xtream guide'})
now=datetime.now(timezone.utc)
# Provider's dates are DD-MM-YYYY and times are explicitly GMT/UTC.
date_re=re.compile(r'\b(\d{2}-\d{2}-\d{4})\s*\|\s*(\d{1,2}:\d{2})\s*\(GMT\)',re.I)
slot_re=re.compile(r'\bUS\s*:\s*SOCCER\s+PPV\s+(\d{1,3})\s*$',re.I)
seen=set(); programmes=0
for ch in channels:
 name=str(ch.get('name',''))
 m=slot_re.search(name)
 if not m: continue
 slot=int(m.group(1))
 if not 1<=slot<=200 or slot in seen:continue
 seen.add(slot)
 # Stable slot ID: provider changes names but keeps each PPV slot.
 cid=f'us.soccer.ppv.{slot}'
 node=ET.SubElement(root,'channel',{'id':cid})
 ET.SubElement(node,'display-name').text=f'US SOCCER PPV {slot}'
 ET.SubElement(node,'display-name').text=name
 if any(word in name.upper() for word in ('NO EVENT STREAMING','####')):continue
 d=date_re.search(name)
 if not d:continue
 try: start=datetime.strptime(d.group(1)+' '+d.group(2),'%d-%m-%Y %H:%M').replace(tzinfo=timezone.utc)
 except ValueError:continue
 # No obsolete events. Include live/recent programmes only until their estimated end.
 label=name.split('|')[1].strip() if '|' in name else name
 label=re.sub(r'^\s*(?:NEXT|LIVE|END)\s*[:\-]?\s*','',label,flags=re.I).strip()
 low=label.lower()
 hours=3
 if any(t in low for t in ('test match','1st test','2nd test','3rd test','4th test','5th test')):hours=9
 elif any(t in low for t in ('odi','one day international')):hours=8
 elif any(t in low for t in ('t20','t10 league')):hours=4
 elif any(t in low for t in ('boxing','ufc','wwe','fight night')):hours=5
 elif any(t in low for t in ('tennis','atp','wta')):hours=4
 elif any(t in low for t in ('formula 1','grand prix','motogp')):hours=4
 elif any(t in low for t in (' vs ',' vs. ',' v ')):hours=3
 stop=start+timedelta(hours=hours)
 if stop < now-timedelta(minutes=15) or start > now+timedelta(days=14):continue
 fmt=lambda x:x.strftime('%Y%m%d%H%M%S +0000')
 p=ET.SubElement(root,'programme',{'channel':cid,'start':fmt(start),'stop':fmt(stop)})
 ET.SubElement(p,'title',{'lang':'en'}).text=label or f'PPV Event {slot}'
 ET.SubElement(p,'desc',{'lang':'en'}).text='Provider event listing. Start time supplied in GMT; end time estimated. Display in local time in TiviMate.'
 programmes+=1
if not seen:raise RuntimeError('No numbered PPV slots found; refusing empty guide')
xml=ET.tostring(root,encoding='utf-8',xml_declaration=True)
with gzip.open(dst,'wb') as f:f.write(xml)
print(f'Generated {len(seen)} channels, {programmes} non-expired events -> {dst}')
