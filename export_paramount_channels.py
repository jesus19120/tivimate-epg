import json
import os
import urllib.error
import urllib.parse
import urllib.request

server = os.environ['XTREAM_SERVER'].strip().rstrip('/')
if not server.startswith(('http://', 'https://')):
    server = 'http://' + server

username = os.environ['XTREAM_USERNAME']
password = os.environ['XTREAM_PASSWORD']

def get(action, category_id=None):
    params = {
        'username': username,
        'password': password,
        'action': action
    }
    if category_id is not None:
        params['category_id'] = str(category_id)

    url = server + '/player_api.php?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 EPG-Category-Export/1.0'}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        raise SystemExit(
            f'Xtream API rejected {action}: HTTP {exc.code}. '
            'Check provider API access, credentials, and server URL.'
        ) from None

    if not isinstance(data, list):
        raise ValueError(f'Unexpected response for {action}: expected a list')
    return data

categories = get('get_live_categories')
matched = [
    c for c in categories
    if str(c.get('category_id')) == '1038'
    and 'PARAMOUNT' in str(c.get('category_name', '')).upper()
]

if len(matched) != 1:
    raise ValueError('Expected exact Paramount PPV category 1038')

streams = get('get_live_streams', '1038')
channels = [
    {
        'name': str(s.get('name', '')),
        'stream_id': s.get('stream_id')
    }
    for s in streams
    if s.get('stream_id') is not None
]

if not channels:
    raise ValueError('No Paramount PPV channels; refusing to publish')

output = {
    'categories': [{
        'category_id': '1038',
        'category_name': matched[0].get('category_name', ''),
        'channels': channels
    }]
}

with open('paramount_channels_export.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f'Exported {len(channels)} Paramount PPV channels')
