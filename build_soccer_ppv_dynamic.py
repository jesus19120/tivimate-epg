import gzip
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

SOURCE = sys.argv[1] if len(sys.argv) > 1 else 'soccer_ppv_live_channels.json'
OUTPUT = sys.argv[2] if len(sys.argv) > 2 else 'soccer_ppv_live.xml.gz'
with open(SOURCE, encoding='utf-8') as file:
    channels = json.load(file)

now = datetime.now(timezone.utc)
root = ET.Element('tv', {'generator-info-name': 'US PPV dynamic Xtream guide'})
slot_re = re.compile(r'\bUS\s*:\s*SOCCER\s+PPV\s+(\d{1,3})\s*$', re.I)
date_re = re.compile(r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\s*\|\s*(\d{1,2}:\d{2})\s*(?:\((?:GMT|UTC)\)|GMT|UTC)\b?', re.I)
# Some provider names use '(GMT)' where a word boundary does not follow the closing parenthesis.
date_re = re.compile(r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})\s*\|\s*(\d{1,2}:\d{2})\s*(?:\((?:GMT|UTC)\)|GMT|UTC)', re.I)
status_re = re.compile(r'^\s*(LIVE|NEXT|END)\b\s*[:|\-]?\s*', re.I)
seen = set()
programmes = 0

def fmt(dt):
    return dt.strftime('%Y%m%d%H%M%S +0000')

def duration_hours(title):
    lower = title.lower()
    if any(s in lower for s in ('test match', '1st test', '2nd test', '3rd test', '4th test', '5th test')):
        return 9
    if any(s in lower for s in ('odi', 'one day international')):
        return 8
    if any(s in lower for s in ('t20', 't10 league', 'tennis', 'atp', 'wta', 'grand prix', 'motogp')):
        return 4
    if any(s in lower for s in ('boxing', 'ufc', 'wwe', 'fight night', 'poker', 'championship', 'semifinal')):
        return 5
    return 3

for ch in channels:
    name = str(ch.get('name') or '')
    slot_match = slot_re.search(name)
    if not slot_match:
        continue
    slot = int(slot_match.group(1))
    if not 1 <= slot <= 200 or slot in seen:
        continue
    seen.add(slot)
    cid = f'us.soccer.ppv.{slot}'
    channel = ET.SubElement(root, 'channel', {'id': cid})
    ET.SubElement(channel, 'display-name').text = f'US SOCCER PPV {slot}'
    ET.SubElement(channel, 'display-name').text = name

    # Remove the stable slot suffix, retaining the event's full descriptive title.
    event = name[:slot_match.start()].strip(' |:-')
    event = re.sub(r'^\s*(?:US\s*:\s*SOCCER\s+PPV)\s*\|?\s*', '', event, flags=re.I)
    event = event.strip(' |:-')
    status_match = status_re.match(event)
    status = status_match.group(1).upper() if status_match else ''
    if status_match:
        event = event[status_match.end():].strip(' |:-')
    if status == 'END' or 'NO EVENT STREAMING' in name.upper() or not event or set(event) <= set('# |:-'):
        continue

    date_match = date_re.search(event)
    title = (event[:date_match.start()] + event[date_match.end():]).strip(' |:-') if date_match else event
    title = re.sub(r'\s*\|\s*all\b.*$', '', title, flags=re.I).strip(' |:-') or f'PPV Event {slot}'
    start = stop = None
    description = ''

    if date_match:
        date_text = date_match.group(1).replace('/', '-')
        try:
            scheduled = datetime.strptime(date_text + ' ' + date_match.group(2), '%d-%m-%Y %H:%M').replace(tzinfo=timezone.utc)
        except ValueError:
            scheduled = None
        if scheduled is not None:
            end_estimate = scheduled + timedelta(hours=duration_hours(title))
            if status == 'LIVE':
                # A LIVE marker is stronger evidence than an estimated end time.
                # Cover the current refresh interval even if the estimated end passed.
                start = scheduled if scheduled <= now else now - timedelta(minutes=15)
                if start < now - timedelta(hours=24):
                    start = now - timedelta(minutes=15)
                stop = max(end_estimate, now + timedelta(hours=4))
                description = 'Provider marks this event LIVE. Broadcast start may be estimated; listing refreshed every three hours.'
            elif end_estimate >= now - timedelta(minutes=15) and scheduled <= now + timedelta(days=14):
                start, stop = scheduled, end_estimate
                description = 'Provider event listing. Start time supplied in GMT/UTC; end time estimated.'
    elif status == 'LIVE':
        # No usable start time: don't invent one; this is only a rolling guide window.
        start = now - timedelta(minutes=15)
        stop = now + timedelta(hours=4)
        description = 'Provider marks this event LIVE; actual start time unavailable. Temporary rolling guide window, refreshed every three hours.'

    if start is None or stop is None or stop <= start:
        continue
    programme = ET.SubElement(root, 'programme', {'channel': cid, 'start': fmt(start), 'stop': fmt(stop)})
    ET.SubElement(programme, 'title', {'lang': 'en'}).text = title
    ET.SubElement(programme, 'desc', {'lang': 'en'}).text = description
    programmes += 1

if not seen:
    raise RuntimeError('No numbered US SOCCER PPV channels found; refusing empty guide')
xml = ET.tostring(root, encoding='utf-8', xml_declaration=True)
with gzip.open(OUTPUT, 'wb') as file:
    file.write(xml)
print(f'Generated {len(seen)} channels and {programmes} event listings -> {OUTPUT}')
