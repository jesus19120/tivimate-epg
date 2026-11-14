#!/usr/bin/env python3
"""Build NFL PPV XMLTV with week-long pregame filler and stable slot IDs.

State file prevents unchanged stale matchups from being moved to future weeks.
Provider channel times are assumed America/New_York. Does not verify NFL fixtures.
"""
import datetime as dt
import gzip
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

ETZ=ZoneInfo('America/New_York')
UTC=dt.timezone.utc
STATE=Path('nfl_ppv_state.json')
SLOT_RE=re.compile(r'^NFL\s*\|\s*(?:4k|\d{1,2})\s*-\s*(.*)$',re.I)
TIME_RE=re.compile(r'(?<!\d)(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b',re.I)
AT_RE=re.compile(r'\b(.+?)\s+at\s+(.+)$',re.I)


def parse(name):
    m=SLOT_RE.match(name.strip())
    if not m: return None
    rest=m.group(1).strip()
    t=TIME_RE.search(rest)
    if not t: return None
    hour=int(t.group(1))%12+(12 if t.group(3).lower()=='pm' else 0)
    minute=int(t.group(2) or 0)
    if hour>23 or minute>59: return None
    teams=rest[t.end():].strip(' -|:')
    if not AT_RE.search(teams): return None
    day='monday' if re.search(r'\bMNF\b',rest,re.I) else 'sunday'
    return {'title':teams,'day':day,'hour':hour,'minute':minute}


def initial_date(today,day):
    # The upcoming (or current) Sunday; MNF is the next day.
    sunday=today+dt.timedelta(days=(6-today.weekday())%7)
    return sunday+dt.timedelta(days=(1 if day=='monday' else 0))


def xmltime(d):
    return d.astimezone(UTC).strftime('%Y%m%d%H%M%S +0000')


def main():
    src=Path(sys.argv[1] if len(sys.argv)>1 else 'nfl_live_channels.json')
    dest=Path(sys.argv[2] if len(sys.argv)>2 else 'nfl_ppv_live.xml.gz')
    streams=json.loads(src.read_text())
    if not isinstance(streams,list) or not streams: raise ValueError('Empty provider list; refusing to overwrite EPG')
    now=dt.datetime.now(ETZ)
    old=json.loads(STATE.read_text()) if STATE.exists() else {}
    state={}
    tv=ET.Element('tv',{'generator-info-name':'NFL PPV provider guide'})
    count=0
    for stream in streams:
        sid=stream.get('stream_id')
        if sid is None: continue
        name=str(stream.get('name','')).strip()
        cid=f'nfl-ppv-{sid}'
        channel=ET.SubElement(tv,'channel',{'id':cid})
        ET.SubElement(channel,'display-name').text=name
        # Header, NFL Network, RedZone and unassigned slots get channel records but no event.
        parsed=parse(name)
        if not parsed: continue
        key=str(sid)
        signature=f"{parsed['day']}|{parsed['hour']:02d}:{parsed['minute']:02d}|{parsed['title'].casefold()}"
        prev=old.get(key,{})
        if prev.get('signature')==signature and prev.get('date'):
            date=dt.date.fromisoformat(prev['date'])
        else:
            date=initial_date(now.date(),parsed['day'])
        state[key]={'signature':signature,'date':date.isoformat()}
        start=dt.datetime.combine(date,dt.time(parsed['hour'],parsed['minute']),ETZ)
        end=start+dt.timedelta(hours=3,minutes=30)
        # Filler is present from the guide's current window until kickoff, not from past weeks.
        filler_start=now-dt.timedelta(hours=2)
        if start>filler_start:
            prog=ET.SubElement(tv,'programme',{'channel':cid,'start':xmltime(filler_start),'stop':xmltime(start)})
            ET.SubElement(prog,'title').text=f"UP NEXT: {parsed['title']} — {start.strftime('%A')} {start.strftime('%I:%M %p').lstrip('0')} ET"
            ET.SubElement(prog,'desc').text='Upcoming NFL game. Kickoff time supplied by IPTV provider; date inferred from Sunday/Monday scheduling.'
            count+=1
        if end>now-dt.timedelta(hours=2):
            prog=ET.SubElement(tv,'programme',{'channel':cid,'start':xmltime(start),'stop':xmltime(end)})
            ET.SubElement(prog,'title').text=parsed['title']
            ET.SubElement(prog,'desc').text=f"NFL {('Monday Night Football' if parsed['day']=='monday' else 'Sunday Night Football' if 'SNF' in name.upper() else 'Football')}. Provider kickoff: {start.strftime('%A %b %d, %I:%M %p')} ET. End time estimated."
            count+=1
    # Persist state only for existing channels; blank slots can later receive events.
    STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
    data=ET.tostring(tv,encoding='utf-8',xml_declaration=True)
    with gzip.open(dest,'wb') as f: f.write(data)
    print(f'Wrote {dest}: {len(streams)} channels, {count} programmes; {len(state)} assigned game feeds')

if __name__=='__main__':main()
