#!/usr/bin/env python3
"""Generate a FIFA+ PPV XMLTV guide from sanitized Xtream channel metadata.

No provider credentials or URLs are written into the guide. Match listings are
scheduled by the date/time in provider names; pregame fillers use generic titles
so searches for the matchup show the future game rather than the current filler.
"""
import datetime as dt
import gzip
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo('America/New_York')
UTC = dt.timezone.utc
PATTERN = re.compile(r'^\s*(ENDED|LIVE|NEXT)\s*\|\s*(.+?)\s*\|\s*([A-Za-z]{3})\s+(\d{1,2})\s+([A-Za-z]{3})\s+(\d{1,2}):(\d{2})\s+(EST|EDT)\s*\(US\)', re.I)
SLOT = re.compile(r'\bUS\s*:\s*FIFA\+\s*PPV\s*(\d+)\b', re.I)
MONTHS = {dt.date(2000, m, 1).strftime('%b').lower(): m for m in range(1, 13)}
WEEKDAYS = ['mon','tue','wed','thu','fri','sat','sun']

def xmltime(t):
    return t.astimezone(UTC).strftime('%Y%m%d%H%M%S +0000')

def add_programme(tv, cid, start, stop, title, description):
    if stop <= start:
        return False
    p = ET.SubElement(tv, 'programme', {'channel': cid, 'start': xmltime(start), 'stop': xmltime(stop)})
    ET.SubElement(p, 'title', {'lang':'en'}).text = title
    ET.SubElement(p, 'desc', {'lang':'en'}).text = description
    return True

def parse(name, now):
    match = PATTERN.match(name)
    slot = SLOT.search(name)
    if not match or not slot:
        return None
    status, teams, weekday, day, month, hour, minute, zone = match.groups()
    month_num = MONTHS.get(month.lower())
    if not month_num:
        return None
    hour, minute, day = int(hour), int(minute), int(day)
    if hour > 23 or minute > 59:
        return None
    candidates = []
    for year in (now.year - 1, now.year, now.year + 1):
        try:
            d = dt.date(year, month_num, day)
        except ValueError:
            continue
        if WEEKDAYS[d.weekday()] != weekday.lower():
            continue
        start = dt.datetime.combine(d, dt.time(hour, minute), EASTERN)
        # The provider explicitly labels EST/EDT. Reject inconsistent offsets
        # rather than silently shifting the kickoff by an hour.
        expected = dt.timedelta(hours=-5 if zone.upper() == 'EST' else -4)
        if start.utcoffset() != expected:
            continue
        candidates.append(start)
    if not candidates:
        return None
    start = min(candidates, key=lambda d: abs((d - now).total_seconds()))
    return {'status':status.upper(), 'title':teams.strip(), 'start':start, 'slot':int(slot.group(1))}

def main():
    source = Path(sys.argv[1] if len(sys.argv) > 1 else 'fifa_plus_channels_export.json')
    target = Path(sys.argv[2] if len(sys.argv) > 2 else 'fifa_plus_ppv_live.xml.gz')
    data = json.loads(source.read_text(encoding='utf-8'))
    categories = [c for c in data.get('categories', []) if 'FIFA' in c.get('category_name','').upper() and '+' in c.get('category_name','')]
    if not categories:
        raise ValueError('No FIFA+ categories found. Refusing to overwrite guide.')
    now = dt.datetime.now(EASTERN)
    tv = ET.Element('tv', {'generator-info-name': 'US FIFA+ PPV dynamic guide'})
    seen = set()
    matches = 0
    skipped = 0
    for category in categories:
        for stream in category.get('channels', []):
            sid = stream.get('stream_id')
            if sid is None or str(sid) in seen:
                continue
            seen.add(str(sid))
            name = str(stream.get('name') or '')
            cid = f'fifa-plus-ppv-{sid}'
            channel = ET.SubElement(tv, 'channel', {'id':cid})
            ET.SubElement(channel, 'display-name').text = name
            # Additional stable slot alias helps TiviMate users identify channels.
            slot = SLOT.search(name)
            if slot:
                ET.SubElement(channel, 'display-name').text = f'US: FIFA+ PPV {slot.group(1)}'
            parsed = parse(name, now)
            if not parsed:
                if slot:
                    skipped += 1
                continue
            start = parsed['start']
            end = start + dt.timedelta(hours=2, minutes=30)  # estimated; not a live result
            status = parsed['status']
            if status == 'ENDED':
                # Ended events cannot appear as live even if their scheduled
                # estimate would otherwise extend into the present.
                end = min(end, now)
            # Filler starts at the earliest part of the rolling 7-day EPG window.
            # It has no team names in its title, so matchup searches hit the
            # future programme, not the currently airing filler.
            filler_start = now - dt.timedelta(hours=12)
            if status != 'ENDED' and start > filler_start:
                add_programme(tv, cid, filler_start, start,
                              'FIFA+ PPV — Upcoming Match',
                              f"Next: {parsed['title']}. Kickoff {start.strftime('%a %b %d, %I:%M %p')} ET. This is pregame information, not a live match.")
            if end > start and end > now - dt.timedelta(days=2):
                add_programme(tv, cid, start, end, parsed['title'],
                              f"FIFA+ PPV football match. Provider status at latest refresh: {status}. Kickoff: {start.strftime('%a %b %d, %I:%M %p')} ET. End time estimated.")
                matches += 1
    if not seen:
        raise ValueError('No channels returned; refusing to overwrite guide.')
    raw = ET.tostring(tv, encoding='utf-8', xml_declaration=True)
    with gzip.open(target, 'wb') as f:
        f.write(raw)
    print(f'Wrote {target}: {len(seen)} channels, {matches} game programmes, {skipped} unparsed slots')

if __name__ == '__main__':
    main()
