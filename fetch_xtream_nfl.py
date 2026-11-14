#!/usr/bin/env python3
"""Fetch the provider's NFL PPV category without printing credentials."""
import json, os, urllib.parse, urllib.request
server=os.environ['XTREAM_SERVER'].strip().rstrip('/')
if not server.startswith(('http://','https://')): server='http://'+server
params=urllib.parse.urlencode({'username':os.environ['XTREAM_USERNAME'],'password':os.environ['XTREAM_PASSWORD'],'action':'get_live_streams','category_id':'597'})
url=f'{server}/player_api.php?{params}'
req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 NFL-EPG/1.0'})
with urllib.request.urlopen(req,timeout=55) as r: streams=json.load(r)
if not isinstance(streams,list): raise ValueError('Provider did not return a channel list')
if not streams: raise ValueError('NFL category 597 returned no channels; keeping previous guide')
with open('nfl_live_channels.json','w') as f: json.dump(streams,f)
print(f'Fetched {len(streams)} channels from NFL PPV category')
