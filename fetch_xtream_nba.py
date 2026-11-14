import json, os, urllib.parse, urllib.request
server=os.environ['XTREAM_SERVER'].strip().rstrip('/')
if not server.startswith(('http://','https://')): server='http://'+server
params=urllib.parse.urlencode({'username':os.environ['XTREAM_USERNAME'],'password':os.environ['XTREAM_PASSWORD'],'action':'get_live_streams','category_id':'2094'})
req=urllib.request.Request(f'{server}/player_api.php?{params}',headers={'User-Agent':'Mozilla/5.0'})
with urllib.request.urlopen(req,timeout=75) as r: channels=json.load(r)
if not isinstance(channels,list): raise RuntimeError('Unexpected provider response; refusing to publish')
channels=[{'name':c['name'],'stream_id':c['stream_id']} for c in channels if str(c.get('category_id'))=='2094' or 2094 in c.get('category_ids',[])]
if not channels: raise RuntimeError('No NBA category channels; refusing to publish')
with open('nba_live_channels.json','w') as f:json.dump(channels,f)
print(f'Fetched {len(channels)} NBA channels')
