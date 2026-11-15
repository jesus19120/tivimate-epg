import json
import os
import urllib.error
import urllib.parse
import urllib.request

server = os.environ["XTREAM_SERVER"].strip().rstrip("/")
if not server.startswith(("http://", "https://")):
    server = "http://" + server

username = os.environ["XTREAM_USERNAME"]
password = os.environ["XTREAM_PASSWORD"]

def fetch(action, category_id=None):
    params = {
        "username": username,
        "password": password,
        "action": action,
    }
    if category_id is not None:
        params["category_id"] = str(category_id)

    url = server + "/player_api.php?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 EPG-Category-Export/1.0"},
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        raise SystemExit(
            f"Xtream API returned HTTP {error.code} for {action}"
        ) from None

    if not isinstance(data, list):
        raise ValueError(f"Unexpected response for {action}")
    return data

categories = fetch("get_live_categories")

matches = [
    category
    for category in categories
    if "STAN" in str(category.get("category_name", "")).upper()
]

if not matches:
    raise SystemExit("No STAN categories found")

found_target = False

for category in matches:
    category_id = str(category["category_id"])
    category_name = str(category.get("category_name", ""))
    streams = fetch("get_live_streams", category_id)

    print(f"Category: {category_name}")
    print(f"Category ID: {category_id}")
    print(f"Channel count: {len(streams)}")

    if category_name.strip().upper() == "US | STAN":
        found_target = True
        channels = [
            {
                "name": str(stream.get("name", "")),
                "stream_id": stream.get("stream_id"),
            }
            for stream in streams
            if stream.get("stream_id") is not None
        ]

        if not channels:
            raise SystemExit("US | STAN has no valid channels")

        output = {
            "categories": [
                {
                    "category_id": category_id,
                    "category_name": category_name,
                    "channels": channels,
                }
            ]
        }

        with open("stan_channels_export.json", "w", encoding="utf-8") as file:
            json.dump(output, file, ensure_ascii=False, indent=2)

        print(f"Exported {len(channels)} US | STAN channels")

if not found_target:
    raise SystemExit("Exact US | STAN category not found")
