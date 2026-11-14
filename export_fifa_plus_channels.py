#!/usr/bin/env python3
"""Export public-facing channel metadata only from the provider's US FIFA Plus category."""
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

server = os.environ['XTREAM_SERVER'].strip().rstrip('/')
if not server.startswith(('http://', 'https://')):
    server = 'http://' + server
username = os.environ['XTREAM_USERNAME']
password = os.environ['XTREAM_PASSWORD']

def get(action, category_id=None):
    params = {'username': username, 'password': password, 'action': action}
    if category_id is not None:
        params['category_id'] = category_id
    url = server + '/player_api.php?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 EPG-Category-Export/1.0'})
    with urllib.request.urlopen(req, timeout=60) as response:
        data = json.load(response)
    if not isinstance(data, list):
        raise ValueError('Provider returned unexpected data for ' + action)
    return data

categories = get('get_live_categories')
# Require both FIFA and PLUS in the name; avoid accidentally exporting unrelated FIFA categories.
matched = [c for c in categories if re.search(r'fifa\s*\+|fifa\s*plus', str(c.get('category_name', '')), re.I) and re.search(r'\bUS\b|\bUSA\b|UNITED STATES', str(c.get('category_name', '')), re.I)]
if not matched:
    print('No exact US FIFA Plus category found. Available FIFA-related category names:')
    for c in categories:
        if 'fifa' in str(c.get('category_name', '')).lower():
            print('-', c.get('category_name', ''))
    raise SystemExit('Nothing exported; category name must be confirmed before proceeding.')

output = {'exported_at_utc': datetime.now(timezone.utc).isoformat(), 'categories': []}
for category in matched:
    category_id = str(category['category_id'])
    streams = get('get_live_streams', category_id)
    output['categories'].append({
        'category_name': category.get('category_name', ''),
        'category_id': category_id,
        'channel_count': len(streams),
        'channels': [
            {'name': str(s.get('name') or ''),
             'stream_id': s.get('stream_id'),
             'epg_channel_id': str(s.get('epg_channel_id') or ''),
             'category_id': str(s.get('category_id') or category_id)}
            for s in streams
        ],
    })
with open('fifa_plus_channels_export.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print('Exported metadata for', sum(c['channel_count'] for c in output['categories']), 'channels across', len(matched), 'categories')
print('Excluded stream URLs, provider address, username, password, and tokens.')
