import datetime as dt, gzip, json, re, sys, xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo
ETZONE=ZoneInfo('America/New_York')
NOW=dt.datetime.now(ETZONE)
INFILE=sys.argv[1] if len(sys.argv)>1 else 'nba_live_channels.json'
OUTFILE=sys.argv[2] if len(sys.argv)>2 else 'nba_ppv_live.xml.gz'
with open(INFILE) as f: channels=json.load(f)
root=ET.Element('tv',{'generator-info-name':'NBA PPV Xtream dynamic guide'})
count=0
for c in channels:
    name=c['name']; sid=str(c['stream_id']); channel_id=f'nba.ppv.{sid}'
    ch=ET.SubElement(root,'channel',id=channel_id)
    ET.SubElement(ch,'display-name').text=name
    m=re.search(r'\b(?:LIVE|NEXT)\s*\|\s*(.*?)\s*\|\s*((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+\d{1,2}\s+[A-Za-z]{3}\s+\d{1,2}:\d{2})\s+(?:EST|EDT)',name,re.I)
    if not m:continue
    event=m.group(1).strip(); raw=m.group(2)
    try:
        stamp=dt.datetime.strptime(raw,'%a %d %b %H:%M')
        candidates=[]
        for year in (NOW.year-1,NOW.year,NOW.year+1):
            try:
                candidate=stamp.replace(year=year,tzinfo=ETZONE)
                if candidate.strftime('%a').lower()==raw[:3].lower():candidates.append(candidate)
            except ValueError:pass
        if not candidates:continue
        start=min(candidates,key=lambda x:abs((x-NOW).total_seconds()))
        end=start+dt.timedelta(hours=3)
        if end < NOW-dt.timedelta(hours=6) or start>NOW+dt.timedelta(days=14):continue
        fmt=lambda x:x.strftime('%Y%m%d%H%M%S %z')
        p=ET.SubElement(root,'programme',{'start':fmt(start),'stop':fmt(end),'channel':channel_id})
        ET.SubElement(p,'title',lang='en').text=event.replace(' VS ',' vs ')
        ET.SubElement(p,'desc',lang='en').text='NBA PPV event. Time supplied by provider; estimated three-hour duration.'
        ET.SubElement(p,'category',lang='en').text='Basketball'
        count+=1
    except ValueError:continue
ET.indent(root,space='  ')
with gzip.open(OUTFILE,'wb') as f:f.write(ET.tostring(root,encoding='utf-8',xml_declaration=True))
print(f'Generated {len(channels)} channels, {count} current/upcoming programmes: {OUTFILE}')
