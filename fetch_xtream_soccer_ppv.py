import json, os, urllib.parse, urllib.request
server=os.environ['XTREAM_SERVER'].strip().rstrip('/')
user=os.environ['XTREAM_USERNAME'].strip()
password=os.environ['XTREAM_PASSWORD'].strip()
if not server.startswith(('http://','https://')): server='http://'+server
# Accept a base server URL or a URL ending in player_api.php.
if server.endswith('/player_api.php'): server=server[:-len('/player_api.php')]
qs=urllib.parse.urlencode({'username':user,'password':password,'action':'get_live_streams','category_id':'1513'})
url=f'{server}/player_api.php?{qs}'
req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (EPG Builder)'})
with urllib.request.urlopen(req,timeout=75) as response: data=json.load(response)
if not isinstance(data,list): raise RuntimeError('Xtream response is not a live stream list')
channels=[{'name':v.get('name',''),'stream_id':v.get('stream_id'),'epg_channel_id':v.get('epg_channel_id',''),'category_id':str(v.get('category_id',''))} for v in data if str(v.get('category_id',''))=='1513' or 'US: SOCCER PPV' in str(v.get('name','')).upper()]
if not channels: raise RuntimeError('No US: SOCCER PPV channels found; refusing to publish an empty guide')
with open('soccer_ppv_live_channels.json','w') as f:json.dump(channels,f)
print(f'Fetched {len(channels)} SOCCER PPV entries')
