import gzip
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

INPUT = Path("stan_channels_export.json")
OUTPUT = Path("stan_ppv_live.xml.gz")

SYDNEY = ZoneInfo("Australia/Sydney")
UTC = ZoneInfo("UTC")

PATTERN = re.compile(
    r"^AU \(STAN (\d{2,3})\)\s*\|\s*(.*?)\s*"
    r"\((\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\)\s*$"
)

def xmltv_time(value):
    return value.astimezone(UTC).strftime("%Y%m%d%H%M%S +0000")

def main():
    if not INPUT.exists():
        raise SystemExit("Missing stan_channels_export.json")

    with INPUT.open("r", encoding="utf-8") as f:
        data = json.load(f)

    categories = data.get("categories", [])
    if not categories:
        raise SystemExit("No STAN categories found")

    channels = categories[0].get("channels", [])
    root = ET.Element("tv", {
        "generator-info-name": "TiviMate STAN Dynamic EPG"
    })

    parsed = []
    skipped = []

    for channel in channels:
        name = str(channel.get("name", ""))
        match = PATTERN.match(name)

        if not match:
            skipped.append(name)
            continue

        number, event, timestamp = match.groups()
        stream_id = str(channel["stream_id"])
        channel_id = f"stan.{number}"

        start = datetime.strptime(
            timestamp, "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=SYDNEY)

        event = " ".join(event.split())
        parsed.append((channel_id, number, event, start, stream_id))

    if not parsed:
        raise SystemExit("No valid STAN events found")

    for channel_id, number, event, start, stream_id in parsed:
        ch = ET.SubElement(root, "channel", id=channel_id)
        ET.SubElement(ch, "display-name").text = f"AU (STAN {number})"
        ET.SubElement(ch, "display-name").text = f"STAN {number}"
        ET.SubElement(ch, "display-name").text = str(stream_id)

    for channel_id, number, event, start, stream_id in parsed:
        stop = start + timedelta(hours=4)
        programme = ET.SubElement(root, "programme", {
            "start": xmltv_time(start),
            "stop": xmltv_time(stop),
            "channel": channel_id
        })
        ET.SubElement(programme, "title", lang="en").text = event
        ET.SubElement(programme, "desc", lang="en").text = (
            f"STAN PPV {number} | Broadcast start: "
            f"{start.strftime('%Y-%m-%d %I:%M %p %Z')} | "
            f"Stream ID: {stream_id}"
        )

    xml_bytes = ET.tostring(
        root, encoding="utf-8", xml_declaration=True
    )

    with gzip.open(OUTPUT, "wb") as f:
        f.write(xml_bytes)

    print(f"Channels: {len(parsed)}")
    print(f"Programmes: {len(parsed)}")
    print(f"Skipped: {len(skipped)}")
    print(f"Output: {OUTPUT}")

    if skipped:
        print("Skipped entries:")
        for name in skipped:
            print(f" - {name}")

if __name__ == "__main__":
    main()
