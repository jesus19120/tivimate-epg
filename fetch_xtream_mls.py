#!/usr/bin/env python3
"""Fetch only MLS PPV live streams from an Xtream Codes provider.
Credentials are supplied via GitHub Actions secrets, never printed.
"""
import json, os, sys, urllib.parse, urllib.request

server=os.environ.get('XTREAM_SERVER','').strip().rstrip('/')
username=os.environ.get('XTREAM_USERNAME','')
password=os.environ.get('XTREAM_PASSWORD','')
if not (server and username and password):
    sys.exit('Missing XTREAM_SERVER, XTREAM_USERNAME, or XTREAM_PASSWORD secret')
if not server.startswith(('http://','https://')):
    sys.exit('XTREAM_SERVER must begin with http:// or https://')
query=urllib.parse.urlencode({'username':username,'password':password,'action':'get_live_streams','category_id':'607'})
url=server+'/player_api.php?'+query
req=urllib.request.Request(url,headers={'User-Agent':'MLS-EPG-Updater/1.0','Accept':'application/json'})
try:
    with urllib.request.urlopen(req,timeout=45) as response:
        data=json.load(response)
except Exception as exc:
    sys.exit('Xtream request failed: '+type(exc).__name__+' (check URL, credentials, and provider access)')
if not isinstance(data,list):
    sys.exit('Xtream API did not return a live-stream list')
items=[x for x in data if isinstance(x,dict) and str(x.get('category_id'))=='607']
if not items:
    sys.exit('No MLS PPV channels found in category 607; not publishing an empty guide')
with open('mls_live_channels.json','w',encoding='utf-8') as out:
    json.dump(items,out,ensure_ascii=False)
print('Fetched',len(items),'MLS PPV channel entries')
