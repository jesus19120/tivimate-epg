import argparse
import datetime as dt
import gzip
import json
import re
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")

TIME_RE = re.compile(
    r"\b(?:(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+)?"
    r"(\d{1,2})\s+([A-Za-z]{3})\s+"
    r"(\d{1,2}):(\d{2})\s*(EST|EDT|ET)?\b",
    re.IGNORECASE,
)

SLOT_RE = re.compile(r"PARAMOUNT\+?\s*(?:PPV)?\s*0*(\d+)", re.I)

def xmltime(value):
    return value.strftime("%Y%m%d%H%M%S %z")

def add_programme(tv, channel_id, start, end, title):
    programme = ET.SubElement(tv, "programme", {
        "channel": channel_id,
        "start": xmltime(start),
        "stop": xmltime(end),
    })
    ET.SubElement(programme, "title", {"lang": "en"}).text = title

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument("--pre-hours", type=float, default=1)
    parser.add_argument("--event-hours", type=float, default=3)
    parser.add_argument("--post-hours", type=float, default=1)
    args = parser.parse_args()

    with open(args.source, encoding="utf-8") as f:
        data = json.load(f)

    categories = data.get("categories", [])
    if len(categories) != 1:
        raise ValueError("Expected exactly one Paramount category")

    channels = categories[0].get("channels", [])
    if not channels:
        raise ValueError("No Paramount channels found")

    tv = ET.Element("tv", {"generator-info-name": "Paramount PPV EPG"})
    now = dt.datetime.now(EASTERN)
    channel_count = 0
    event_count = 0
    seen = set()

    for channel in channels:
        name = str(channel.get("name", "")).strip()
        stream_id = channel.get("stream_id")

        if stream_id is None:
            continue

        stream_id = str(stream_id)
        if stream_id in seen:
            continue
        seen.add(stream_id)

        channel_id = "paramount-plus-ppv-" + stream_id

        node = ET.SubElement(tv, "channel", {"id": channel_id})
        ET.SubElement(node, "display-name").text = name or ("Paramount+ " + stream_id)
        channel_count += 1

        match = TIME_RE.search(name)
        if not match:
            continue

        weekday, day, month, hour, minute, zone = match.groups()
        candidates = []

        for year in (now.year - 1, now.year, now.year + 1):
            try:
                event_date = dt.datetime.strptime(
                    f"{year} {month} {day} {hour}:{minute}",
                    "%Y %b %d %H:%M",
                ).replace(tzinfo=EASTERN)
            except ValueError:
                continue

            if weekday and event_date.strftime("%a").lower() != weekday.lower():
                continue

            if zone and event_date.strftime("%Z").upper() != zone.upper():
                continue

            candidates.append(event_date)

        if not candidates:
            continue

        start = min(candidates, key=lambda d: abs((d - now).total_seconds()))
        title = name[:match.start()].strip(" -|:")
        if not title:
            continue

        add_programme(
            tv, channel_id,
            start - dt.timedelta(hours=args.pre_hours),
            start, "Upcoming: " + title
        )
        add_programme(
            tv, channel_id,
            start,
            start + dt.timedelta(hours=args.event_hours),
            title
        )
        add_programme(
            tv, channel_id,
            start + dt.timedelta(hours=args.event_hours),
            start + dt.timedelta(hours=args.event_hours + args.post_hours),
            "Event ended: " + title
        )
        event_count += 1

    if not channel_count:
        raise ValueError("No valid channels to publish")

    xml_data = ET.tostring(tv, encoding="utf-8", xml_declaration=True)

    with gzip.open(args.output, "wb") as f:
        f.write(xml_data)

    print(f"Built {channel_count} channels and {event_count} scheduled events")
    if event_count == 0:
        print("NOTICE: No event times found; publishing channel-only guide")

if __name__ == "__main__":
    main()
