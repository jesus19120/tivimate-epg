import json
import os
import urllib.error
import urllib.parse
import urllib.request

CATEGORY_ID = "1983"

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
    if str(category.get("category_id")) == CATEGORY_ID
    and "STAN PPV" in str(category.get("category_name", "")).upper()
    and str(category.get("category_name", "")).strip().upper().startswith("US")
]

if len(matches) != 1:
    raise SystemExit("US STAN PPV category 1983 not found")

category = matches[0]
category_name = str(category.get("category_name", ""))

streams = fetch("get_live_streams", CATEGORY_ID)

channels = [
    {
        "name": str(stream.get("name", "")),
        "stream_id": stream.get("stream_id"),
    }
    for stream in streams
    if stream.get("stream_id") is not None
]

if not channels:
    raise SystemExit("No valid US STAN PPV channels found")

output = {
    "categories": [
        {
            "category_id": CATEGORY_ID,
            "category_name": category_name,
            "channels": channels,
        }
    ]
}

with open("stan_channels_export.json", "w", encoding="utf-8") as file:
    json.dump(output, file, ensure_ascii=False, indent=2)

print(f"Category: {category_name}")
print(f"Category ID: {CATEGORY_ID}")
print(f"Channel count: {len(channels)}")
print("STAN channel discovery completed successfully")
